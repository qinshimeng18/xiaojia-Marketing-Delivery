import { chmod, mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { dirname, join } from 'node:path'
import { randomUUID } from 'node:crypto'
import { XiaojiaClient, DEFAULT_BASE_URL } from '../client.js'
import { resolveApiKey } from '../credentials.js'

export function validateBaseUrl(value) {
  const url = new URL(value)
  if (url.username || url.password || url.search || url.hash || url.pathname !== '/') throw new Error('API 地址只能包含协议、主机和端口')
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname))) throw new Error('API 必须使用 HTTPS；仅本机联调允许 HTTP')
  return url.origin
}

export async function loadConfig(env = process.env, home = homedir()) {
  let path = env.JUSTAI_OPENAPI_CONFIG || join(home, '.xiaojia/config.json')
  let dedicated = !env.JUSTAI_OPENAPI_CONFIG
  let config = {}
  try { config = JSON.parse(await readFile(path, 'utf8')) } catch (error) {
    if (error.code !== 'ENOENT') throw error
    dedicated = false
    if (!env.JUSTAI_OPENAPI_CONFIG) {
      try { config = JSON.parse(await readFile(join(home, '.codex/justai-openapi-chat.json'), 'utf8')) } catch (legacyError) { if (legacyError.code !== 'ENOENT') throw legacyError }
    }
  }
  // CLI独立连接不受旧Skill的全局环境变量覆盖；显式CLI环境变量仍最高优先。
  env = { ...env,
    JUSTAI_OPENAPI_BASE_URL: env.XIAOJIA_BASE_URL || (dedicated ? undefined : env.JUSTAI_OPENAPI_BASE_URL),
    JUSTAI_OPENAPI_API_KEY: env.XIAOJIA_API_KEY || (dedicated ? undefined : env.JUSTAI_OPENAPI_API_KEY),
  }
  const baseUrl = validateBaseUrl(env.JUSTAI_OPENAPI_BASE_URL || config.base_url || DEFAULT_BASE_URL)
  if (config.api_key && !env.JUSTAI_OPENAPI_API_KEY && baseUrl !== validateBaseUrl(config.base_url || DEFAULT_BASE_URL)) throw new Error('API 地址与已保存凭证不匹配，请针对新地址重新登录或显式设置 API Key')
  // 不把默认站点的旧凭证自动发送给自定义服务器。
  const apiKey = env.JUSTAI_OPENAPI_API_KEY || config.api_key || (baseUrl === DEFAULT_BASE_URL ? resolveApiKey({ env, home }) : '')
  return { path, baseUrl, apiKey }
}

export async function saveConfig(config, apiKey) {
  await mkdir(dirname(config.path), { recursive: true, mode: 0o700 })
  const temporary = `${config.path}.${randomUUID()}.tmp`
  await writeFile(temporary, JSON.stringify({ base_url: config.baseUrl, api_key: apiKey }, null, 2), { flag: 'wx', mode: 0o600 })
  await rename(temporary, config.path)
  await chmod(config.path, 0o600)
}

export class CLIClient extends XiaojiaClient {
  constructor(config) { super({ ...config, source: 'xiaojia-cli', requestTimeoutMs: 150_000 }) }

  async checkReady({ signal } = {}) {
    const result = await this.call('/openapi/credits/balance', {}, { signal })
    if (result.status !== 'ok' || !Number.isFinite(result.available_credits)) throw new Error('积分接口响应异常，请检查服务地址与后端版本')
    return result
  }

  async call(path, payload = {}, options = {}) {
    const result = await this.request(path, payload, options)
    if (result.status === 'error' || result.status === 'failed' || (typeof result.status === 'number' && result.status < 0)) {
      const message = String(result.message || result.msg || result.code || '小加请求失败')
      throw new Error(this.apiKey ? message.split(this.apiKey).join('[REDACTED]') : message)
    }
    return result
  }
}

export async function login(config, { signal, log = console.error } = {}) {
  async function call(path, payload = {}) {
    const response = await fetch(`${config.baseUrl}${path}`, {
      method: 'POST', redirect: 'error', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(20_000)]) : AbortSignal.timeout(20_000),
    })
    const result = await response.json()
    if (!response.ok || result.status === 'error') throw new Error(result.message || '登录失败')
    return result
  }
  const start = await call('/openapi/auth/login/start')
  if (!start.login_token) throw new Error('登录接口未返回登录令牌')
  log(`请在浏览器登录：${config.baseUrl}/login?login_token=${encodeURIComponent(start.login_token)}`)
  const deadline = Date.now() + 300_000
  while (Date.now() < deadline) {
    signal?.throwIfAborted()
    const result = await call('/openapi/auth/login/result', { login_token: start.login_token })
    if (result.status === 'success' && result.api_key) { await saveConfig(config, result.api_key); return }
    if (['expired', 'failed'].includes(result.status)) throw new Error('登录已过期，请重新运行 xiaojia login')
    await new Promise(resolve => setTimeout(resolve, 1500))
  }
  throw new Error('登录等待超时，请重新登录')
}
