const fs = require('node:fs')
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
  if (mode === 'portable' || mode === 'installed') {
    if (!localAppData || !path.isAbsolute(localAppData)) {
      throw new Error('iCinema requires an absolute LOCALAPPDATA path')
    }
    return path.join(localAppData, 'iCinema')
  }
  throw new Error('Unknown iCinema distribution mode')
}

// Publish a complete copy atomically. Existing user data and the old copy are never overwritten.
function migrateLegacyData(source, target) {
  if (fs.existsSync(target)) return false
  const sourceStat = fs.lstatSync(source, { throwIfNoEntry: false })
  if (!sourceStat) return false
  if (!sourceStat.isDirectory() || sourceStat.isSymbolicLink()) {
    throw new Error('Legacy data must be a regular directory')
  }
  const parent = path.dirname(path.resolve(target))
  fs.mkdirSync(parent, { recursive: true })
  const staging = fs.mkdtempSync(path.join(parent, '.iCinema-migration-'))
  try {
    const caches = new Set(['Cache', 'Code Cache', 'GPUCache', 'DawnCache', 'Crashpad'])
    fs.cpSync(source, staging, {
      recursive: true,
      filter(file) {
        const relative = path.relative(source, file)
        const name = path.basename(file)
        if (caches.has(relative) || name === 'LOCK' || name.startsWith('Singleton')) return false
        if (fs.lstatSync(file).isSymbolicLink()) {
          throw new Error('Legacy data contains a symbolic link; migration stopped')
        }
        return true
      }
    })
    // Another launch may have completed migration while this copy was being made.
    if (fs.existsSync(target)) return false
    fs.renameSync(staging, target)
    return true
  } finally {
    if (path.dirname(staging) !== parent || !path.basename(staging).startsWith('.iCinema-migration-')) {
      throw new Error('Unexpected migration staging directory')
    }
    fs.rmSync(staging, { recursive: true, force: true })
  }
}

module.exports = { distributionMode, storageDirectory, migrateLegacyData }
