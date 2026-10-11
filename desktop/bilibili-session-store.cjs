const fs = require('node:fs/promises')
const path = require('node:path')
const { randomBytes } = require('node:crypto')

const PARTITION_PATTERN = /^icinema-bilibili-([a-f0-9]{32})$/

function isBilibiliCookie(cookie) {
  const domain = String(cookie?.domain ?? '').replace(/^\./, '').toLowerCase()
  return domain === 'bilibili.com' || domain.endsWith('.bilibili.com')
}

function cookieDetails(cookie) {
  if (!isBilibiliCookie(cookie) || typeof cookie.name !== 'string' ||
      typeof cookie.value !== 'string') return null
  const domain = cookie.domain.replace(/^\./, '').toLowerCase()
  const cookiePath = typeof cookie.path === 'string' && cookie.path.startsWith('/')
    ? cookie.path : '/'
  const details = {
    url: `https://${domain}${cookiePath}`,
    name: cookie.name,
    value: cookie.value,
    path: cookiePath,
    secure: Boolean(cookie.secure),
    httpOnly: Boolean(cookie.httpOnly)
  }
  if (!cookie.hostOnly) details.domain = cookie.domain
  if (typeof cookie.expirationDate === 'number') {
    if (cookie.expirationDate <= Date.now() / 1000) return null
    details.expirationDate = cookie.expirationDate
  }
  if (['unspecified', 'no_restriction', 'lax', 'strict'].includes(cookie.sameSite)) {
    details.sameSite = cookie.sameSite
  }
  return details
}

function snapshotCookie(cookie) {
  const details = cookieDetails(cookie)
  return details ? { ...details, domain: cookie.domain, hostOnly: Boolean(cookie.hostOnly) } : null
}

function createBilibiliSessionStore({ session, safeStorage, storagePath }) {
  const states = new Map()
  const vaultDir = path.join(storagePath, 'bilibili-accounts')

  function vaultPath(partition) {
    const match = PARTITION_PATTERN.exec(partition)
    if (!match) throw new Error('INVALID_BILIBILI_PARTITION')
    return path.join(vaultDir, `${match[1]}.enc`)
  }

  async function encryptionReady() {
    if (!await safeStorage.isAsyncEncryptionAvailable()) {
      throw new Error('BILIBILI_SECURE_STORAGE_UNAVAILABLE')
    }
  }

  async function writeVault(partition, cookies) {
    await encryptionReady()
    const encrypted = await safeStorage.encryptStringAsync(JSON.stringify({ version: 1, cookies }))
    await fs.mkdir(vaultDir, { recursive: true })
    const target = vaultPath(partition)
    const temporary = `${target}.${randomBytes(8).toString('hex')}.tmp`
    try {
      await fs.writeFile(temporary, encrypted, { flag: 'wx', mode: 0o600 })
      await fs.rename(temporary, target)
    } finally {
      await fs.rm(temporary, { force: true })
    }
  }

  async function readVault(partition) {
    let encrypted
    try {
      encrypted = await fs.readFile(vaultPath(partition))
    } catch (error) {
      if (error.code === 'ENOENT') return null
      throw error
    }
    await encryptionReady()
    let payload
    let shouldReEncrypt
    try {
      const decrypted = await safeStorage.decryptStringAsync(encrypted)
      payload = JSON.parse(decrypted.result)
      shouldReEncrypt = decrypted.shouldReEncrypt
    } catch {
      throw new Error('BILIBILI_SECURE_STORAGE_UNREADABLE')
    }
    if (payload?.version !== 1 || !Array.isArray(payload.cookies) || payload.cookies.length > 512) {
      throw new Error('BILIBILI_SECURE_STORAGE_UNREADABLE')
    }
    return { cookies: payload.cookies, shouldReEncrypt }
  }

  async function saveState(state) {
    if (state.suspended) return
    const cookies = (await state.biliSession.cookies.get({})).map(snapshotCookie).filter(Boolean)
    await writeVault(state.partition, cookies)
  }

  function save(partition) {
    const state = states.get(partition)
    if (!state) throw new Error('BILIBILI_SESSION_NOT_LOADED')
    clearTimeout(state.timer)
    state.timer = null
    state.queue = state.queue.catch(() => {}).then(() => saveState(state))
    return state.queue
  }

  async function load(partition, legacyPartition) {
    vaultPath(partition)
    if (legacyPartition !== `persist:${partition}`) throw new Error('INVALID_BILIBILI_PARTITION')
    const existing = states.get(partition)
    if (existing) return existing.ready
    const biliSession = session.fromPartition(partition, { cache: false })
    if (biliSession.storagePath !== null) throw new Error('BILIBILI_SESSION_MUST_BE_IN_MEMORY')
    const state = { partition, biliSession, queue: Promise.resolve(), timer: null,
      suspended: true, ready: null }
    states.set(partition, state)
    state.ready = (async () => {
      await encryptionReady()
      const vault = await readVault(partition)
      if (vault) {
        for (const cookie of vault.cookies) {
          const details = cookieDetails(cookie)
          if (details) await biliSession.cookies.set(details)
        }
        if (vault.shouldReEncrypt) await writeVault(partition, vault.cookies)
      } else {
        // Migrate the previous persistent partition only after encryption succeeds.
        const legacySession = session.fromPartition(legacyPartition)
        const cookies = (await legacySession.cookies.get({})).map(snapshotCookie).filter(Boolean)
        if (cookies.length) {
          await writeVault(partition, cookies)
          for (const cookie of cookies) await biliSession.cookies.set(cookieDetails(cookie))
        }
      }
      const legacySession = session.fromPartition(legacyPartition)
      await legacySession.clearStorageData()
      await legacySession.clearCache()
      await legacySession.cookies.flushStore()
      state.suspended = false
      biliSession.cookies.on('changed', (_event, cookie) => {
        if (!state.suspended && isBilibiliCookie(cookie)) {
          clearTimeout(state.timer)
          state.timer = setTimeout(() => {
            void save(partition).catch(() => {})
          }, 250)
        }
      })
      return biliSession
    })().catch(error => {
      states.delete(partition)
      throw error
    })
    return state.ready
  }

  async function clear(partition, legacyPartition) {
    const state = states.get(partition)
    if (state) {
      await state.ready.catch(() => {})
      state.suspended = true
      clearTimeout(state.timer)
      await state.queue.catch(() => {})
      await state.biliSession.clearStorageData()
      await state.biliSession.clearCache()
    }
    await fs.rm(vaultPath(partition), { force: true })
    const legacySession = session.fromPartition(legacyPartition)
    await legacySession.clearStorageData()
    await legacySession.clearCache()
    await legacySession.cookies.flushStore()
    if (state) state.suspended = false
  }

  async function flushAll() {
    await Promise.all([...states.values()].map(state =>
      state.ready.then(() => save(state.partition))))
  }

  return { load, save, clear, flushAll }
}

module.exports = { createBilibiliSessionStore, isBilibiliCookie, cookieDetails, snapshotCookie }
