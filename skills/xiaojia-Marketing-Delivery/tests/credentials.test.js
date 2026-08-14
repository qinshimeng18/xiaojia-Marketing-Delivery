import assert from 'node:assert/strict'
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import test from 'node:test'

import { resolveApiKey } from '../credentials.js'

test('reads the API key persisted by the existing Python login flow', async t => {
  const home = await mkdtemp(join(tmpdir(), 'xiaojia-credentials-'))
  t.after(() => rm(home, { recursive: true, force: true }))
  await mkdir(join(home, '.codex'), { recursive: true })
  await writeFile(
    join(home, '.codex', 'justai-openapi-chat.json'),
    JSON.stringify({ api_key: 'persisted-key' }),
  )

  assert.equal(resolveApiKey({ env: {}, home }), 'persisted-key')
})

test('uses the existing shell rc fallback when the local JSON config is absent', async t => {
  const home = await mkdtemp(join(tmpdir(), 'xiaojia-credentials-'))
  t.after(() => rm(home, { recursive: true, force: true }))
  await writeFile(join(home, '.zshrc'), 'export JUSTAI_OPENAPI_API_KEY="shell-key"\n')

  assert.equal(resolveApiKey({ env: { SHELL: '/bin/zsh' }, home }), 'shell-key')
})

test('keeps explicit plugin configuration and environment variables higher priority', async () => {
  assert.equal(
    resolveApiKey({ configuredValue: 'configured-key', env: { JUSTAI_OPENAPI_API_KEY: 'env-key' } }),
    'configured-key',
  )
  assert.equal(resolveApiKey({ env: { JUSTAI_OPENAPI_API_KEY: 'env-key' } }), 'env-key')
})
