import { randomUUID } from 'node:crypto'

export const CLIENT_SOURCE = 'deepseek-harness'
export const CLIENT_VERSION = '0.2.1'
export const DEFAULT_BASE_URL = 'https://justailab.com'

export function validateImageUploadSize(size) {
  if (size <= 0 || size > 10 * 1024 * 1024) {
    throw new Error('invalid_image_size: 请选择 1 字节至 10 MiB 的图片，尚未发起上传。')
  }
}

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
    source = CLIENT_SOURCE,
  } = {}) {
    if (typeof fetchImpl !== 'function') throw new Error('A fetch implementation is required.')
    this.apiKey = String(apiKey || '').trim()
    this.baseUrl = String(baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, '')
    this.requestTimeoutMs = positiveInteger(requestTimeoutMs, 20_000, 'requestTimeoutMs')
    this.taskTimeoutMs = positiveInteger(taskTimeoutMs, 300_000, 'taskTimeoutMs')
    this.pollIntervalMs = positiveInteger(pollIntervalMs, 2_000, 'pollIntervalMs')
    this.fetchImpl = fetchImpl
    this.source = source
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
    if (signal?.aborted) onAbort()

    try {
      const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
        method: 'POST',
        redirect: 'error',
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
          'X-Xiaojia-Source': this.source,
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
        const error = new Error(`Xiaojia OpenAPI request failed: ${message}`)
        if (/^[a-z][a-z0-9_]{0,63}$/.test(result?.code || '')) error.code = result.code
        error.httpStatus = response.status
        throw error
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

  async uploadImage({ filename, contentType, bytes, signal }) {
    validateImageUploadSize(bytes.length)
    let ticket
    try {
      ticket = await this.request('/openapi/images/upload_url', {
        filename,
        content_type: contentType,
        size_bytes: bytes.length,
      }, { signal })
    } catch (error) {
      throw new Error(`${error.code || 'upload_ticket_failed'}: ${error.message} 图片尚未发送。`)
    }
    if (ticket.status !== 'ok' || !ticket.upload_id || ticket.method !== 'PUT'
        || typeof ticket.upload_url !== 'string' || !ticket.upload_url.startsWith('https://') || !ticket.headers) {
      throw new Error('invalid_upload_ticket: 小加未返回有效的 COS 上传凭证，图片尚未发送。请检查服务版本。')
    }

    const { upload_id: uploadId, headers } = ticket
    const confirmHint = `使用同一个 upload_id ${uploadId} 调用 /openapi/images/upload_complete 核对结果。`
    const timeout = AbortSignal.timeout(this.requestTimeoutMs)
    let response
    try {
      response = await this.fetchImpl(ticket.upload_url, {
        method: 'PUT',
        headers: { 'Content-Type': headers['Content-Type'], 'x-cos-acl': headers['x-cos-acl'] },
        body: bytes,
        credentials: 'omit',
        redirect: 'error',
        signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
      })
    } catch {
      throw new Error(`upload_put_unknown: 未取得 COS 上传结果。${confirmHint}`)
    }
    await response.body?.cancel()
    if (!response.ok) {
      throw new Error(`upload_put_rejected: COS 拒绝上传（HTTP ${response.status}），未确认成品。请检查图片或重新申请上传地址。`)
    }

    let confirmed
    try {
      confirmed = await this.request('/openapi/images/upload_complete', { upload_id: uploadId }, { signal })
    } catch (error) {
      if ([401, 403, 404, 410, 422].includes(error.httpStatus)) {
        const action = error.httpStatus === 422 ? '请检查文件或更换参考图。'
          : error.httpStatus === 410 ? '上传已过期，请重新申请上传地址。'
            : '请检查 API Key 及上传归属。'
        throw new Error(`${error.code || 'upload_confirm_rejected'}: ${error.message} ${action}`)
      }
      const reason = error.code ? error.message : '成品确认结果未知。'
      throw new Error(`${error.code || 'upload_confirm_unknown'}: 原图已发送。${reason} ${confirmHint}`)
    }
    if (confirmed.status !== 'ok' || !confirmed.url) {
      throw new Error(`upload_confirm_unknown: 小加未返回成品地址。${confirmHint}`)
    }
    return {
      ...confirmed,
      cos_key: new URL(confirmed.url).pathname,
      content_type: contentType,
      size: bytes.length,
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
    videoPlan = false,
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
    if (videoPlan) payload.video_plan = true
    if (String(message).trim()) payload.message = String(message)
    if (String(conversationId).trim()) payload.conversation_id = String(conversationId).trim()
    if (projectIds.length) payload.project_id = projectIds.filter(Boolean)
    if (skillIds.length) payload.skill_id = skillIds.filter(Boolean)
    if (String(formId).trim()) payload.form_id = String(formId).trim()
    if (formData !== undefined) payload.form_data = formData

    if (videoPlan) {
      const result = await this.request('/openapi/agent/chat_stream', { ...payload, stream: false }, { signal })
      return this.withConversationUrl(result, result.conversation_id || conversationId)
    }

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

  async approveVideo({ conversationId, actionId, revision, priceConfirmationToken, signal } = {}) {
    if (!String(conversationId || '').trim() || !String(actionId || '').trim() || !Number.isInteger(revision) || revision < 1) throw new Error('Video approval requires a conversation, action and current revision.')
    const pending_action = { op: 'approve_pending_action', action_id: actionId, revision }
    if (priceConfirmationToken) pending_action.price_confirmation_token = priceConfirmationToken
    try {
      return await this.request('/openapi/agent/chat_stream', { conversation_id: conversationId, pending_action, stream: false }, { signal, timeoutMs: 150_000 })
    } catch (error) {
      if (error.name !== 'AbortError' && !(error instanceof TypeError)) throw error
      return {
        status: 'pending', submission_status: 'unknown', conversation_id: conversationId, action_id: actionId,
        message: '批准响应超时或连接中断，提交结果尚未确认；请查询视频结果，不要重复批准。',
      }
    }
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
