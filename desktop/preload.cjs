const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('icinemaDesktop', {
  getInfo: () => ipcRenderer.invoke('desktop:info'),
  checkForUpdates: () => ipcRenderer.invoke('desktop:check-updates'),
  openDataFolder: () => ipcRenderer.invoke('desktop:open-data')
})

const prefix = '--icinema-config='
const argument = process.argv.filter(value => value.startsWith(prefix)).at(-1)
if (argument) {
  const config = JSON.parse(decodeURIComponent(argument.slice(prefix.length)))
  contextBridge.exposeInMainWorld('icinemaDesktopConfig', {
    apiOrigin: config.apiOrigin,
    wsOrigin: config.wsOrigin,
    storageMode: config.storageMode,
    storagePath: config.storagePath
  })
}

contextBridge.exposeInMainWorld('icinemaBilibili', {
  status: token => ipcRenderer.invoke('bilibili:status', token),
  login: token => ipcRenderer.invoke('bilibili:login', token),
  logout: token => ipcRenderer.invoke('bilibili:logout', token),
  videoInfo: (token, bvid) => ipcRenderer.invoke('bilibili:video-info', token, bvid),
  resolve: (token, bvid, cid) => ipcRenderer.invoke('bilibili:resolve', token, bvid, cid),
  onLoginComplete: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('bilibili:login-complete', listener)
    return () => ipcRenderer.removeListener('bilibili:login-complete', listener)
  }
})
