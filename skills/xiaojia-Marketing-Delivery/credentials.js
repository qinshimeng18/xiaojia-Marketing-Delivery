import { existsSync, readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { isAbsolute, join, resolve } from 'node:path'

const API_KEY_ENV_NAME = 'JUSTAI_OPENAPI_API_KEY'
const CONFIG_PATH_ENV_NAME = 'JUSTAI_OPENAPI_CONFIG'
const DEFAULT_CONFIG_FILE_NAMES = [
  '.codex/justai-openapi-chat.json',
  '.claude/justai-openapi-chat.json',
]

function expandPath(rawPath, home) {
  if (rawPath.startsWith('~/')) return join(home, rawPath.slice(2))
  return isAbsolute(rawPath) ? rawPath : resolve(rawPath)
}

function candidateConfigPaths(env, home) {
  const paths = []
  const explicitPath = String(env[CONFIG_PATH_ENV_NAME] || '').trim()
  if (explicitPath) paths.push(expandPath(explicitPath, home))
  paths.push(...DEFAULT_CONFIG_FILE_NAMES.map(fileName => join(home, fileName)))
  return paths
}

function readApiKeyFromLocalConfig(env, home) {
  for (const path of candidateConfigPaths(env, home)) {
    if (!existsSync(path)) continue
    let config
    try {
      config = JSON.parse(readFileSync(path, 'utf8'))
    } catch (error) {
      throw new Error(`Failed to read Xiaojia login config: ${path} (${error.message})`)
    }
    if (!config || Array.isArray(config) || typeof config !== 'object') continue
    const apiKey = String(config.api_key || '').trim()
    if (apiKey) return apiKey
  }
  return ''
}

function shellRcCandidates(env, home) {
  const shellName = String(env.SHELL || '').trim().split('/').pop()
  const fileNames = shellName === 'zsh'
    ? ['.zshrc', '.bashrc', '.profile']
    : ['bash', 'sh'].includes(shellName)
      ? ['.bashrc', '.profile', '.zshrc']
      : ['.profile', '.zshrc', '.bashrc']
  return fileNames.map(fileName => join(home, fileName))
}

function readApiKeyFromShellRc(env, home) {
  const pattern = /^\s*export\s+JUSTAI_OPENAPI_API_KEY=(["']?)(.*?)\1\s*$/
  for (const path of shellRcCandidates(env, home)) {
    if (!existsSync(path)) continue
    const lines = readFileSync(path, 'utf8').split(/\r?\n/)
    for (let index = lines.length - 1; index >= 0; index -= 1) {
      const match = pattern.exec(lines[index])
      if (match) return match[2].trim()
    }
  }
  return ''
}

export function resolveApiKey({ configuredValue = '', env = process.env, home = homedir() } = {}) {
  return String(configuredValue || '').trim()
    || String(env[API_KEY_ENV_NAME] || '').trim()
    || readApiKeyFromLocalConfig(env, home)
    || readApiKeyFromShellRc(env, home)
}
