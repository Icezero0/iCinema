const { test } = require('node:test')
const assert = require('node:assert/strict')
const { appUrlFromEnvironment, navigationTarget } = require('./navigation.cjs')

test('desktop app URL defaults to the existing Vite server', () => {
  assert.equal(appUrlFromEnvironment(), 'http://localhost:5173/')
  assert.equal(appUrlFromEnvironment('https://icinema.example/'), 'https://icinema.example/')
  for (const value of ['file:///tmp/index.html', 'https://user@icinema.example/',
    'https://icinema.example/room/1', 'https://icinema.example/?next=evil']) {
    assert.throws(() => appUrlFromEnvironment(value))
  }
})

test('only app-origin navigation stays in Electron', () => {
  const origin = 'http://localhost:5173'
  assert.equal(navigationTarget('http://localhost:5173/room/1', origin), 'internal')
  assert.equal(navigationTarget('https://www.bilibili.com/', origin), 'external')
  assert.equal(navigationTarget('mailto:test@example.com', origin), 'external')
  for (const value of ['javascript:alert(1)', 'file:///C:/secret',
    'http://localhost:5173.evil.test/', 'icinema-probe://app/']) {
    assert.notEqual(navigationTarget(value, origin), 'internal')
  }
})
