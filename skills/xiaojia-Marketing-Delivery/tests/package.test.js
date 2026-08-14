import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import test from 'node:test'

const execFileAsync = promisify(execFile)
const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

test('package exposes a public installable DSH bundle', async () => {
  const packageJson = JSON.parse(await readFile(resolve(packageRoot, 'package.json'), 'utf8'))

  assert.equal(packageJson.name, 'dsh-xiaojia-marketing-delivery')
  assert.equal(packageJson.private, undefined)
  assert.equal(packageJson.publishConfig.access, 'public')
  assert.equal(packageJson.dsh.bundle.patch, './cordis.patch.yml')
  assert.equal(packageJson.repository.directory, 'skills/xiaojia-Marketing-Delivery')
  assert.ok(packageJson.keywords.includes('dsh-plugin'))
})

test('npm package contains the runtime and bundled Skill only', async () => {
  const { stdout } = await execFileAsync(
    'npm',
    ['pack', '--dry-run', '--json', '--ignore-scripts'],
    { cwd: packageRoot },
  )
  const files = JSON.parse(stdout)[0].files.map(item => item.path)

  for (const expected of [
    'client.js',
    'cordis.patch.yml',
    'credentials.js',
    'index.js',
    'package.json',
    'skills/xiaojia-marketing-delivery/SKILL.md',
  ]) {
    assert.ok(files.includes(expected), `missing package file: ${expected}`)
  }
  assert.equal(files.some(path => path.startsWith('tests/')), false)
  assert.equal(files.some(path => path.startsWith('scripts/')), false)
})
