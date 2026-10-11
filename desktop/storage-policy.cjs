const path = require('node:path')

function distributionMode(isPackaged, manifest) {
  if (!isPackaged) return 'development'
  if (manifest?.mode !== 'portable' && manifest?.mode !== 'installed') {
    throw new Error('Packaged iCinema requires an explicit distribution mode')
  }
  return manifest.mode
}

function storageDirectory(mode, exePath, localAppData) {
  if (mode === 'development') return null
  if (mode === 'portable') return path.join(path.dirname(exePath), 'data')
  if (mode === 'installed') {
    if (!localAppData || !path.isAbsolute(localAppData)) {
      throw new Error('Installed iCinema requires an absolute LOCALAPPDATA path')
    }
    return path.join(localAppData, 'iCinema')
  }
  throw new Error('Unknown iCinema distribution mode')
}

module.exports = { distributionMode, storageDirectory }
