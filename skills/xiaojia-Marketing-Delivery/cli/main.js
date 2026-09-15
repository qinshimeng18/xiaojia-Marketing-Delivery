#!/usr/bin/env node
import { parseArgs } from 'node:util'
import { readFile, mkdir, writeFile, realpath, mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve, basename } from 'node:path'
import { pathToFileURL } from 'node:url'
import { CLIClient, loadConfig, login } from './api.js'
import { collectArtifacts, mediaUrl, downloadMedia } from './media.js'
import { Marked } from 'marked'
import { markedTerminal } from 'marked-terminal'
import ora from 'ora'
import terminalImage from 'term-img'

const HELP = `小加 CLI — 原有 Skill / OpenAPI 的轻量命令行封装

  xiaojia login                         登录小加
  xiaojia doctor                        检查连接和凭证，不调用模型
  xiaojia chat "营销需求"                 调用服务端小加
  xiaojia chat "继续修改" --conversation ID
  xiaojia chat-result ID                 查询已有对话结果
  xiaojia image "图片描述"                生成图片并自动内嵌显示
  xiaojia image-result JOB_ID            查询已有图片任务
  xiaojia preview HTTPS_URL              显示已有图片，不重新生成
  xiaojia projects | skills | credits    查询资料库、技能或积分
  xiaojia video plan "视频需求"           生成方案，暂不提交视频生成
  xiaojia video result ID                查询方案或视频结果
  xiaojia video approve ID --action ACTION --revision N --confirm
  xiaojia video reject ID --action ACTION

选项：--json 结构化输出；--output FILE 保存结果；--download DIR 下载媒体
      --conversation ID 续聊；--project ID / --skill ID 可重复指定
      --model image-2|image-flash|doubao-5.0；--scale 3:4
      --price-token TOKEN 确认最新视频报价；--no-preview 关闭图片展示
生图及营销任务使用小加积分；视频批准必须显式确认。
在 iTerm2 中自动显示原图；没有本地 Agent、文件编辑或系统命令执行。
环境：XIAOJIA_BASE_URL / XIAOJIA_API_KEY；兼容既有 Skill 登录配置。
`

export const safe = value => String(value).replace(/\x1b(?:\][^\x07]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~])/g, '').replace(/[\x00-\x08\x0b-\x1f\x7f-\x9f]/g, '')

export function renderMarkdown(text, width = 80) {
  const renderer = new Marked(markedTerminal({ width: Math.max(20, width), reflowText: true, showSectionPrefix: false, unescape: false }))
  return renderer.parse(safe(text)).trimEnd()
}

export function inlineImagesSupported(env = process.env) {
  return ['iTerm.app', 'WezTerm', 'vscode', 'rio'].includes(env.TERM_PROGRAM) || Boolean(env.KONSOLE_VERSION)
}

async function previewArtifact(artifact, signal) {
  if (artifact.type !== 'image' || !process.stdout.isTTY || !inlineImagesSupported()) return false
  const directory = await mkdtemp(join(tmpdir(), 'xiaojia-preview-'))
  try {
    const file = join(directory, 'image')
    await downloadMedia(artifact.url, file, signal, { maxBytes: 20 * 1024 * 1024 })
    const output = terminalImage(await readFile(file), { width: Math.min(process.stdout.columns || 80, 64), height: 20, preserveAspectRatio: true, fallback: () => '' })
    if (output) process.stdout.write(output + '\n')
    return Boolean(output)
  } finally { await rm(directory, { recursive: true, force: true }) }
}

export async function main(argv = process.argv.slice(2)) {
  const { values, positionals } = parseArgs({ args: argv, allowPositionals: true, options: {
    help: { type: 'boolean', short: 'h' }, json: { type: 'boolean' }, 'no-preview': { type: 'boolean' },
    output: { type: 'string' }, download: { type: 'string' }, conversation: { type: 'string' },
    project: { type: 'string', multiple: true }, skill: { type: 'string', multiple: true },
    model: { type: 'string' }, scale: { type: 'string' }, action: { type: 'string' },
    revision: { type: 'string' }, confirm: { type: 'boolean' }, 'price-token': { type: 'string' },
  } })
  if (values.help || !positionals.length) {
    console.log(values.json ? JSON.stringify({ help: HELP }) : HELP); return
  }
  const command = positionals[0]
  if (!['login', 'doctor', 'chat', 'chat-result', 'image', 'image-result', 'preview', 'projects', 'skills', 'credits', 'video'].includes(command)) {
    throw new Error('未知命令；本地 Agent 已移除，请用 xiaojia chat "需求" 或 xiaojia --help')
  }
  const controller = new AbortController()
  const interrupt = () => controller.abort(new Error('已中断，不会自动重新提交任务'))
  process.on('SIGINT', interrupt)
  const spinner = ora({ stream: process.stderr, isEnabled: Boolean(process.stderr.isTTY && !values.json), isSilent: Boolean(values.json || !process.stderr.isTTY), discardStdin: false })
  const log = message => { spinner.stop(); console.error(safe(message)) }
  const emit = async result => {
    spinner.stop()
    const artifacts = collectArtifacts(result)
    const json = JSON.stringify({ ...result, artifacts }, null, 2)
    if (values.output) await writeFile(resolve(values.output), json + '\n', { flag: 'wx', mode: 0o600 })
    if (values.download) {
      const destination = resolve(values.download); await mkdir(destination, { recursive: true })
      for (const [index, artifact] of artifacts.entries()) {
        await downloadMedia(artifact.url, join(destination, `${index + 1}-${basename(new URL(artifact.url).pathname) || 'media'}`), controller.signal)
      }
    }
    if (values.json) console.log(json)
    else {
      for (const [index, artifact] of artifacts.entries()) {
        console.log(`\n${artifact.type === 'image' ? '图片' : '视频'} ${index + 1}`)
        let previewed = false
        if (!values['no-preview']) {
          try { previewed = await previewArtifact(artifact, controller.signal) }
          catch { log('图片预览暂不可用，生成结果仍已保留。') }
        }
        if (!previewed) {
          if (artifact.type === 'image' && process.stdout.isTTY && !values['no-preview']) log('未能内嵌显示原图，可在 iTerm2 中使用自动预览。')
          console.log(artifact.url)
        }
      }
      console.log(renderMarkdown(humanResult(result, JSON.stringify(result, null, 2))))
      if (result.conversation_id) console.log(`会话：${safe(result.conversation_id)}`)
      if (result.job_id) console.log(`任务：${safe(result.job_id)}`)
    }
    if (result.status === 'error' || result.status === 'failed' || (typeof result.status === 'number' && result.status < 0) || result.generation_status === 'failed') process.exitCode = 1
    else if (['running', 'pending', 'timeout'].includes(result.status) || ['pending', 'running', 'timeout'].includes(result.generation_status)) process.exitCode = 2
  }
  try {
    if (command === 'preview') {
      const url = mediaUrl(positionals[1])
      if (!url) throw new Error('请提供 HTTPS 图片或视频地址')
      await emit({ status: 'ok', artifacts: collectArtifacts({ url }) }); return
    }
    const config = await loadConfig()
    if (command === 'login') { await login(config, { signal: controller.signal, log }); await emit({ status: 'ok', message: '登录成功' }); return }
    if (!config.apiKey) throw new Error('尚未登录，请运行 xiaojia login')
    const client = new CLIClient(config)
    if (command === 'doctor') {
      await client.checkReady({ signal: controller.signal })
      await emit({ status: 'ok', message: '连接正常，凭证有效；未调用模型。', base_url: config.baseUrl }); return
    }
    spinner.start(command === 'image' ? '正在生成图片…' : '请求小加…')
    const options = { signal: controller.signal }
    if (['projects', 'skills', 'credits'].includes(command)) { await emit(await client.call(command === 'credits' ? '/openapi/credits/balance' : `/openapi/${command}/list`, {}, options)); return }
    if (['chat-result', 'image-result'].includes(command)) {
      if (!positionals[1]) throw new Error('缺少任务或会话 ID')
      await emit(await client.call(command === 'chat-result' ? '/openapi/agent/chat_result' : '/openapi/images/result', command === 'chat-result' ? { conversation_id: positionals[1] } : { job_id: positionals[1] }, options)); return
    }
    if (command === 'chat') { await emit(await client.chat({ message: positionals.slice(1).join(' '), conversationId: values.conversation, projectIds: values.project || [], skillIds: values.skill || [], ...options })); return }
    if (command === 'image') { await emit(await client.generateImage({ prompt: positionals.slice(1).join(' '), conversationId: values.conversation, model: values.model, picScale: values.scale, ...options })); return }
    if (command === 'video') {
      const [operation, id] = positionals.slice(1)
      if (operation === 'plan') {
        if (!positionals.slice(2).join(' ').trim()) throw new Error('缺少视频需求')
        const result = await client.chat({ videoPlan: true, message: `请生成视频方案，展示分镜和预计积分，等待我确认后再生成视频。需求：${positionals.slice(2).join(' ')}`, conversationId: values.conversation, signal: controller.signal })
        if (result.conversation_id) {
          try { result.video = await client.call('/openapi/videos/result', { conversation_id: result.conversation_id }, options) } catch { /* 尚未形成视频方案时保留原始结果 */ }
        }
        await emit(result); return
      }
      if (!id) throw new Error('缺少视频会话 ID')
      if (operation === 'result') { await emit(await client.call('/openapi/videos/result', { conversation_id: id }, options)); return }
      if (!['approve', 'reject'].includes(operation) || !values.action) throw new Error('请提供 approve/reject 及 --action')
      if (operation === 'approve' && (!values.confirm || !Number.isInteger(Number(values.revision)) || Number(values.revision) < 1)) throw new Error('批准视频会产生费用，必须提供 --revision N --confirm')
      const pending = { op: `${operation}_pending_action`, action_id: values.action }
      if (operation === 'approve') { pending.revision = Number(values.revision); if (values['price-token']) pending.price_confirmation_token = values['price-token'] }
      await emit(await client.request('/openapi/agent/chat_stream', { conversation_id: id, pending_action: pending, stream: false }, options)); return
    }
  } finally {
    spinner.stop(); process.removeListener('SIGINT', interrupt)
  }
}

function humanResult(result, json) {
  if (result.status === 'ok' && result.artifacts?.length) return ''
  if (typeof result.text === 'string' && result.text) return result.text
  if (typeof result.content === 'string' && result.content) return result.content
  if (!result.input_required && !result.video && !result.action && typeof result.message === 'string') return result.message
  if (result.generation_status === 'completed' && collectArtifacts(result).length && !result.video) return '生成完成。'
  const video = result.video || result
  const action = video.action || result.input_required
  if (!action || (!action.action_id && action.type !== 'video_confirmation')) return json
  const lines = [action.summary || '视频方案', `状态：${video.generation_status || action.status || '待确认'}`, `会话：${result.conversation_id}`, `方案：${action.action_id} · 版本 ${action.revision || 1}`]
  if (action.display_estimated_credits !== undefined) lines.push(`预计视频积分：${action.display_estimated_credits}`)
  if (action.params?.script) lines.push('', action.params.script)
  if (video.video_urls?.length) lines.push('', ...video.video_urls)
  if (['pending', undefined].includes(action.status) && !video.job_id) lines.push('', `确认生成：xiaojia video approve ${result.conversation_id} --action ${action.action_id} --revision ${action.revision || 1} --confirm`)
  if (result.web_url) lines.push('', result.web_url)
  return lines.join('\n')
}

if (process.argv[1] && import.meta.url === pathToFileURL(await realpath(process.argv[1])).href) {
  main().catch(error => {
    if (process.argv.includes('--json')) console.log(JSON.stringify({ status: 'error', message: safe(error.message) }))
    else console.error(safe(error.message))
    process.exitCode = 1
  })
}
