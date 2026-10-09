const { app, BrowserWindow, shell } = require('electron')
const { appUrlFromEnvironment, navigationTarget } = require('./navigation.cjs')

const appUrl = appUrlFromEnvironment(process.env.ICINEMA_DESKTOP_URL)
const appOrigin = new URL(appUrl).origin

app.setName('iCinema')
if (process.platform === 'win32') app.setAppUserModelId('icinema.desktop')

function createWindow(url = appUrl) {
  const window = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 800,
    minHeight: 600,
    title: 'iCinema',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      webviewTag: false
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
    if (action === 'internal') createWindow(target)
    if (action === 'external') void shell.openExternal(target)
    return { action: 'deny' }
  })

  void window.loadURL(url).catch(error => {
    console.error('iCinema desktop could not load the frontend:', error.message)
  })
  return window
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => app.quit())
