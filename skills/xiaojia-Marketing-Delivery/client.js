import { randomUUID } from 'node:crypto'

export const CLIENT_SOURCE = 'deepseek-harness'
export const CLIENT_VERSION = '0.1.0'
export const DEFAULT_BASE_URL = 'https://justailab.com'

const IMAGE_MODEL_KEYS = {
  'image-flash': 'google/gemini-3.1-flash-image-preview',
  'image-2': 'apimart-gpt-image-2',
  'doubao-5.0': 'doubao-seedream-5-0-260128',
}

function positiveInteger(value, fallback, fieldName) {
  const resolved = value === undefined ? fallback : Number(value)
  if (!Number.isInteger(resolved) || resolved <= 0) {
    throw new Error(`${fieldName} must be a positive integer.`)
  }
  return resolved
}

function abortError(message) {
  const error = new Error(message)
  error.name = 'AbortError'
  return error
}

function wait(milliseconds, signal) {
  if (signal?.aborted) return Promise.reject(abortError('Xiaojia request was cancelled.'))
  return new Promise((resolve, reject) => {
    const finish = () => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }
    const timer = setTimeout(finish, milliseconds)
    const onAbort = () => {
      clearTimeout(timer)
      signal?.removeEventListener('abort', onAbort)
      reject(abortError('Xiaojia request was cancelled.'))
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

function redact(text, secret) {
  const value = String(text || '')
  return secret ? value.split(secret).join('[REDACTED]') : value
}

function responseMessage(payload, fallback) {
  if (!payload || typeof payload !== 'object') return fallback
  return String(payload.message || payload.msg || payload.code || fallback)
}

export class XiaojiaClient {
  constructor({
    apiKey = '',
    baseUrl = DEFAULT_BASE_URL,
    requestTimeoutMs = 20_000,
    taskTimeoutMs = 300_000,
    pollIntervalMs = 2_000,
    fetchImpl = globalThis.fetch,
  } = {}) {
    if (typeof fetchImpl !== 'function') throw new Error('A fetch implementation is required.')
    this.apiKey = String(apiKey || '').trim()
    this.baseUrl = String(baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, '')
    this.requestTimeoutMs = positiveInteger(requestTimeoutMs, 20_000, 'requestTimeoutMs')
    this.taskTimeoutMs = positiveInteger(taskTimeoutMs, 300_000, 'taskTimeoutMs')
    this.pollIntervalMs = positiveInteger(pollIntervalMs, 2_000, 'pollIntervalMs')
    this.fetchImpl = fetchImpl
  }

  async request(path, payload = {}, { signal, timeoutMs } = {}) {
    if (!this.apiKey) {
      throw new Error('JUSTAI_OPENAPI_API_KEY is not configured. Set an API key or complete Xiaojia Skill login first.')
    }

    const controller = new AbortController()
    const requestTimeout = positiveInteger(timeoutMs, this.requestTimeoutMs, 'timeoutMs')
    const timer = setTimeout(() => controller.abort('timeout'), requestTimeout)
    timer.unref?.()
    const onAbort = () => controller.abort(signal?.reason || 'cancelled')
    signal?.addEventListener('abort', onAbort, { once: true })

    try {
      const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
          'X-Xiaojia-Source': CLIENT_SOURCE,
          'X-Xiaojia-Version': CLIENT_VERSION,
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      })
      const text = await response.text()
      let result
      try {
        result = text ? JSON.parse(text) : {}
      } catch {
        throw new Error(`Xiaojia returned invalid JSON (HTTP ${response.status}).`)
      }
      if (!response.ok) {
        const message = redact(responseMessage(result, `HTTP ${response.status}`), this.apiKey)
        throw new Error(`Xiaojia OpenAPI request failed: ${message}`)
      }
      if (!result || typeof result !== 'object' || Array.isArray(result)) {
        throw new Error('Xiaojia returned a non-object JSON response.')
      }
      return result
    } catch (error) {
      if (controller.signal.aborted) {
        if (signal?.aborted) throw abortError('Xiaojia request was cancelled.')
        throw abortError(`Xiaojia request timed out after ${requestTimeout}ms.`)
      }
      throw error
    } finally {
      clearTimeout(timer)
      signal?.removeEventListener('abort', onAbort)
    }
  }

  async chat({
    message = '',
    conversationId = '',
    projectIds = [],
    skillIds = [],
    formId = '',
    formData,
    waitForCompletion = true,
    timeoutMs = this.taskTimeoutMs,
    signal,
  } = {}) {
    if (!String(message).trim() && !String(formId).trim()) {
      throw new Error('message or form_id is required.')
    }
    if (formData !== undefined && (formData === null || typeof formData !== 'object' || Array.isArray(formData))) {
      throw new Error('form_data must be an object.')
    }
    const payload = {}
    if (String(message).trim()) payload.message = String(message)
    if (String(conversationId).trim()) payload.conversation_id = String(conversationId).trim()
    if (projectIds.length) payload.project_id = projectIds.filter(Boolean)
    if (skillIds.length) payload.skill_id = skillIds.filter(Boolean)
    if (String(formId).trim()) payload.form_id = String(formId).trim()
    if (formData !== undefined) payload.form_data = formData

    const submitted = await this.request('/openapi/agent/chat_submit', payload, { signal })
    if (!waitForCompletion) return submitted
    const resolvedConversationId = String(submitted.conversation_id || conversationId || '').trim()
    if (!resolvedConversationId || !['accepted', 'running', 'pending'].includes(String(submitted.status || ''))) {
      return this.withConversationUrl(submitted, resolvedConversationId)
    }
    return this.pollChat(resolvedConversationId, { timeoutMs, signal })
  }

  withConversationUrl(result, conversationId) {
    if (!conversationId) return result
    return {
      ...result,
      web_url: result.web_url || `${this.baseUrl}/pages/agent/preview?conversation_id=${encodeURIComponent(conversationId)}`,
    }
  }

  async pollChat(conversationId, { timeoutMs = this.taskTimeoutMs, signal } = {}) {
    const deadline = Date.now() + positiveInteger(timeoutMs, this.taskTimeoutMs, 'timeoutMs')
    let result = {}
    while (Date.now() < deadline) {
      result = await this.request(
        '/openapi/agent/chat_result',
        { conversation_id: conversationId },
        { signal, timeoutMs: Math.min(this.requestTimeoutMs, Math.max(deadline - Date.now(), 1)) },
      )
      if (['completed', 'failed'].includes(String(result.status || ''))) {
        return this.withConversationUrl(result, conversationId)
      }
      const remaining = deadline - Date.now()
      if (remaining > 0) await wait(Math.min(this.pollIntervalMs, remaining), signal)
    }
    return this.withConversationUrl(
      { ...result, status: result.status || 'timeout', message: result.message || 'Xiaojia task polling timed out.' },
      conversationId,
    )
  }

  async generateImage({
    prompt,
    model = 'image-2',
    reqKey = '',
    picScale = '3:4',
    templateId = 1,
    conversationId = '',
    negativePrompt = '',
    imageUrls = [],
    rawPrompt = false,
    idempotencyKey = '',
    waitForCompletion = true,
    timeoutMs = this.taskTimeoutMs,
    signal,
  } = {}) {
    if (!String(prompt || '').trim()) throw new Error('prompt is required.')
    if (!Object.hasOwn(IMAGE_MODEL_KEYS, model)) throw new Error(`Unsupported image model: ${model}`)
    if (imageUrls.length > 14) throw new Error('At most 14 reference images are supported.')
    const totalTimeout = positiveInteger(timeoutMs, this.taskTimeoutMs, 'timeoutMs')
    const payload = {
      prompt: String(prompt),
      model,
      req_key: String(reqKey || IMAGE_MODEL_KEYS[model]),
      pic_scale: String(picScale || '3:4'),
      template_id: Number(templateId || 1),
      max_wait_time: Math.ceil(totalTimeout / 1000),
      poll_interval: Math.max(1, Math.ceil(this.pollIntervalMs / 1000)),
      wait_for_completion: false,
      prompt_mode: rawPrompt ? 'raw' : 'enhanced',
      idempotency_key: String(idempotencyKey || randomUUID().replaceAll('-', '')),
    }
    if (String(conversationId).trim()) payload.conversation_id = String(conversationId).trim()
    if (String(negativePrompt).trim()) payload.negative_prompt = String(negativePrompt)
    if (imageUrls.length) payload.image_urls = imageUrls.filter(Boolean)

    const submitted = await this.request('/openapi/images/generate', payload, { signal })
    if (!waitForCompletion || submitted.status !== 'ok') return submitted
    const jobId = String(submitted.job_id || '').trim()
    const generationStatus = String(submitted.generation_status || '').toLowerCase()
    if (!jobId || ['completed', 'failed'].includes(generationStatus)) return submitted
    return this.pollImage(jobId, { timeoutMs: totalTimeout, signal })
  }

  async pollImage(jobId, { timeoutMs = this.taskTimeoutMs, signal } = {}) {
    const deadline = Date.now() + positiveInteger(timeoutMs, this.taskTimeoutMs, 'timeoutMs')
    let result = {}
    while (Date.now() < deadline) {
      result = await this.request(
        '/openapi/images/result',
        { job_id: jobId },
        { signal, timeoutMs: Math.min(this.requestTimeoutMs, Math.max(deadline - Date.now(), 1)) },
      )
      const status = String(result.generation_status || '').toLowerCase()
      if (result.status !== 'ok' || ['completed', 'failed'].includes(status)) return result
      const remaining = deadline - Date.now()
      if (remaining > 0) await wait(Math.min(this.pollIntervalMs, remaining), signal)
    }
    return {
      ...result,
      status: result.status || 'ok',
      generation_status: result.generation_status || 'timeout',
      message: result.message || 'Xiaojia image polling timed out.',
    }
  }
}
