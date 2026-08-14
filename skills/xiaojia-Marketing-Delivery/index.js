import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

import { BUNDLED_SKILL_RANK } from '@deepseek-ai/dsh-skill'
import { defineTool } from '@deepseek-ai/dsh-tools'
import Schema from '@deepseek-ai/schemastery'

import { DEFAULT_BASE_URL, XiaojiaClient } from './client.js'
import { resolveApiKey } from './credentials.js'

export const name = 'xiaojia-marketing-delivery'
export const inject = ['tools', 'skills']

export const Config = Schema.object({
  apiKey: Schema.string().default(''),
  baseUrl: Schema.string().default(DEFAULT_BASE_URL),
  requestTimeoutMs: Schema.number().default(20_000),
  taskTimeoutMs: Schema.number().default(300_000),
  pollIntervalMs: Schema.number().default(2_000),
})

const SKILL_NAME = 'xiaojia-marketing-delivery'
const SKILL_DESCRIPTION = '调用小加完整营销能力，完成营销策划、内容生成、项目资料库引用、Skill 管理、文生图、图生图和结果迭代。'
const SKILL_FILE_URL = new URL('./skills/xiaojia-marketing-delivery/SKILL.md', import.meta.url)
const SKILL_RESOURCE_BASE = {
  kind: 'directory',
  path: fileURLToPath(new URL('./skills/xiaojia-marketing-delivery/', import.meta.url)),
}

function stripFrontmatter(content) {
  return content.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '')
}

function renderJson(_args, value) {
  return [{ type: 'text', text: JSON.stringify(value, null, 2) }]
}

const jsonOutput = {
  schema: { type: 'json' },
  render: renderJson,
}

function copyDefined(source, keys) {
  const target = {}
  for (const key of keys) {
    if (source[key] !== undefined && source[key] !== '') target[key] = source[key]
  }
  return target
}

function requireText(value, fieldName) {
  const resolved = String(value || '').trim()
  if (!resolved) throw new Error(`${fieldName} is required.`)
  return resolved
}

function normalizeEnabledFilter(value) {
  if (value === undefined || value === 'all') return value
  return value === 'true'
}

function buildSkillPayload(args) {
  if (args.operation === 'list') {
    const payload = {
      source: args.source || 'all',
      page: args.page || 1,
      page_size: args.page_size || 20,
    }
    Object.assign(payload, copyDefined(args, ['keyword', 'category', 'sort_by', 'include_details', 'is_featured']))
    const enabled = normalizeEnabledFilter(args.enabled_filter)
    if (enabled !== undefined) payload.enabled = enabled
    return ['/openapi/skills/list', payload]
  }

  const editableFields = [
    'name', 'description', 'prompt_content', 'thumbnail', 'category', 'keywords',
    'market_status', 'review_status', 'load_strategy', 'applicable_stages', 'priority',
    'enabled', 'share_prompt_visible', 'market_prompt_visible', 'thumbnail_file_name',
    'thumbnail_file_data', 'thumbnail_content_type',
  ]
  const payload = copyDefined(args, editableFields)
  if (args.operation === 'create') {
    delete payload.review_status
    delete payload.share_prompt_visible
    payload.name = requireText(args.name, 'name')
    payload.description = requireText(args.description, 'description')
    payload.prompt_content = requireText(args.prompt_content, 'prompt_content')
    return ['/openapi/skills/create', payload]
  }
  const skillId = requireText(args.skill_id, 'skill_id')
  if (args.operation === 'detail') return ['/openapi/skills/detail', { skill_id: skillId }]
  if (args.operation === 'delete') return ['/openapi/skills/delete', { skill_id: skillId }]
  if (args.operation === 'update') {
    delete payload.enabled
    delete payload.thumbnail_file_name
    delete payload.thumbnail_file_data
    delete payload.thumbnail_content_type
    if (!Object.keys(payload).length) throw new Error('At least one editable field is required for update.')
    return ['/openapi/skills/update', { skill_id: skillId, ...payload }]
  }
  throw new Error(`Unsupported skill operation: ${args.operation}`)
}

function registerTools(ctx, client) {
  ctx.tools.register(defineTool({
    name: 'xiaojia_chat',
    description: 'Use Xiaojia to complete a marketing task or continue an existing Xiaojia conversation. This is the primary full-capability tool.',
    parameters: {
      message: { type: 'string', description: 'Marketing request or revision instruction.' },
      conversation_id: { type: 'string', description: 'Existing conversation id for continued iteration.' },
      project_ids: { type: 'array', items: { type: 'string' }, description: 'Optional Xiaojia project or knowledge-base ids.' },
      skill_ids: { type: 'array', items: { type: 'string' }, description: 'Optional Xiaojia Skill ids to preload.' },
      form_id: { type: 'string', description: 'Form id returned when Xiaojia requests structured input.' },
      form_data: { type: 'object', additionalProperties: true, description: 'Structured values for form_id.' },
      wait_for_completion: { type: 'boolean', description: 'Wait for the final result. Defaults to true.' },
      timeout_seconds: { type: 'integer', description: 'Total polling timeout in seconds.' },
    },
    output: jsonOutput,
    async execute(args, exec) {
      return client.chat({
        message: args.message,
        conversationId: args.conversation_id,
        projectIds: args.project_ids || [],
        skillIds: args.skill_ids || [],
        formId: args.form_id,
        formData: args.form_data,
        waitForCompletion: args.wait_for_completion ?? true,
        timeoutMs: args.timeout_seconds === undefined ? undefined : args.timeout_seconds * 1000,
        signal: exec.signal,
      })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'xiaojia_projects',
    description: 'List Xiaojia projects and knowledge bases available to the current account.',
    parameters: {},
    output: jsonOutput,
    execute(_args, exec) {
      return client.request('/openapi/projects/list', {}, { signal: exec.signal })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'xiaojia_skills',
    description: 'List, inspect, create, update, or delete Xiaojia Skills. Mutating operations affect the current Xiaojia account.',
    parameters: {
      operation: { type: 'string', required: true, enum: ['list', 'detail', 'create', 'update', 'delete'] },
      skill_id: { type: 'string' },
      source: { type: 'string', enum: ['all', 'system', 'personal', 'shared', 'market'] },
      enabled_filter: { type: 'string', enum: ['all', 'true', 'false'] },
      keyword: { type: 'string' },
      category: { type: 'string' },
      sort_by: { type: 'string', enum: ['hot', 'latest'] },
      page: { type: 'integer' },
      page_size: { type: 'integer' },
      include_details: { type: 'boolean' },
      is_featured: { type: 'boolean' },
      name: { type: 'string' },
      description: { type: 'string' },
      prompt_content: { type: 'string' },
      thumbnail: { type: 'string' },
      thumbnail_file_name: { type: 'string' },
      thumbnail_file_data: { type: 'string', description: 'PNG/WebP data URI for create.' },
      thumbnail_content_type: { type: 'string', enum: ['image/png', 'image/webp'] },
      keywords: { type: 'string' },
      market_status: { type: 'string', enum: ['off', 'listed'] },
      review_status: { type: 'string' },
      load_strategy: { type: 'string', enum: ['always', 'on_demand', 'manual'] },
      applicable_stages: { type: 'array', items: { type: 'string' } },
      priority: { type: 'integer' },
      enabled: { type: 'boolean' },
      share_prompt_visible: { type: 'boolean' },
      market_prompt_visible: { type: 'boolean' },
    },
    output: jsonOutput,
    async execute(args, exec) {
      const [path, payload] = buildSkillPayload(args)
      return client.request(path, payload, { signal: exec.signal })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'xiaojia_upload_image',
    description: 'Upload a PNG, JPEG, or WebP data URI to Xiaojia and return a reusable Xiaojia COS URL.',
    parameters: {
      file_name: { type: 'string', required: true },
      image_base64: { type: 'string', required: true, description: 'Full data URI, for example data:image/png;base64,...' },
      content_type: { type: 'string', required: true, enum: ['image/png', 'image/jpeg', 'image/webp'] },
    },
    output: jsonOutput,
    execute(args, exec) {
      return client.request('/openapi/images/upload', args, { signal: exec.signal })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'xiaojia_generate_image',
    description: 'Generate or edit marketing images through Xiaojia. Pass Xiaojia COS image_urls for image-to-image.',
    parameters: {
      prompt: { type: 'string', required: true },
      model: { type: 'string', enum: ['image-2', 'image-flash', 'doubao-5.0'] },
      req_key: { type: 'string' },
      pic_scale: { type: 'string' },
      template_id: { type: 'integer' },
      conversation_id: { type: 'string' },
      negative_prompt: { type: 'string' },
      image_urls: { type: 'array', items: { type: 'string' } },
      raw_prompt: { type: 'boolean' },
      idempotency_key: { type: 'string' },
      wait_for_completion: { type: 'boolean' },
      timeout_seconds: { type: 'integer' },
    },
    output: jsonOutput,
    execute(args, exec) {
      return client.generateImage({
        prompt: args.prompt,
        model: args.model,
        reqKey: args.req_key,
        picScale: args.pic_scale,
        templateId: args.template_id,
        conversationId: args.conversation_id,
        negativePrompt: args.negative_prompt,
        imageUrls: args.image_urls || [],
        rawPrompt: args.raw_prompt,
        idempotencyKey: args.idempotency_key,
        waitForCompletion: args.wait_for_completion ?? true,
        timeoutMs: args.timeout_seconds === undefined ? undefined : args.timeout_seconds * 1000,
        signal: exec.signal,
      })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'xiaojia_image_result',
    description: 'Query a previously submitted Xiaojia image generation job.',
    parameters: {
      job_id: { type: 'string', required: true },
    },
    output: jsonOutput,
    execute(args, exec) {
      return client.request('/openapi/images/result', { job_id: args.job_id }, { signal: exec.signal })
    },
  }))

  ctx.tools.register(defineTool({
    name: 'xiaojia_credits',
    description: 'Query the Xiaojia credit balance or paginated credit usage records.',
    parameters: {
      operation: { type: 'string', required: true, enum: ['balance', 'usage'] },
      start_date: { type: 'string' },
      end_date: { type: 'string' },
      conversation_id: { type: 'string' },
      page: { type: 'integer' },
      page_size: { type: 'integer' },
    },
    output: jsonOutput,
    execute(args, exec) {
      if (args.operation === 'balance') {
        return client.request('/openapi/credits/balance', {}, { signal: exec.signal })
      }
      const payload = copyDefined(args, ['start_date', 'end_date', 'conversation_id', 'page', 'page_size'])
      return client.request('/openapi/credits/usage', payload, { signal: exec.signal })
    },
  }))
}

function registerSkill(ctx) {
  const candidate = {
    name: SKILL_NAME,
    description: SKILL_DESCRIPTION,
    invocation: { modelInvocable: true, userInvocable: true },
    provider: SKILL_NAME,
    source: 'bundled',
    resourceBase: SKILL_RESOURCE_BASE,
    rank: BUNDLED_SKILL_RANK,
    locator: SKILL_FILE_URL,
  }
  ctx.skills.registerProvider(() => ({
    name: SKILL_NAME,
    list: () => Promise.resolve([candidate]),
    async get() {
      return {
        name: candidate.name,
        description: candidate.description,
        invocation: candidate.invocation,
        provider: candidate.provider,
        source: candidate.source,
        resourceBase: candidate.resourceBase,
        content: stripFrontmatter(await readFile(SKILL_FILE_URL, 'utf8')),
      }
    },
  }))
}

export function apply(ctx, config = {}) {
  const client = new XiaojiaClient({
    apiKey: resolveApiKey({ configuredValue: config.apiKey }),
    baseUrl: config.baseUrl || process.env.JUSTAI_OPENAPI_BASE_URL || DEFAULT_BASE_URL,
    requestTimeoutMs: config.requestTimeoutMs,
    taskTimeoutMs: config.taskTimeoutMs,
    pollIntervalMs: config.pollIntervalMs,
  })
  registerTools(ctx, client)
  registerSkill(ctx)
}
