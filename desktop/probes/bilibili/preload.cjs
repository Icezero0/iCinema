const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('desktopProbe', {
  openLogin: () => ipcRenderer.invoke('probe:open-login'),
  status: () => ipcRenderer.invoke('probe:status'),
  onLoginSuccess: callback => {
    const listener = (_event, status) => callback(status)
    ipcRenderer.on('probe:login-success', listener)
    return () => ipcRenderer.off('probe:login-success', listener)
  },
  resolve: (input, quality) => ipcRenderer.invoke('probe:resolve', input, quality),
  benchmarkVideo: () => ipcRenderer.invoke('probe:benchmark'),
  traffic: () => ipcRenderer.invoke('probe:traffic'),
  logout: () => ipcRenderer.invoke('probe:logout')
})
