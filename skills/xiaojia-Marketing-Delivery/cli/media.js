import https from 'node:https'
import { lookup } from 'node:dns/promises'
import { isIP } from 'node:net'
import { open, unlink } from 'node:fs/promises'

export function mediaUrl(raw) {
  if (typeof raw !== 'string' || /[\x00-\x20\x7f-\x9f]/.test(raw)) return null
  try {
    const url = new URL(raw)
    if (url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443')) return null
    return /\.(png|jpe?g|webp|gif|mp4|webm)$/i.test(url.pathname) ? url.href : null
  } catch { return null }
}

export function collectArtifacts(value) {
  const found = new Map()
  const visit = (item, depth = 0) => {
    if (depth > 12 || found.size >= 24) return
    if (typeof item === 'string') {
      const url = mediaUrl(item)
      if (url) found.set(url, { type: /\.(mp4|webm)$/i.test(new URL(url).pathname) ? 'video' : 'image', url })
    } else if (Array.isArray(item)) item.forEach(child => visit(child, depth + 1))
    else if (item && typeof item === 'object') {
      if (item.error || item.denied || item.uncertain || ['failed', 'error'].includes(item.status) || item.generation_status === 'failed') return
      // 只提取媒体结果字段，不把提示词、模型回答或任意文件内容当成图片。
      for (const [key, child] of Object.entries(item)) {
        if (['url', 'image_url', 'image_urls', 'picture_urls', 'images', 'urls', 'video_urls', 'thumbnail_urls', 'artifacts', 'data', 'result', 'video'].includes(key)) visit(child, depth + 1)
      }
    }
  }
  visit(value)
  return [...found.values()]
}

export function publicAddress(address) {
  if (isIP(address) !== 4) return false // 首版仅下载公网 IPv4，避免 IPv6 映射和本地地址绕过。
  const [a, b] = address.split('.').map(Number)
  return !([0, 10, 127, 169].includes(a) || a >= 224 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 100 && b >= 64 && b <= 127) || a === 198)
}

export async function downloadMedia(raw, path, signal, { maxBytes = 100 * 1024 * 1024 } = {}) {
  const url = new URL(raw)
  if (url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443')) throw new Error('下载地址必须是公网 HTTPS 地址')
  const addresses = await lookup(url.hostname, { all: true, family: 4 })
  if (!addresses.length || addresses.some(item => !publicAddress(item.address))) throw new Error('拒绝下载内网地址')
  // 固定校验过的 IP，保留原主机 TLS 验证，禁止 DNS 重绑定和重定向。
  const response = await new Promise((resolve, reject) => {
    const request = https.get(url, { signal, lookup: (_host, options, callback) => options.all ? callback(null, [addresses[0]]) : callback(null, addresses[0].address, 4) }, resolve)
    request.setTimeout(30_000, () => request.destroy(new Error('下载超时')))
    request.on('error', reject)
  })
  if (response.statusCode !== 200) { response.destroy(); throw new Error(`下载失败 HTTP ${response.statusCode}（不跟随重定向）`) }
  let file
  try {
    file = await open(path, 'wx', 0o600)
    let bytes = 0
    for await (const chunk of response) {
      bytes += chunk.length
      if (bytes > maxBytes) throw new Error('媒体超过下载大小上限')
      await file.write(chunk)
    }
  } catch (error) {
    response.destroy()
    if (file) { await file.close(); file = null; await unlink(path) }
    throw error
  } finally { await file?.close() }
}
