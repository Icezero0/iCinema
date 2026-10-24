const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { desktopRuntimeConfig, readConnectionConfig, readDevelopmentApiOrigin } = require('./runtime-config.cjs')

test('backend and websocket origins are explicit and validated', () => {
  assert.deepEqual(desktopRuntimeConfig({}), {
    apiOrigin: 'http://localhost:8000',
    wsOrigin: 'ws://localhost:8000'
  })
  assert.deepEqual(desktopRuntimeConfig({ ICINEMA_API_ORIGIN: 'https://example.com/' }), {
    apiOrigin: 'https://example.com',
    wsOrigin: 'wss://example.com'
  })
  for (const value of ['file:///tmp/', 'http://user@example.com/',
    'https://example.com/path', 'https://example.com/?token=x']) {
    assert.throws(() => desktopRuntimeConfig({ ICINEMA_API_ORIGIN: value }))
  }
  assert.throws(() => desktopRuntimeConfig({ ICINEMA_WS_ORIGIN: 'https://example.com' }))
})

test('saved connection works on double click while environment overrides it', () => {
  const saved = { apiOrigin: 'https://cinema.example', wsOrigin: 'wss://ws.cinema.example' }
  assert.deepEqual(desktopRuntimeConfig({}, saved), saved)
  assert.deepEqual(desktopRuntimeConfig({ ICINEMA_API_ORIGIN: 'https://staging.example' }, saved), {
    apiOrigin: 'https://staging.example',
    wsOrigin: 'wss://staging.example'
  })
})

test('development login uses the same Vite backend origin', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'icinema-vite-env-'))
  try {
    fs.writeFileSync(path.join(tempDir, '.env'), 'VITE_API_ORIGIN=http://localhost:8000\n')
    fs.writeFileSync(path.join(tempDir, '.env.development'), 'VITE_API_ORIGIN=http://192.168.58.1:8000\n')
    assert.equal(readDevelopmentApiOrigin(tempDir, {}), 'http://192.168.58.1:8000')
    assert.equal(readDevelopmentApiOrigin(tempDir, { VITE_API_ORIGIN: 'https://override.example' }), 'https://override.example')
  } finally {
    if (path.dirname(tempDir) !== os.tmpdir()) throw new Error('Unexpected test directory')
    fs.rmSync(tempDir, { recursive: true })
  }
})

test('connection file is created once and later edits are read', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'icinema-connection-'))
  try {
    const file = path.join(tempDir, 'connection.json')
    assert.equal(readConnectionConfig(file, 'https://icinema.site').apiOrigin, 'https://icinema.site')
    fs.writeFileSync(file, '{"apiOrigin":"https://cinema.example"}')
    assert.equal(readConnectionConfig(file, 'https://icinema.site').apiOrigin, 'https://cinema.example')
  } finally {
    if (path.dirname(tempDir) !== os.tmpdir()) throw new Error('Unexpected test directory')
    fs.rmSync(tempDir, { recursive: true })
  }
})
