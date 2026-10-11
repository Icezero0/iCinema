const assert = require('node:assert/strict')
const test = require('node:test')
const { accountPartition, legacyAccountPartition, isBilibiliPage, bilibiliStatusFromNav } = require('./bilibili-account.cjs')

test('Bilibili login storage is isolated by backend and iCinema user', () => {
  const first = accountPartition('https://cinema.example', 1)
  assert.equal(first, accountPartition('https://cinema.example/', 1))
  assert.match(first, /^icinema-bilibili-[a-f0-9]{32}$/)
  assert.equal(legacyAccountPartition('https://cinema.example', 1), `persist:${first}`)
  assert.notEqual(first, accountPartition('https://cinema.example', 2))
  assert.notEqual(first, accountPartition('https://other.example', 1))
  assert.throws(() => accountPartition('https://cinema.example', 0))
  assert.throws(() => accountPartition('file:///tmp/icinema', 1))
})

test('login windows only navigate to HTTPS Bilibili pages', () => {
  assert.equal(isBilibiliPage('https://www.bilibili.com/'), true)
  assert.equal(isBilibiliPage('https://passport.bilibili.com/login'), true)
  assert.equal(isBilibiliPage('https://www.bilibili.com.evil.example/'), false)
  assert.equal(isBilibiliPage('http://www.bilibili.com/'), false)
  assert.equal(isBilibiliPage('https://name@www.bilibili.com/'), false)
})

test('Bilibili anonymous response is signed out, while genuine API errors stay errors', () => {
  assert.deepEqual(bilibiliStatusFromNav({ code: -101, data: { isLogin: false } }), {
    loggedIn: false, name: '', mid: null, avatarUrl: null
  })
  assert.deepEqual(bilibiliStatusFromNav({ code: 0, data: { isLogin: false } }), {
    loggedIn: false, name: '', mid: null, avatarUrl: null
  })
  assert.deepEqual(bilibiliStatusFromNav({ code: 0, data: {
    isLogin: true, uname: 'Viewer', mid: 123, face: 'https://i0.hdslb.com/bfs/face/avatar.jpg'
  } }), {
    loggedIn: true, name: 'Viewer', mid: 123, avatarUrl: 'https://i0.hdslb.com/bfs/face/avatar.jpg'
  })
  assert.equal(bilibiliStatusFromNav({ code: 0, data: {
    isLogin: true, face: 'https://hdslb.com.evil.example/avatar.jpg'
  } }).avatarUrl, null)
  assert.throws(() => bilibiliStatusFromNav({ code: -412, message: 'risk control' }))
})
