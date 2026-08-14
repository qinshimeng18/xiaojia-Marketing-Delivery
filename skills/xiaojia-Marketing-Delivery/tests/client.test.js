import assert from 'node:assert/strict'
import test from 'node:test'

import { CLIENT_SOURCE, CLIENT_VERSION, XiaojiaClient } from '../client.js'

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function queuedFetch(responses, calls = []) {
  return async (url, options) => {
    calls.push({ url, options })
    const next = responses.shift()
    if (!next) throw new Error('Unexpected fetch call.')
    return typeof next === 'function' ? next(url, options) : next
  }
}

test('request adds bearer auth and DeepSeek Harness attribution headers', async () => {
  const calls = []
  const client = new XiaojiaClient({
    apiKey: 'secret-key',
    baseUrl: 'https://example.test/',
    fetchImpl: queuedFetch([jsonResponse({ status: 'ok' })], calls),
  })

  const result = await client.request('/openapi/projects/list', {})

  assert.equal(result.status, 'ok')
  assert.equal(calls[0].url, 'https://example.test/openapi/projects/list')
  assert.equal(calls[0].options.headers.Authorization, 'Bearer secret-key')
  assert.equal(calls[0].options.headers['X-Xiaojia-Source'], CLIENT_SOURCE)
  assert.equal(calls[0].options.headers['X-Xiaojia-Version'], CLIENT_VERSION)
})

test('chat submits once and polls until the final result', async () => {
  const calls = []
  const client = new XiaojiaClient({
    apiKey: 'key',
    pollIntervalMs: 1,
    fetchImpl: queuedFetch([
      jsonResponse({ status: 'accepted', conversation_id: 'cvt_1' }),
      jsonResponse({ status: 'running', conversation_id: 'cvt_1' }),
      jsonResponse({ status: 'completed', conversation_id: 'cvt_1', content: 'done' }),
    ], calls),
  })

  const result = await client.chat({
    message: '生成营销方案',
    projectIds: ['project_1'],
    skillIds: ['skill_1'],
    timeoutMs: 1_000,
  })

  assert.equal(result.status, 'completed')
  assert.equal(result.content, 'done')
  assert.equal(result.web_url, 'https://justailab.com/pages/agent/preview?conversation_id=cvt_1')
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    message: '生成营销方案',
    project_id: ['project_1'],
    skill_id: ['skill_1'],
  })
  assert.equal(calls.filter(call => call.url.endsWith('/openapi/agent/chat_result')).length, 2)
})

test('image generation maps the friendly model and keeps reference images', async () => {
  const calls = []
  const client = new XiaojiaClient({
    apiKey: 'key',
    fetchImpl: queuedFetch([
      jsonResponse({ status: 'ok', generation_status: 'pending', job_id: 'job_1' }),
    ], calls),
  })

  const result = await client.generateImage({
    prompt: '咖啡店开业海报',
    model: 'image-2',
    imageUrls: ['https://example.test/reference.png'],
    waitForCompletion: false,
  })

  assert.equal(result.job_id, 'job_1')
  const payload = JSON.parse(calls[0].options.body)
  assert.equal(payload.req_key, 'apimart-gpt-image-2')
  assert.equal(payload.wait_for_completion, false)
  assert.deepEqual(payload.image_urls, ['https://example.test/reference.png'])
  assert.match(payload.idempotency_key, /^[a-f0-9]{32}$/)
})

test('HTTP errors redact the configured API key', async () => {
  const client = new XiaojiaClient({
    apiKey: 'top-secret',
    fetchImpl: queuedFetch([
      jsonResponse({ status: 'error', message: 'bad top-secret credential' }, 401),
    ]),
  })

  await assert.rejects(
    client.request('/openapi/projects/list', {}),
    error => {
      assert.doesNotMatch(error.message, /top-secret/)
      assert.match(error.message, /\[REDACTED\]/)
      return true
    },
  )
})

test('missing API key fails before any network request', async () => {
  let called = false
  const client = new XiaojiaClient({
    fetchImpl: async () => {
      called = true
      return jsonResponse({})
    },
  })

  await assert.rejects(client.request('/openapi/projects/list', {}), /JUSTAI_OPENAPI_API_KEY/)
  assert.equal(called, false)
})
