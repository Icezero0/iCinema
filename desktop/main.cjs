const fs = require('node:fs')
const path = require('node:path')
const { pathToFileURL } = require('node:url')
const { app, BrowserWindow, dialog, ipcMain, Menu, net, protocol, safeStorage, screen, session, shell } = require('electron')
const { appUrlFromEnvironment, navigationTarget } = require('./navigation.cjs')
const { APP_URL, assetPathForUrl } = require('./app-protocol.cjs')
const { desktopRuntimeConfig, readConnectionConfig, readDevelopmentApiOrigin } = require('./runtime-config.cjs')
const { distributionMode, storageDirectory } = require('./storage-policy.cjs')
const { setupBilibiliLogin } = require('./bilibili-login.cjs')
const { createBilibiliSessionStore } = require('./bilibili-session-store.cjs')
const { setupBilibiliPlayback } = require('./bilibili-playback.cjs')
const { bilibiliVideoInfoFromView } = require('./bilibili-video.cjs')

const bundled = app.isPackaged || process.argv.includes('--bundled')
const distributionManifest = app.isPackaged
  ? JSON.parse(fs.readFileSync(path.join(__dirname, 'distribution.json'), 'utf8'))
  : null
const mode = distributionMode(app.isPackaged, distributionManifest)
const appUrl = bundled ? APP_URL : appUrlFromEnvironment(process.env.ICINEMA_DESKTOP_URL)
const appOrigin = bundled ? APP_URL : new URL(appUrl).origin
const rendererDir = path.join(__dirname, 'renderer')

protocol.registerSchemesAsPrivileged([
  { scheme: 'icinema', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } },
  { scheme: 'icinema-bili', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true, stream: true } }
])

app.setName('iCinema')
if (process.platform === 'win32') app.setAppUserModelId('icinema.desktop')
const dataDir = storageDirectory(mode, app.getPath('exe'), process.env.LOCALAPPDATA)
if (dataDir) {
  fs.mkdirSync(dataDir, { recursive: true })
  app.setPath('userData', dataDir)
  app.setPath('sessionData', dataDir)
}
const storagePath = app.getPath('userData')
let runtimeConfig = null
let configurationError = null
let bilibiliApiOrigin = null
let credentialStore = null
let quitAfterCredentialFlush = false
let credentialFlushPending = false
try {
  if (bundled) {
    const connection = readConnectionConfig(dataDir && path.join(dataDir, 'connection.json'))
    runtimeConfig = {
      ...desktopRuntimeConfig(process.env, connection),
      storageMode: mode,
      storagePath
    }
  }
  const developmentApiOrigin = bundled ? null : readDevelopmentApiOrigin(path.join(__dirname, '..', 'frontend'))
  bilibiliApiOrigin = runtimeConfig?.apiOrigin || desktopRuntimeConfig({
    ...process.env,
    ICINEMA_API_ORIGIN: process.env.ICINEMA_API_ORIGIN || developmentApiOrigin
  }).apiOrigin
} catch (error) {
  configurationError = error
}
const configArgument = runtimeConfig
  ? `--icinema-config=${encodeURIComponent(JSON.stringify(runtimeConfig))}`
  : null

function createWindow(url = appUrl, persistWindowState = true) {
  const workArea = screen.getPrimaryDisplay().workAreaSize
  const window = new BrowserWindow({
    ...(persistWindowState ? {
      name: 'main-window',
      windowStatePersistence: { bounds: true, displayMode: false }
    } : {}),
    width: Math.min(1360, workArea.width),
    height: Math.min(960, workArea.height),
    minWidth: 800,
    minHeight: 600,
    title: 'iCinema',
    ...(bundled ? { icon: path.join(rendererDir, 'favicon.ico') } : {}),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      webviewTag: false,
      preload: path.join(__dirname, 'preload.cjs'),
      ...(configArgument ? { additionalArguments: [configArgument] } : {})
    }
  })

  window.webContents.on('will-navigate', (event, target) => {
    const action = navigationTarget(target, appOrigin)
    if (action === 'internal') return
    event.preventDefault()
    if (action === 'external') void shell.openExternal(target)
  })

  window.webContents.setWindowOpenHandler(({ url: target }) => {
    const action = navigationTarget(target, appOrigin)
    if (action === 'internal') createWindow(target, false)
    if (action === 'external') void shell.openExternal(target)
    return { action: 'deny' }
  })

  void window.loadURL(url).catch(error => {
    console.error('iCinema desktop could not load the frontend:', error.message)
  })
  return window
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null)
  if (configurationError) {
    dialog.showErrorBox('iCinema connection configuration', configurationError.message)
    app.quit()
    return
  }
  if (bundled) {
    if (!assetPathForUrl(APP_URL, rendererDir)) {
      throw new Error('Desktop renderer is missing. Run npm --prefix .\\desktop run build:renderer first.')
    }
    protocol.handle('icinema', request => {
      if (request.method !== 'GET') return new Response('Method not allowed', { status: 405 })
      const asset = assetPathForUrl(request.url, rendererDir)
      return asset
        ? net.fetch(pathToFileURL(asset).toString())
        : new Response('Not found', { status: 404 })
    })
  }
  credentialStore = createBilibiliSessionStore({ session, safeStorage, storagePath })
  let bilibiliPlayback
  const bilibiliAuth = setupBilibiliLogin({
    ipcMain, net, BrowserWindow, appOrigin, apiOrigin: bilibiliApiOrigin, credentialStore,
    onLogout: userId => bilibiliPlayback?.clearUser(userId)
  })
  bilibiliPlayback = setupBilibiliPlayback({
    ipcMain, session, net, protocol, appOrigin,
    bilibiliVideoInfoFromView, ...bilibiliAuth
  })
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => app.quit())
app.on('before-quit', event => {
  if (!credentialStore || quitAfterCredentialFlush) return
  event.preventDefault()
  if (credentialFlushPending) return
  credentialFlushPending = true
  void credentialStore.flushAll().catch(error => {
    console.error('Could not persist Bilibili login:', error.message)
  }).finally(() => {
    quitAfterCredentialFlush = true
    app.quit()
  })
})
