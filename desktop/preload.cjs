const { contextBridge } = require('electron')

const prefix = '--icinema-config='
const argument = process.argv.filter(value => value.startsWith(prefix)).at(-1)
if (!argument) throw new Error('Missing iCinema desktop configuration')

const config = JSON.parse(decodeURIComponent(argument.slice(prefix.length)))
contextBridge.exposeInMainWorld('icinemaDesktopConfig', {
  apiOrigin: config.apiOrigin,
  wsOrigin: config.wsOrigin,
  storageMode: config.storageMode,
  storagePath: config.storagePath
})
