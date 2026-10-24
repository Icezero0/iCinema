const { repository } = require('./release-config.json')

const RELEASES_URL = `https://github.com/${repository}/releases`
const RELEASE_API = `https://api.github.com/repos/${repository}/releases/latest`

function parseVersion(value) {
  const match = /^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([\da-zA-Z-]+(?:\.[\da-zA-Z-]+)*))?(?:\+[\da-zA-Z.-]+)?$/.exec(value)
  if (!match) throw new Error('Invalid release version')
  const prerelease = match[4]?.split('.') ?? []
  if (prerelease.some(part => /^0\d+$/.test(part))) throw new Error('Invalid release version')
  return { numbers: match.slice(1, 4).map(BigInt), prerelease }
}

function compareVersions(left, right) {
  const a = parseVersion(left)
  const b = parseVersion(right)
  for (let i = 0; i < 3; i++) {
    if (a.numbers[i] !== b.numbers[i]) return a.numbers[i] > b.numbers[i] ? 1 : -1
  }
  if (!a.prerelease.length || !b.prerelease.length) {
    return a.prerelease.length === b.prerelease.length ? 0 : a.prerelease.length ? -1 : 1
  }
  for (let i = 0; i < Math.max(a.prerelease.length, b.prerelease.length); i++) {
    const x = a.prerelease[i]
    const y = b.prerelease[i]
    if (x === y) continue
    if (x === undefined) return -1
    if (y === undefined) return 1
    const xn = /^\d+$/.test(x)
    const yn = /^\d+$/.test(y)
    if (xn && yn) return BigInt(x) > BigInt(y) ? 1 : -1
    if (xn !== yn) return xn ? -1 : 1
    return x > y ? 1 : -1
  }
  return 0
}

function releaseResult(release, version) {
  if (!release || release.draft || release.prerelease || typeof release.tag_name !== 'string') {
    throw new Error('Invalid release response')
  }
  const available = compareVersions(release.tag_name, version) > 0
  return {
    status: available ? 'available' : 'current',
    latestVersion: release.tag_name.replace(/^v/, ''),
    // Construct this ourselves: no arbitrary URLs from the response reach the renderer.
    releaseUrl: `${RELEASES_URL}/tag/${encodeURIComponent(release.tag_name)}`,
    checkedAt: new Date().toISOString()
  }
}

function createUpdateChecker(fetchRelease, version, now = Date.now) {
  let pending = null
  let cached = null
  let nextAttempt = 0
  return function check() {
    if (pending) return pending
    if (now() < nextAttempt) {
      if (cached) return Promise.resolve(cached)
      return Promise.reject(new Error('UPDATE_CHECK_UNAVAILABLE'))
    }
    nextAttempt = now() + 15000
    pending = (async () => {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 12000)
      try {
        const response = await fetchRelease(RELEASE_API, {
          headers: { Accept: 'application/vnd.github+json', 'User-Agent': `iCinema/${version}` },
          credentials: 'omit', redirect: 'error', cache: 'no-store', signal: controller.signal
        })
        if (response.status === 404) {
          cached = { status: 'unpublished', latestVersion: null, releaseUrl: RELEASES_URL, checkedAt: new Date().toISOString() }
        } else {
          if (!response.ok) throw new Error('Release service unavailable')
          cached = releaseResult(await response.json(), version)
        }
        nextAttempt = now() + 60000
        return cached
      } catch {
        cached = null
        nextAttempt = now() + 15000
        throw new Error('UPDATE_CHECK_UNAVAILABLE')
      } finally {
        clearTimeout(timeout)
        pending = null
      }
    })()
    return pending
  }
}

function assertAppFrame(event, appOrigin) {
  const frame = event.senderFrame
  if (!frame || frame !== event.sender.mainFrame) throw new Error('INVALID_APP_FRAME')
  const url = new URL(frame.url)
  const expected = new URL(appOrigin)
  if (url.protocol !== expected.protocol || url.host !== expected.host || url.username || url.password) {
    throw new Error('INVALID_APP_FRAME')
  }
}

function setupDesktopInfo({ ipcMain, net, shell, appOrigin, version, storagePath, mode }) {
  const check = createUpdateChecker((...args) => net.fetch(...args), version)
  ipcMain.handle('desktop:info', event => {
    assertAppFrame(event, appOrigin)
    return { version, storagePath, mode, platform: process.platform, arch: process.arch }
  })
  ipcMain.handle('desktop:check-updates', event => {
    assertAppFrame(event, appOrigin)
    return check()
  })
  ipcMain.handle('desktop:open-data', async event => {
    assertAppFrame(event, appOrigin)
    const error = await shell.openPath(storagePath)
    if (error) throw new Error('OPEN_DATA_DIRECTORY_FAILED')
  })
}

module.exports = { compareVersions, releaseResult, createUpdateChecker, setupDesktopInfo }
