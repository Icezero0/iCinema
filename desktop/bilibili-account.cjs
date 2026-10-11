const { createHash } = require('node:crypto')

function accountPartition(apiOrigin, userId) {
  const url = new URL(apiOrigin)
  const origin = url.origin
  if (!['http:', 'https:'].includes(url.protocol) || origin === 'null' ||
      !Number.isSafeInteger(userId) || userId <= 0) {
    throw new Error('Invalid iCinema account identity')
  }
  const key = createHash('sha256').update(`${origin}\n${userId}`).digest('hex').slice(0, 32)
  return `icinema-bilibili-${key}`
}

function legacyAccountPartition(apiOrigin, userId) {
  return `persist:${accountPartition(apiOrigin, userId)}`
}

function isBilibiliPage(value) {
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && !url.username && !url.password &&
      (url.hostname === 'bilibili.com' || url.hostname.endsWith('.bilibili.com'))
  } catch {
    return false
  }
}

function bilibiliStatusFromNav(response) {
  const signedOut = { loggedIn: false, name: '', mid: null, avatarUrl: null }
  if (response?.code === -101) return signedOut
  if (response?.code !== 0 || typeof response.data?.isLogin !== 'boolean') {
    throw new Error('BILIBILI_STATUS_UNAVAILABLE')
  }
  if (!response.data.isLogin) return signedOut
  let avatarUrl = null
  try {
    const rawFace = response.data.face
    if (typeof rawFace === 'string' && rawFace) {
      const url = new URL(rawFace.startsWith('//') ? `https:${rawFace}` : rawFace)
      if (url.protocol === 'https:' && !url.username && !url.password &&
          (url.hostname === 'hdslb.com' || url.hostname.endsWith('.hdslb.com'))) {
        avatarUrl = url.href
      }
    }
  } catch {
    // Leave the avatar empty when Bilibili returns an unusable image URL.
  }
  return {
    loggedIn: true,
    name: String(response.data.uname || '').slice(0, 80),
    mid: Number.isSafeInteger(response.data.mid) ? response.data.mid : null,
    avatarUrl
  }
}

module.exports = { accountPartition, legacyAccountPartition, isBilibiliPage, bilibiliStatusFromNav }
