const fs = require('node:fs')

function readConnectionConfig(filePath) {
  if (!filePath) return {}
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, '{\n  "apiOrigin": "http://localhost:8000"\n}\n', { flag: 'wx' })
  }
  const config = JSON.parse(fs.readFileSync(filePath, 'utf8'))
  if (!config || typeof config !== 'object' || Array.isArray(config)) {
    throw new Error('connection.json must contain a JSON object')
  }
  return config
}

function normalizeOrigin(value, protocols, label) {
  let url
  try {
    url = new URL(value)
  } catch {
    throw new Error(`${label} must be an origin URL`)
  }
  if (!protocols.includes(url.protocol) || url.username || url.password ||
      url.pathname !== '/' || url.search || url.hash) {
    throw new Error(`${label} must be an origin URL`)
  }
  return url.origin
}

function desktopRuntimeConfig(env = process.env, saved = {}) {
  const apiOrigin = normalizeOrigin(
    env.ICINEMA_API_ORIGIN || saved.apiOrigin || 'http://localhost:8000',
    ['http:', 'https:'],
    'ICINEMA_API_ORIGIN'
  )
  const derivedWs = apiOrigin.replace(/^http/, 'ws')
  const wsOrigin = normalizeOrigin(
    env.ICINEMA_WS_ORIGIN || (env.ICINEMA_API_ORIGIN ? derivedWs : saved.wsOrigin || derivedWs),
    ['ws:', 'wss:'],
    'ICINEMA_WS_ORIGIN'
  )
  return { apiOrigin, wsOrigin }
}

module.exports = { desktopRuntimeConfig, readConnectionConfig }
