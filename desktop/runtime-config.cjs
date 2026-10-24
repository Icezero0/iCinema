const fs = require('node:fs')
const path = require('node:path')

function readDevelopmentApiOrigin(frontendDir, env = process.env) {
  if (env.VITE_API_ORIGIN) return env.VITE_API_ORIGIN
  let origin = null
  for (const name of ['.env', '.env.local', '.env.development', '.env.development.local']) {
    const file = path.join(frontendDir, name)
    if (!fs.existsSync(file)) continue
    for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
      const match = /^\s*(?:export\s+)?VITE_API_ORIGIN\s*=\s*(.*?)\s*$/.exec(line)
      if (!match) continue
      const value = match[1].trim()
      origin = /^(['"]).*\1$/.test(value) ? value.slice(1, -1) : value.replace(/\s+#.*$/, '')
    }
  }
  return origin
}

function readConnectionConfig(filePath, defaultApiOrigin = 'http://localhost:8000') {
  if (!filePath) return {}
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, JSON.stringify({ apiOrigin: defaultApiOrigin }, null, 2) + '\n', { flag: 'wx' })
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

module.exports = { desktopRuntimeConfig, readConnectionConfig, readDevelopmentApiOrigin }
