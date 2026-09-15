import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, readFile, rm, stat } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { CLIClient, loadConfig, saveConfig, validateBaseUrl } from '../cli/api.js'
import { publicAddress, collectArtifacts, mediaUrl } from '../cli/media.js'
import { renderMarkdown, safe, inlineImagesSupported } from '../cli/main.js'
import terminalImage from 'term-img'
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'xiaojia-test-'))
  t.after(() => rm(root, { recursive: true, force: true }))
  return root
}

test('CLI专用配置优先，原Skill凭证不被覆盖', async t => {
  const home = await fixture(t), path = join(home, '.xiaojia/config.json')
  await saveConfig({ path, baseUrl: 'http://127.0.0.1:18917' }, 'trial-key')
  const config = await loadConfig({ JUSTAI_OPENAPI_BASE_URL: 'https://justailab.com', JUSTAI_OPENAPI_API_KEY: 'legacy-production-key' }, home)
  assert.equal(config.apiKey, 'trial-key')
  assert.equal(config.baseUrl, 'http://127.0.0.1:18917')
  await assert.rejects(loadConfig({ XIAOJIA_BASE_URL: 'https://other.example.org' }, home), /不匹配/)
})

test('配置绑定服务器，不向新服务器泄露旧密钥', async t => {
  const root = await fixture(t), path = join(root, 'config.json')
  await saveConfig({ path, baseUrl: 'https://justailab.com' }, 'test-key')
  assert.equal((await loadConfig({ JUSTAI_OPENAPI_CONFIG: path }, root)).apiKey, 'test-key')
  await assert.rejects(loadConfig({ JUSTAI_OPENAPI_CONFIG: path, JUSTAI_OPENAPI_BASE_URL: 'https://example.org' }, root))
  assert.throws(() => validateBaseUrl('http://example.org'))
  assert.throws(() => validateBaseUrl('https://user:secret@example.org'))
  assert.equal(validateBaseUrl('http://127.0.0.1:8123'), 'http://127.0.0.1:8123')
})

test('媒体下载拒绝内网和IPv6映射地址', () => {
  for (const value of ['127.0.0.1', '10.1.1.1', '172.20.0.1', '192.168.1.1', '169.254.169.254', '::ffff:127.0.0.1']) assert.equal(publicAddress(value), false)
  assert.equal(publicAddress('8.8.8.8'), true)
})

test('Markdown 正常排版，过滤终端控制序列和实体转义注入', () => {
  assert.match(safe(renderMarkdown('**完成**\n\n- 小猫照片')), /^完成\n\n\s+\* 小猫照片$/)
  assert.equal(safe('正文\x1b[2J\x1b]52;c;c2VjcmV0\x07结束'), '正文结束')
  assert(!renderMarkdown('&#27;[2J').includes('\x1b'))
  assert(!renderMarkdown('[查看](https://example.org)').includes('[查看]('))
})

test('媒体只取结构化工具结果，兼容实际 picture_urls，拒绝危险链接和失败结果', () => {
  const url = 'https://example.org/cat.png'
  assert.deepEqual(collectArtifacts({ picture_urls: [url, url], prompt: 'https://example.org/prompt.png', text: 'https://example.org/text.png' }), [{ type: 'image', url }])
  for (const bad of ['file:///etc/a.png', 'https://user:pass@example.org/a.png', 'https://example.org:444/a.png', 'https://example.org/a.png\n', 'javascript:alert(1)']) assert.equal(mediaUrl(bad), null)
  assert.deepEqual(collectArtifacts({ denied: true, picture_urls: [url] }), [])
  assert.deepEqual(collectArtifacts({ generation_status: 'failed', picture_urls: [url] }), [])
})

test('原生图片协议与不支持终端的降级，不输出字符画', () => {
  const previous = process.env.TERM_PROGRAM, version = process.env.TERM_PROGRAM_VERSION
  try {
    process.env.TERM_PROGRAM = 'vscode'; process.env.TERM_PROGRAM_VERSION = '1.100.0'
    const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aO1kAAAAASUVORK5CYII=', 'base64')
    assert.match(terminalImage(png, { width: 20, fallback: () => '' }), /1337;File=/)
    assert.equal(inlineImagesSupported(), true)
    process.env.TERM_PROGRAM = 'iTerm.app'; process.env.TERM_PROGRAM_VERSION = '3.7.2'
    const original = terminalImage(png, { width: 64, height: 20, preserveAspectRatio: true, fallback: () => '' })
    assert.equal(inlineImagesSupported(), true)
    if (process.platform === 'darwin') {
      assert.match(original, /1337;File=/)
      assert.ok(original.includes(png.toString('base64')), '传输原始图片字节，不转换为字符画或重编码')
    } else assert.equal(original, '', 'term-img 的 iTerm2 检测仅支持 macOS')
    process.env.TERM_PROGRAM = 'Apple_Terminal'
    assert.equal(inlineImagesSupported(), false)
    assert.equal(terminalImage(png, { fallback: () => '' }), '')
  } finally {
    if (previous === undefined) delete process.env.TERM_PROGRAM; else process.env.TERM_PROGRAM = previous
    if (version === undefined) delete process.env.TERM_PROGRAM_VERSION; else process.env.TERM_PROGRAM_VERSION = version
  }
})

async function runCLI(args, env = {}) {
  const child = spawn(process.execPath, [new URL('../cli/main.js', import.meta.url).pathname, ...args], { env: { ...process.env, ...env } })
  let stdout = '', stderr = ''
  child.stdout.on('data', chunk => { stdout += chunk })
  child.stderr.on('data', chunk => { stderr += chunk })
  const code = await new Promise((resolve, reject) => { child.on('error', reject); child.on('close', resolve) })
  return { code, stdout, stderr }
}

test('doctor 使用既有积分接口，不依赖模型接口并拒绝业务错误', async () => {
  const client = new CLIClient({ apiKey: 'private-key', fetchImpl: async (url, options) => {
    assert.ok(url.endsWith('/openapi/credits/balance'))
    assert.equal(options.method, 'POST')
    return Response.json({ status: 'ok', available_credits: 0 })
  } })
  assert.equal((await client.checkReady()).available_credits, 0)
  assert.equal(client.model, undefined)
  client.fetchImpl = async () => Response.json({ status: -2, msg: 'bad private-key' })
  await assert.rejects(client.checkReady(), error => !error.message.includes('private-key'))
  client.fetchImpl = async () => Response.json({ status: 'ok' })
  await assert.rejects(client.checkReady(), /响应异常/)
})

test('无参数只显示帮助；旧 Agent 命令和授权参数不再可用', async () => {
  assert.match((await runCLI([])).stdout, /轻量命令行封装/)
  for (const args of [['run', 'hello'], ['sessions'], ['chat', 'hello', '--allow-shell']]) {
    const result = await runCLI([...args, '--json'])
    assert.equal(result.code, 1)
    assert.equal(JSON.parse(result.stdout).status, 'error')
  }
  for (const file of ['agent.js', 'session.js', 'tools.js']) {
    await assert.rejects(stat(new URL('../cli/' + file, import.meta.url)), { code: 'ENOENT' })
  }
})

test('CLI 直接调用图片/对话/视频 API，不运行本地 Agent、不写会话', async t => {
  const home = await fixture(t), calls = [], url = 'https://example.org/cat.png'
  const server = createServer(async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk
    calls.push({ path: req.url, body: JSON.parse(raw || '{}') })
    res.setHeader('Content-Type', 'application/json')
    const responses = {
      '/openapi/images/generate': { status: 'ok', generation_status: 'completed', picture_urls: [url] },
      '/openapi/agent/chat_submit': { status: 'accepted', conversation_id: 'c1' },
      '/openapi/agent/chat_result': { status: 'completed', conversation_id: 'c1', text: '服务端结果' },
      '/openapi/agent/chat_stream': { status: 'input_required', conversation_id: 'v1' },
      '/openapi/videos/result': { status: 'ok', action: { action_id: 'a1', revision: 1 } },
    }
    res.end(JSON.stringify(responses[req.url] || { status: 'error' }))
  })
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  t.after(() => new Promise(resolve => server.close(resolve)))
  const env = { HOME: home, XIAOJIA_BASE_URL: `http://127.0.0.1:${server.address().port}`, XIAOJIA_API_KEY: 'test-only' }
  const image = await runCLI(['image', '小猫', '--json'], env)
  assert.equal(image.code, 0, image.stderr)
  assert.equal(image.stderr, '')
  assert.deepEqual(JSON.parse(image.stdout).artifacts, [{ type: 'image', url }])
  assert.equal(calls.filter(call => call.path === '/openapi/images/generate').length, 1)
  const chat = await runCLI(['chat', 'hello', '--conversation', 'c1', '--project', 'p1', '--skill', 's1'], env)
  assert.equal(chat.code, 0, chat.stderr)
  assert.match(chat.stdout, /服务端结果/)
  assert.deepEqual(calls.find(call => call.path.endsWith('chat_submit')).body, { message: 'hello', conversation_id: 'c1', project_id: ['p1'], skill_id: ['s1'] })
  const plan = await runCLI(['video', 'plan', '宣传视频', '--json'], env)
  assert.equal(plan.code, 0, plan.stderr)
  assert.equal(calls.find(call => call.path.endsWith('chat_stream')).body.video_plan, true)
  const before = calls.length
  assert.equal((await runCLI(['video', 'approve', 'v1', '--action', 'a1', '--json'], env)).code, 1)
  assert.equal(calls.length, before)
  await runCLI(['video', 'approve', 'v1', '--action', 'a1', '--revision', '1', '--confirm', '--json'], env)
  assert.equal(calls.at(-1).body.pending_action.op, 'approve_pending_action')
  assert.ok(calls.every(call => !call.path.includes('/model/')))
  await assert.rejects(stat(join(home, '.xiaojia/sessions')), { code: 'ENOENT' })
})

test('JSON 预览不下载、不输出终端转义序列', async () => {
  const result = await runCLI(['preview', 'https://example.org/a.png', '--json'])
  assert.equal(result.code, 0)
  assert.equal(result.stderr, '')
  assert.doesNotMatch(result.stdout, /\x1b/)
  assert.equal(JSON.parse(result.stdout).artifacts[0].url, 'https://example.org/a.png')
})
