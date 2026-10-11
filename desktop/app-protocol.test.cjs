const { test } = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { APP_URL, assetPathForUrl } = require('./app-protocol.cjs')

test('bundled routes fall back to index while assets stay within the build', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'icinema-protocol-'))
  const root = path.join(temporary, 'renderer')
  try {
    fs.mkdirSync(root)
    fs.mkdirSync(path.join(root, 'assets'))
    fs.writeFileSync(path.join(root, 'index.html'), '<html></html>')
    fs.writeFileSync(path.join(root, 'assets', 'app.js'), 'ok')
    fs.writeFileSync(path.join(temporary, 'secret.txt'), 'private')
    assert.equal(assetPathForUrl(APP_URL, root), path.join(root, 'index.html'))
    assert.equal(assetPathForUrl('icinema://app/room/12?tab=chat', root), path.join(root, 'index.html'))
    assert.equal(assetPathForUrl('icinema://app/assets/app.js', root), path.join(root, 'assets', 'app.js'))
    for (const url of [
      'icinema://other/assets/app.js',
      'icinema://app/assets/missing.js',
      'icinema://app/%2e%2e%2fsecret.txt',
      'icinema://app/%00secret',
      'file:///C:/secret'
    ]) {
      assert.equal(assetPathForUrl(url, root), null, url)
    }
  } finally {
    assert.equal(path.dirname(temporary), path.resolve(os.tmpdir()))
    fs.rmSync(temporary, { recursive: true, force: true })
  }
})
