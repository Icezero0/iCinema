const assert = require('node:assert/strict')
const test = require('node:test')
const fs = require('node:fs/promises')
const os = require('node:os')
const path = require('node:path')
const { EventEmitter } = require('node:events')
const { accountPartition, legacyAccountPartition } = require('./bilibili-account.cjs')
const { createBilibiliSessionStore } = require('./bilibili-session-store.cjs')

function fakeSessionRegistry() {
  const partitions = new Map()
  return {
    fromPartition(partition) {
      if (partitions.has(partition)) return partitions.get(partition)
      const cookies = new EventEmitter()
      const values = []
      cookies.get = async () => values.map(cookie => ({ ...cookie }))
      cookies.set = async details => {
        const domain = details.domain ?? new URL(details.url).hostname
        const cookie = { ...details, domain, hostOnly: !details.domain,
          session: !details.expirationDate }
        const index = values.findIndex(item => item.domain === domain &&
          item.path === details.path && item.name === details.name)
        if (index >= 0) values.splice(index, 1)
        values.push(cookie)
        cookies.emit('changed', {}, cookie, 'explicit', false)
      }
      cookies.flushStore = async () => {}
      const created = {
        storagePath: partition.startsWith('persist:') ? 'legacy-on-disk' : null,
        cookies,
        clearStorageData: async () => { values.splice(0) },
        clearCache: async () => {}
      }
      partitions.set(partition, created)
      return created
    }
  }
}

const fakeSafeStorage = {
  isAsyncEncryptionAvailable: async () => true,
  encryptStringAsync: async value => Buffer.from(`sealed:${Buffer.from(value).toString('base64')}`),
  decryptStringAsync: async value => ({
    result: Buffer.from(value.toString().slice(7), 'base64').toString(),
    shouldReEncrypt: false
  })
}

test('legacy Bilibili cookies migrate into an encrypted vault and in-memory session', async t => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'icinema-bili-vault-'))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  const session = fakeSessionRegistry()
  const partition = accountPartition('https://cinema.example', 7)
  const legacy = legacyAccountPartition('https://cinema.example', 7)
  await session.fromPartition(legacy).cookies.set({
    url: 'https://www.bilibili.com/', domain: '.bilibili.com', path: '/',
    name: 'SESSDATA', value: 'secret-session', secure: true, httpOnly: true
  })
  const store = createBilibiliSessionStore({ session, safeStorage: fakeSafeStorage, storagePath: directory })
  const active = await store.load(partition, legacy)
  assert.equal(active.storagePath, null)
  assert.equal((await active.cookies.get({}))[0].value, 'secret-session')
  assert.equal((await session.fromPartition(legacy).cookies.get({})).length, 0)
  const files = await fs.readdir(path.join(directory, 'bilibili-accounts'))
  assert.equal(files.length, 1)
  const vault = await fs.readFile(path.join(directory, 'bilibili-accounts', files[0]), 'utf8')
  assert.doesNotMatch(vault, /secret-session|SESSDATA/)

  const restarted = fakeSessionRegistry()
  const secondStore = createBilibiliSessionStore({ session: restarted,
    safeStorage: fakeSafeStorage, storagePath: directory })
  const restored = await secondStore.load(partition, legacy)
  assert.equal((await restored.cookies.get({}))[0].value, 'secret-session')
})

test('cookie changes are persisted and logout removes the vault', async t => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'icinema-bili-vault-'))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  const session = fakeSessionRegistry()
  const partition = accountPartition('https://cinema.example', 8)
  const legacy = legacyAccountPartition('https://cinema.example', 8)
  const store = createBilibiliSessionStore({ session, safeStorage: fakeSafeStorage, storagePath: directory })
  const active = await store.load(partition, legacy)
  await active.cookies.set({ url: 'https://passport.bilibili.com/', path: '/',
    name: 'SESSDATA', value: 'new-secret' })
  await store.flushAll()
  const vaultDir = path.join(directory, 'bilibili-accounts')
  assert.equal((await fs.readdir(vaultDir)).length, 1)
  await store.save(partition)
  assert.equal((await fs.readdir(vaultDir)).length, 1)
  await store.clear(partition, legacy)
  assert.equal((await active.cookies.get({})).length, 0)
  assert.equal((await fs.readdir(vaultDir)).length, 0)
})

test('an unavailable encryption key leaves the old login untouched', async t => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'icinema-bili-vault-'))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  const session = fakeSessionRegistry()
  const partition = accountPartition('https://cinema.example', 9)
  const legacy = legacyAccountPartition('https://cinema.example', 9)
  await session.fromPartition(legacy).cookies.set({ url: 'https://www.bilibili.com/',
    path: '/', name: 'SESSDATA', value: 'still-here' })
  const store = createBilibiliSessionStore({ session, safeStorage: {
    isAsyncEncryptionAvailable: async () => false
  }, storagePath: directory })
  await assert.rejects(store.load(partition, legacy), /BILIBILI_SECURE_STORAGE_UNAVAILABLE/)
  assert.equal((await session.fromPartition(legacy).cookies.get({}))[0].value, 'still-here')
})

test('an unreadable vault can be explicitly cleared before logging in again', async t => {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'icinema-bili-vault-'))
  t.after(() => fs.rm(directory, { recursive: true, force: true }))
  const partition = accountPartition('https://cinema.example', 10)
  const legacy = legacyAccountPartition('https://cinema.example', 10)
  const vaultDir = path.join(directory, 'bilibili-accounts')
  await fs.mkdir(vaultDir)
  await fs.writeFile(path.join(vaultDir, `${partition.slice(-32)}.enc`), 'broken')
  const store = createBilibiliSessionStore({ session: fakeSessionRegistry(),
    safeStorage: fakeSafeStorage, storagePath: directory })
  await assert.rejects(store.load(partition, legacy), /BILIBILI_SECURE_STORAGE_UNREADABLE/)
  await store.clear(partition, legacy)
  assert.equal((await fs.readdir(vaultDir)).length, 0)
  assert.equal((await store.load(partition, legacy)).storagePath, null)
})
