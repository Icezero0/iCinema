const assert = require('node:assert/strict')
const path = require('node:path')
const fs = require('node:fs')
const os = require('node:os')
const test = require('node:test')
const { distributionMode, storageDirectory, migrateLegacyData } = require('./storage-policy.cjs')

test('packaged builds declare their storage mode explicitly', () => {
  assert.equal(distributionMode(false, null), 'development')
  assert.equal(distributionMode(true, { mode: 'portable' }), 'portable')
  assert.equal(distributionMode(true, { mode: 'installed' }), 'installed')
  assert.throws(() => distributionMode(true, null))
})

test('all packaged editions use the Windows user directory, separate from development', () => {
  const exe = path.join('D:\\Apps', 'iCinema', 'iCinema.exe')
  const localAppData = path.join('C:\\Users', 'Example', 'AppData', 'Local')
  assert.equal(storageDirectory('development', exe, localAppData), null)
  assert.equal(storageDirectory('portable', exe, localAppData), path.join(localAppData, 'iCinema'))
  assert.equal(storageDirectory('installed', exe, localAppData), path.join(localAppData, 'iCinema'))
  assert.throws(() => storageDirectory('installed', exe, undefined))
  assert.throws(() => storageDirectory('portable', exe, 'relative'))
})

function migrationFixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'icinema-storage-test-'))
  t.after(() => {
    if (path.dirname(root) !== os.tmpdir() || !path.basename(root).startsWith('icinema-storage-test-')) {
      throw new Error('Unexpected test directory')
    }
    fs.rmSync(root, { recursive: true, force: true })
  })
  const source = path.join(root, 'old', 'data')
  const target = path.join(root, 'profile', 'iCinema')
  fs.mkdirSync(source, { recursive: true })
  return { root, source, target }
}

test('migration preserves login, settings, connection and encrypted credentials without changing the original', t => {
  const { source, target } = migrationFixture(t)
  const files = {
    'connection.json': '{"apiOrigin":"https://custom.example"}',
    'Local State': 'encryption metadata',
    'Local Storage/leveldb/000001.ldb': 'login and preferences',
    'bilibili-accounts/account.enc': 'encrypted credential bytes',
    'IndexedDB/cache/data': 'sticker data',
    'window-state.json': 'window bounds'
  }
  for (const [name, content] of Object.entries(files)) {
    const file = path.join(source, name)
    fs.mkdirSync(path.dirname(file), { recursive: true })
    fs.writeFileSync(file, content)
  }
  fs.mkdirSync(path.join(source, 'Cache'))
  fs.writeFileSync(path.join(source, 'Cache', 'temporary'), 'cache')
  fs.writeFileSync(path.join(source, 'Local Storage', 'leveldb', 'LOCK'), '')
  assert.equal(migrateLegacyData(source, target), true)
  for (const [name, content] of Object.entries(files)) {
    assert.equal(fs.readFileSync(path.join(target, name), 'utf8'), content)
    assert.equal(fs.readFileSync(path.join(source, name), 'utf8'), content)
  }
  assert.equal(fs.existsSync(path.join(target, 'Cache')), false)
  assert.equal(fs.existsSync(path.join(target, 'Local Storage', 'leveldb', 'LOCK')), false)
})

test('migration never overwrites an existing profile or reimports a stale profile', t => {
  const { source, target } = migrationFixture(t)
  fs.writeFileSync(path.join(source, 'settings'), 'old')
  assert.equal(migrateLegacyData(source, target), true)
  fs.writeFileSync(path.join(target, 'settings'), 'new')
  assert.equal(migrateLegacyData(source, target), false)
  assert.equal(fs.readFileSync(path.join(target, 'settings'), 'utf8'), 'new')
})

test('missing legacy profile does not create a destination', t => {
  const { root, target } = migrationFixture(t)
  assert.equal(migrateLegacyData(path.join(root, 'missing'), target), false)
  assert.equal(fs.existsSync(target), false)
})

test('failed migration leaves no partial profile and retains the source', t => {
  const { root, source, target } = migrationFixture(t)
  const other = path.join(root, 'other')
  fs.mkdirSync(other)
  fs.writeFileSync(path.join(other, 'unrelated'), 'keep')
  fs.writeFileSync(path.join(source, 'settings'), 'keep')
  fs.symlinkSync(other, path.join(source, 'unexpected-link'), 'junction')
  assert.throws(() => migrateLegacyData(source, target), /symbolic link/)
  assert.equal(fs.existsSync(target), false)
  assert.deepEqual(fs.readdirSync(path.dirname(target)), [])
  assert.equal(fs.readFileSync(path.join(source, 'settings'), 'utf8'), 'keep')
  assert.equal(fs.readFileSync(path.join(other, 'unrelated'), 'utf8'), 'keep')
})
