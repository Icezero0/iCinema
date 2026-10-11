const { accountPartition, legacyAccountPartition, isBilibiliPage, bilibiliStatusFromNav } = require('./bilibili-account.cjs')
const { BVID_PATTERN, bilibiliVideoInfoFromView } = require('./bilibili-video.cjs')

const NAV_URL = 'https://api.bilibili.com/x/web-interface/nav'
const MAX_RESPONSE_BYTES = 2 * 1024 * 1024
const MAX_ACCOUNT_RESPONSE_BYTES = 64 * 1024

function setupBilibiliLogin({ ipcMain, net, BrowserWindow, appOrigin, apiOrigin, credentialStore, onLogout }) {
  const appUrl = new URL(appOrigin)
  const loginWindows = new Map()

  function assertAppFrame(event) {
    const frame = event.senderFrame
    if (!frame || frame !== event.sender.mainFrame) throw new Error('INVALID_APP_FRAME')
    const url = new URL(frame.url)
    if (url.protocol !== appUrl.protocol || url.host !== appUrl.host || url.username || url.password) {
      throw new Error('INVALID_APP_FRAME')
    }
  }

  async function accountForToken(token, { resetUnreadable = false } = {}) {
    if (typeof token !== 'string' || !token || token.length > 8192) {
      throw new Error('ICINEMA_AUTH_REQUIRED')
    }
    let response
    try {
      response = await fetch(new URL('/api/v1/users/me', apiOrigin), {
        headers: { Authorization: `Bearer ${token}` },
        redirect: 'error',
        signal: AbortSignal.timeout(12000)
      })
    } catch {
      throw new Error('ICINEMA_BACKEND_UNAVAILABLE')
    }
    if (response.status === 401 || response.status === 403) throw new Error('ICINEMA_AUTH_REQUIRED')
    if (!response.ok || Number(response.headers.get('content-length') || 0) > MAX_ACCOUNT_RESPONSE_BYTES) {
      throw new Error('ICINEMA_BACKEND_UNAVAILABLE')
    }
    let user
    try {
      const body = await response.text()
      if (Buffer.byteLength(body) > MAX_ACCOUNT_RESPONSE_BYTES) throw new Error()
      user = JSON.parse(body)
    } catch {
      throw new Error('ICINEMA_BACKEND_UNAVAILABLE')
    }
    if (!Number.isSafeInteger(user?.id) || user.id <= 0) {
      throw new Error('ICINEMA_BACKEND_UNAVAILABLE')
    }
    const partition = accountPartition(apiOrigin, user.id)
    const legacyPartition = legacyAccountPartition(apiOrigin, user.id)
    let biliSession
    try {
      biliSession = await credentialStore.load(partition, legacyPartition)
    } catch (error) {
      if (!resetUnreadable || error.message !== 'BILIBILI_SECURE_STORAGE_UNREADABLE') throw error
      await credentialStore.clear(partition, legacyPartition)
      biliSession = await credentialStore.load(partition, legacyPartition)
    }
    return { userId: user.id, partition, biliSession }
  }

  function requestBilibiliJson(biliSession, url) {
    return new Promise((resolve, reject) => {
      const request = net.request({
        url,
        session: biliSession,
        useSessionCookies: true,
        redirect: 'error'
      })
      request.setHeader('Referer', 'https://www.bilibili.com/')
      request.setHeader('Accept', 'application/json')
      let finished = false
      const timer = setTimeout(() => request.abort(), 15000)
      function finish(error, data) {
        if (finished) return
        finished = true
        clearTimeout(timer)
        if (error) reject(error)
        else resolve(data)
      }
      request.on('error', () => finish(new Error('BILIBILI_REQUEST_FAILED')))
      request.on('abort', () => finish(new Error('BILIBILI_REQUEST_FAILED')))
      request.on('response', response => {
        if (response.statusCode !== 200) {
          request.abort()
          finish(new Error('BILIBILI_REQUEST_FAILED'))
          return
        }
        const chunks = []
        let size = 0
        response.on('data', chunk => {
          size += chunk.length
          if (size > MAX_RESPONSE_BYTES) {
            request.abort()
            finish(new Error('BILIBILI_REQUEST_FAILED'))
            return
          }
          chunks.push(chunk)
        })
        response.on('error', () => finish(new Error('BILIBILI_REQUEST_FAILED')))
        response.on('end', () => {
          try {
            const parsed = JSON.parse(Buffer.concat(chunks).toString('utf8'))
            finish(null, parsed)
          } catch {
            finish(new Error('BILIBILI_REQUEST_FAILED'))
          }
        })
      })
      request.end()
    })
  }

  async function fetchBilibiliStatus(biliSession) {
    return bilibiliStatusFromNav(await requestBilibiliJson(biliSession, NAV_URL))
  }

  function openLoginWindow(account, sender) {
    const existing = loginWindows.get(account.partition)
    if (existing && !existing.window.isDestroyed()) {
      existing.listeners.add(sender)
      existing.window.focus()
      return
    }

    const window = new BrowserWindow({
      width: 1120,
      height: 800,
      title: 'Bilibili 登录',
      webPreferences: {
        partition: account.partition,
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: true,
        webviewTag: false
      }
    })
    const entry = { window, listeners: new Set([sender]), timer: null, checking: false, needsCheck: false }
    loginWindows.set(account.partition, entry)

    function scheduleCheck() {
      clearTimeout(entry.timer)
      entry.timer = setTimeout(async () => {
        if (loginWindows.get(account.partition) !== entry) return
        if (entry.checking) {
          entry.needsCheck = true
          return
        }
        entry.checking = true
        try {
          const status = await fetchBilibiliStatus(account.biliSession)
          if (!status.loggedIn || loginWindows.get(account.partition) !== entry) return
          await credentialStore.save(account.partition)
          if (loginWindows.get(account.partition) !== entry) return
          for (const contents of entry.listeners) {
            if (!contents.isDestroyed()) {
              contents.send('bilibili:login-complete', { userId: account.userId })
            }
          }
          window.close()
        } catch {
          // Keep the login page open; the user may retry there.
        } finally {
          entry.checking = false
          if (entry.needsCheck && loginWindows.get(account.partition) === entry) {
            entry.needsCheck = false
            scheduleCheck()
          }
        }
      }, 500)
    }

    const onCookieChanged = (_event, cookie, _cause, removed) => {
      if (!removed && cookie.name === 'SESSDATA' &&
          /(^|\.)bilibili\.com$/.test(cookie.domain)) scheduleCheck()
    }
    account.biliSession.cookies.on('changed', onCookieChanged)
    window.webContents.on('did-finish-load', scheduleCheck)
    window.webContents.on('will-navigate', (event, target) => {
      if (!isBilibiliPage(target)) event.preventDefault()
    })
    window.webContents.setWindowOpenHandler(({ url }) => {
      if (!isBilibiliPage(url)) return { action: 'deny' }
      return { action: 'allow', overrideBrowserWindowOptions: { webPreferences: {
        partition: account.partition, nodeIntegration: false,
        contextIsolation: true, sandbox: true, webviewTag: false
      } } }
    })
    window.webContents.on('did-create-window', child => {
      child.webContents.on('will-navigate', (event, target) => {
        if (!isBilibiliPage(target)) event.preventDefault()
      })
      child.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
    })
    window.on('closed', () => {
      clearTimeout(entry.timer)
      account.biliSession.cookies.removeListener('changed', onCookieChanged)
      if (loginWindows.get(account.partition) === entry) loginWindows.delete(account.partition)
    })
    void window.loadURL('https://www.bilibili.com/').catch(() => {
      if (!window.isDestroyed()) window.close()
    })
  }

  ipcMain.handle('bilibili:status', async (event, token) => {
    assertAppFrame(event)
    const account = await accountForToken(token)
    return fetchBilibiliStatus(account.biliSession)
  })
  ipcMain.handle('bilibili:video-info', async (event, token, bvid) => {
    assertAppFrame(event)
    if (typeof bvid !== 'string' || !BVID_PATTERN.test(bvid)) {
      throw new Error('BILIBILI_BVID_INVALID')
    }
    const account = await accountForToken(token)
    const url = new URL('https://api.bilibili.com/x/web-interface/view')
    url.searchParams.set('bvid', bvid)
    return bilibiliVideoInfoFromView(await requestBilibiliJson(account.biliSession, url.href), bvid)
  })
  ipcMain.handle('bilibili:login', async (event, token) => {
    assertAppFrame(event)
    const account = await accountForToken(token, { resetUnreadable: true })
    openLoginWindow(account, event.sender)
    return { opened: true }
  })
  ipcMain.handle('bilibili:logout', async (event, token) => {
    assertAppFrame(event)
    const account = await accountForToken(token, { resetUnreadable: true })
    const entry = loginWindows.get(account.partition)
    if (entry && !entry.window.isDestroyed()) entry.window.close()
    onLogout?.(account.userId)
    await credentialStore.clear(account.partition, legacyAccountPartition(apiOrigin, account.userId))
    return { loggedIn: false, name: '', mid: null, avatarUrl: null }
  })
  return { accountForToken, requestBilibiliJson, fetchBilibiliStatus }
}

module.exports = { setupBilibiliLogin }
