import assert from 'node:assert/strict'
import { execFile } from 'node:child_process'
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'

import { apply } from '../index.js'

const execFileAsync = promisify(execFile)
const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function fakeContext() {
  const tools = []
  const providers = []
  return {
    ctx: {
      tools: { register: tool => tools.push(tool) },
      skills: { registerProvider: factory => providers.push(factory({ signal: new AbortController().signal })) },
    },
    tools,
    providers,
  }
}

test('plugin registers the full Xiaojia tool surface and bundled skill', async () => {
  const { ctx, tools, providers } = fakeContext()

  apply(ctx, { apiKey: 'test-key' })

  assert.deepEqual(
    tools.map(tool => tool.name),
    [
      'xiaojia_chat',
      'xiaojia_projects',
      'xiaojia_skills',
      'xiaojia_upload_image',
      'xiaojia_generate_image',
      'xiaojia_image_result',
      'xiaojia_credits',
      'xiaojia_video',
    ],
  )
  assert.equal(providers.length, 1)
  const candidates = await providers[0].list({})
  assert.equal(candidates[0].name, 'xiaojia-marketing-delivery')
  const skill = await providers[0].get(candidates[0], {})
  assert.match(skill.content, /xiaojia_chat/)
  assert.doesNotMatch(skill.content, /^---/)
})

test('skill create operation calls the existing OpenAPI without requiring skill_id', async () => {
  const originalFetch = globalThis.fetch
  const calls = []
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options })
    return new Response(JSON.stringify({ status: 0, data: { skill_id: 'skill_new' } }), { status: 200 })
  }
  try {
    const { ctx, tools } = fakeContext()
    apply(ctx, { apiKey: 'test-key', baseUrl: 'https://example.test' })
    const tool = tools.find(item => item.name === 'xiaojia_skills')

    const result = await tool.execute({
      operation: 'create',
      name: '测试 Skill',
      description: '测试描述',
      prompt_content: '测试 Prompt',
    }, { signal: new AbortController().signal })

    assert.equal(result.data.skill_id, 'skill_new')
    assert.equal(calls[0].url, 'https://example.test/openapi/skills/create')
    assert.deepEqual(JSON.parse(calls[0].options.body), {
      name: '测试 Skill',
      description: '测试描述',
      prompt_content: '测试 Prompt',
    })
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('video approval requires explicit confirmation and revision', async () => {
  const { ctx, tools } = fakeContext()
  apply(ctx, { apiKey: 'test-key' })
  const tool = tools.find(item => item.name === 'xiaojia_video')
  await assert.rejects(tool.execute({ operation: 'approve', conversation_id: 'c', action_id: 'a', revision: 1 }, {}), /confirmation/)
  await assert.rejects(tool.execute({ operation: 'approve', conversation_id: 'c', action_id: 'a', confirmed: true }, {}), /revision/)
})

test('upload tool accepts a clipboard filename and formatted data URI, and PUTs the original bytes', async t => {
  const bytes = Buffer.from([0x89, 0x50, 0x4e, 0x47])
  const uploadId = 'c17314bb-93d5-496b-8b85-2d9fd359ef61'
  const putUrl = 'https://bucket.cos.example.test/staging?signature=test'
  const finalUrl = 'https://cdn.example.test/sealed/reference.png'
  let put = false
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url === putUrl) {
      assert.equal(options.method, 'PUT')
      assert.ok(bytes.equals(options.body))
      const headers = new Headers(options.headers)
      assert.equal(headers.get('content-type'), 'image/png')
      assert.equal(headers.get('x-cos-acl'), 'private')
      assert.equal(headers.has('authorization'), false)
      put = true
      return new Response(null, { status: 200 })
    }

    const body = JSON.parse(options.body)
    assert.equal(options.headers.Authorization, 'Bearer test-key')
    if (url.endsWith('/upload_url')) {
      assert.equal(body.filename, 'clipboard.png')
      assert.equal(body.content_type, 'image/png')
      assert.equal(body.size_bytes, bytes.length)
      assert.equal('image_base64' in body, false)
      return Response.json({
        status: 'ok', upload_id: uploadId, upload_url: putUrl, method: 'PUT',
        headers: { 'Content-Type': 'image/png', 'x-cos-acl': 'private' },
      })
    }
    assert.ok(url.endsWith('/upload_complete'))
    assert.ok(put)
    assert.equal(body.upload_id, uploadId)
    return Response.json({ status: 'ok', upload_id: uploadId, url: finalUrl })
  })

  const { ctx, tools } = fakeContext()
  apply(ctx, { apiKey: 'test-key', baseUrl: 'https://example.test' })
  const tool = tools.find(item => item.name === 'xiaojia_upload_image')
  const result = await tool.execute({
    file_name: 'screenshots/clipboard',
    image_base64: '  data:IMAGE/PNG;BASE64,\n' + bytes.toString('base64').replace(/(.{32})/g, '$1\n'),
    content_type: 'image/png',
  }, {})

  assert.equal(result.url, finalUrl)
  assert.equal(result.cos_key, '/sealed/reference.png')
  assert.equal(result.upload_id, uploadId)
})

test('upload tool preserves the upload ID if confirmation must be retried', async t => {
  const uploadId = 'c17314bb-93d5-496b-8b85-2d9fd359ef61'
  const putUrl = 'https://bucket.cos.example.test/staging?signature=test'
  let tickets = 0
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url === putUrl) return new Response(null, { status: 200 })
    if (url.endsWith('/upload_url')) {
      tickets += 1
      return Response.json({
        status: 'ok', upload_id: uploadId, upload_url: putUrl, method: 'PUT',
        headers: { 'Content-Type': 'image/png', 'x-cos-acl': 'private' },
      })
    }
    assert.ok(url.endsWith('/upload_complete'))
    assert.equal(JSON.parse(options.body).upload_id, uploadId)
    return Response.json({ status: 'error', code: 'upload_not_found', message: 'COS 尚未收到该对象' }, { status: 409 })
  })

  const { ctx, tools } = fakeContext()
  apply(ctx, { apiKey: 'test-key', baseUrl: 'https://example.test' })
  const tool = tools.find(item => item.name === 'xiaojia_upload_image')
  await assert.rejects(tool.execute({
    file_name: 'reference.png', image_base64: 'data:image/png;base64,iVBORw==', content_type: 'image/png',
  }, {}), error => {
    assert.match(error.message, /upload_not_found/)
    assert.ok(error.message.includes(uploadId))
    assert.match(error.message, /upload_complete/)
    assert.equal(error.message.includes(putUrl), false)
    return true
  })
  assert.equal(tickets, 1)
})

test('plugin uses the API key persisted by the documented login command', async t => {
  const home = await mkdtemp(join(tmpdir(), 'xiaojia-plugin-login-'))
  const configPath = join(home, '.codex', 'justai-openapi-chat.json')
  await mkdir(join(home, '.codex'), { recursive: true })
  await writeFile(configPath, JSON.stringify({ api_key: 'persisted-key' }))
  t.after(() => rm(home, { recursive: true, force: true }))

  const originalFetch = globalThis.fetch
  const originalConfigPath = process.env.JUSTAI_OPENAPI_CONFIG
  const originalApiKey = process.env.JUSTAI_OPENAPI_API_KEY
  process.env.JUSTAI_OPENAPI_CONFIG = configPath
  delete process.env.JUSTAI_OPENAPI_API_KEY
  let authorization = ''
  globalThis.fetch = async (_url, options) => {
    authorization = options.headers.Authorization
    return new Response(JSON.stringify({ status: 0, data: [] }), { status: 200 })
  }
  try {
    const { ctx, tools } = fakeContext()
    apply(ctx, { baseUrl: 'https://example.test' })
    const tool = tools.find(item => item.name === 'xiaojia_projects')

    await tool.execute({}, { signal: new AbortController().signal })

    assert.equal(authorization, 'Bearer persisted-key')
  } finally {
    globalThis.fetch = originalFetch
    if (originalConfigPath === undefined) delete process.env.JUSTAI_OPENAPI_CONFIG
    else process.env.JUSTAI_OPENAPI_CONFIG = originalConfigPath
    if (originalApiKey === undefined) delete process.env.JUSTAI_OPENAPI_API_KEY
    else process.env.JUSTAI_OPENAPI_API_KEY = originalApiKey
  }
})

test('package exposes a public installable DSH bundle', async () => {
  const packageJson = JSON.parse(await readFile(resolve(packageRoot, 'package.json'), 'utf8'))

  assert.equal(packageJson.name, '@qinshimeng81/dsh-xiaojia-marketing-delivery')
  assert.equal(packageJson.private, undefined)
  assert.equal(packageJson.publishConfig.access, 'public')
  assert.equal(packageJson.dsh.bundle.patch, './cordis.patch.yml')
  assert.equal(packageJson.repository.directory, 'skills/xiaojia-Marketing-Delivery')
  assert.ok(packageJson.keywords.includes('dsh-plugin'))
})

test('npm package contains the runtime and bundled Skill only', async () => {
  const { stdout } = await execFileAsync(
    'npm',
    ['pack', '--dry-run', '--json', '--ignore-scripts'],
    { cwd: packageRoot },
  )
  const files = JSON.parse(stdout)[0].files.map(item => item.path)

  for (const expected of [
    'client.js',
    'cordis.patch.yml',
    'credentials.js',
    'index.js',
    'package.json',
    'skills/xiaojia-marketing-delivery/SKILL.md',
  ]) {
    assert.ok(files.includes(expected), `missing package file: ${expected}`)
  }
  assert.equal(files.some(path => path.startsWith('tests/')), false)
  assert.equal(files.some(path => path.startsWith('scripts/')), false)
})
