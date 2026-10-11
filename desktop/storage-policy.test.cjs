const assert = require('node:assert/strict')
const path = require('node:path')
const test = require('node:test')
const { distributionMode, storageDirectory } = require('./storage-policy.cjs')

test('packaged builds declare their storage mode explicitly', () => {
  assert.equal(distributionMode(false, null), 'development')
  assert.equal(distributionMode(true, { mode: 'portable' }), 'portable')
  assert.equal(distributionMode(true, { mode: 'installed' }), 'installed')
  assert.throws(() => distributionMode(true, null))
})

test('portable and installed editions keep independent storage directories', () => {
  const exe = path.join('D:\\Apps', 'iCinema', 'iCinema.exe')
  const localAppData = path.join('C:\\Users', 'Example', 'AppData', 'Local')
  assert.equal(storageDirectory('development', exe, localAppData), null)
  assert.equal(storageDirectory('portable', exe, localAppData), path.join('D:\\Apps', 'iCinema', 'data'))
  assert.equal(storageDirectory('installed', exe, localAppData), path.join(localAppData, 'iCinema'))
  assert.throws(() => storageDirectory('installed', exe, undefined))
})
