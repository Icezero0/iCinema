const DEFAULT_APP_URL = 'http://localhost:5173/'

function appUrlFromEnvironment(value) {
  const url = new URL(value || DEFAULT_APP_URL)
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
      url.pathname !== '/' || url.search || url.hash) {
    throw new Error('ICINEMA_DESKTOP_URL must be an HTTP(S) origin')
  }
  return url.href
}

function navigationTarget(value, appOrigin) {
  let url
  try {
    url = new URL(value)
  } catch {
    return 'blocked'
  }
  if (url.origin === appOrigin && ['http:', 'https:'].includes(url.protocol)) {
    return 'internal'
  }
  if (['http:', 'https:', 'mailto:'].includes(url.protocol)) {
    return 'external'
  }
  return 'blocked'
}

module.exports = { appUrlFromEnvironment, navigationTarget }
