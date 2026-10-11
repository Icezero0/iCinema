const fs = require('node:fs')
const path = require('node:path')

const APP_URL = 'icinema://app/'

function isFile(filePath) {
  try {
    return fs.statSync(filePath).isFile()
  } catch {
    return false
  }
}

function assetPathForUrl(value, rendererDir) {
  let url
  try {
    url = new URL(value)
  } catch {
    return null
  }
  if (url.protocol !== 'icinema:' || url.host !== 'app' || url.username || url.password || url.port) {
    return null
  }

  let pathname
  try {
    pathname = decodeURIComponent(url.pathname)
  } catch {
    return null
  }
  if (!pathname.startsWith('/') || pathname.includes('\\') || pathname.includes('\0')) return null

  const root = path.resolve(rendererDir)
  const isRoute = pathname === '/' || (!path.posix.extname(pathname) && !pathname.startsWith('/assets/'))
  const target = path.resolve(root, isRoute ? 'index.html' : pathname.slice(1))
  const relative = path.relative(root, target)
  if (relative.startsWith('..') || path.isAbsolute(relative)) return null
  return isFile(target) ? target : null
}

module.exports = { APP_URL, assetPathForUrl }
