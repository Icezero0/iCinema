const {
  BVID_PATTERN,
  candidateUrls,
  pickTracks,
  segmentBase,
  mediaToken,
  benchmarkRanges,
  fastestMediaProbe,
  nextMediaCandidate,
  buildMpd
} = require('./bilibili-media.cjs')

const MEDIA_ORIGIN = 'icinema-bili://app'
const REFERER = 'https://www.bilibili.com/'
const MEDIA_LIFETIME_MS = 2 * 60 * 60 * 1000
const MEDIA_CHUNK_BYTES = 512 * 1024
const MEDIA_ATTEMPT_TIMEOUT_MS = 15000

function setupBilibiliPlayback({ ipcMain, net, protocol, session, appOrigin, accountForToken,
  requestBilibiliJson, fetchBilibiliStatus, bilibiliVideoInfoFromView }) {
  const mediaEntries = new Map()

  function assertAppFrame(event) {
    const frame = event.senderFrame
    if (!frame || frame !== event.sender.mainFrame) throw new Error('INVALID_APP_FRAME')
    const url = new URL(frame.url)
    const expected = new URL(appOrigin)
    if (url.protocol !== expected.protocol || url.host !== expected.host || url.username || url.password) {
      throw new Error('INVALID_APP_FRAME')
    }
  }

  async function sampleMediaRange(url, range, expectedBytes, timeoutMs) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    const startedAt = performance.now()
    try {
      const response = await net.fetch(url, {
        method: 'GET',
        headers: { Referer: REFERER, Range: range },
        credentials: 'omit',
        cache: 'no-store',
        redirect: 'error',
        signal: controller.signal
      })
      if (response.status !== 206) {
        await response.body?.cancel()
        return 0
      }
      const bytes = (await response.arrayBuffer()).byteLength
      if (bytes !== expectedBytes) return 0
      return bytes * 8 / Math.max(1, performance.now() - startedAt) / 1000
    } catch {
      return 0
    } finally {
      clearTimeout(timer)
    }
  }

  async function probeMediaCandidate(url) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 5000)
    let totalBytes
    try {
      const response = await net.fetch(url, {
        method: 'GET',
        headers: { Referer: REFERER, Range: 'bytes=0-1' },
        credentials: 'omit',
        redirect: 'error',
        signal: controller.signal
      })
      const match = /^bytes 0-1\/(\d+)$/i.exec(response.headers.get('content-range') ?? '')
      await response.body?.cancel()
      if (response.status !== 206 || !match) return null
      totalBytes = Number(match[1])
    } catch {
      return null
    } finally {
      clearTimeout(timer)
    }

    const probe = { url, totalBytes, sampleMbps: 0 }
    try {
      const [range] = benchmarkRanges(totalBytes)
      const match = /^bytes=(\d+)-(\d+)$/.exec(range)
      const expectedBytes = Number(match[2]) - Number(match[1]) + 1
      probe.sampleMbps = await sampleMediaRange(url, range, expectedBytes, 4000)
    } catch {
      // A valid initial Range response is enough to keep a small media file usable.
    }
    return probe
  }

  async function chooseMediaUrl(track) {
    const candidates = [...new Set(candidateUrls(track))]
    if (!candidates.length) throw new Error('BILIBILI_CDN_UNAVAILABLE')
    const usable = (await Promise.all(candidates.map(probeMediaCandidate))).filter(Boolean)
    const selected = fastestMediaProbe(usable)
    if (!selected) throw new Error('BILIBILI_CDN_UNAVAILABLE')
    const usableCandidates = [selected, ...usable.filter(item =>
      item !== selected && item.totalBytes === selected.totalBytes)
      .sort((a, b) => b.sampleMbps - a.sampleMbps)].map(item => item.url)
    // A probe can fail temporarily; keep every allowed backup for playback retries.
    usableCandidates.push(...candidates.filter(url => !usableCandidates.includes(url)))
    return { ...selected, usableCandidates }
  }

  function clearUser(userId) {
    for (const [token, entry] of mediaEntries) {
      if (entry.userId === userId) mediaEntries.delete(token)
    }
  }

  async function resolve(event, token, bvid, cid) {
    assertAppFrame(event)
    if (typeof bvid !== 'string' || !BVID_PATTERN.test(bvid) ||
        !Number.isSafeInteger(cid) || cid <= 0) throw new Error('BILIBILI_VIDEO_INVALID')
    const account = await accountForToken(token)
    const status = await fetchBilibiliStatus(account.biliSession)
    if (!status.loggedIn) throw new Error('BILIBILI_LOGIN_REQUIRED')
    const viewUrl = new URL('https://api.bilibili.com/x/web-interface/view')
    viewUrl.searchParams.set('bvid', bvid)
    const info = bilibiliVideoInfoFromView(
      await requestBilibiliJson(account.biliSession, viewUrl.href), bvid)
    const part = info.pages.find(item => item.cid === cid)
    if (!part) throw new Error('BILIBILI_PART_UNAVAILABLE')

    const playUrl = new URL('https://api.bilibili.com/x/player/playurl')
    playUrl.searchParams.set('bvid', bvid)
    playUrl.searchParams.set('cid', String(cid))
    playUrl.searchParams.set('qn', '80')
    playUrl.searchParams.set('fnval', '16')
    playUrl.searchParams.set('fourk', '1')
    const response = await requestBilibiliJson(account.biliSession, playUrl.href)
    if (response?.code !== 0 || !response.data?.dash) {
      throw new Error('BILIBILI_DASH_UNAVAILABLE')
    }
    const tracks = pickTracks(response.data.dash, 80)
    const [video, audio] = await Promise.all([
      chooseMediaUrl(tracks.video), chooseMediaUrl(tracks.audio)
    ])
    const duration = part.durationSeconds || Number(response.data.timelength) / 1000
    const tokens = { video: mediaToken(), audio: mediaToken() }
    const mpd = buildMpd(tracks, duration, tokens, MEDIA_ORIGIN)
    const expiresAt = Date.now() + MEDIA_LIFETIME_MS
    for (const [entryToken, entry] of mediaEntries) {
      if (Date.now() >= entry.expiresAt) mediaEntries.delete(entryToken)
    }
    function refreshCandidates(kind, originalTrack) {
      return async () => {
        const updated = await requestBilibiliJson(account.biliSession, playUrl.href)
        if (updated?.code !== 0 || !updated.data?.dash) throw new Error('BILIBILI_DASH_UNAVAILABLE')
        const originalSegment = segmentBase(originalTrack)
        const refreshed = (updated.data.dash[kind] ?? []).find(track => {
          if (Number(track.id) !== Number(originalTrack.id) || track.codecs !== originalTrack.codecs) return false
          try {
            const segment = segmentBase(track)
            return segment.initialization === originalSegment.initialization &&
              segment.indexRange === originalSegment.indexRange
          } catch {
            return false
          }
        })
        if (!refreshed) throw new Error('BILIBILI_TRACK_CHANGED')
        const candidates = [...new Set(candidateUrls(refreshed))]
        if (!candidates.length) throw new Error('BILIBILI_CDN_UNAVAILABLE')
        return candidates
      }
    }
    mediaEntries.set(tokens.video, { ...video, kind: 'video', userId: account.userId, expiresAt,
      refresh: refreshCandidates('video', tracks.video), lastRefreshAt: 0, refreshPromise: null })
    mediaEntries.set(tokens.audio, { ...audio, kind: 'audio', userId: account.userId, expiresAt,
      refresh: refreshCandidates('audio', tracks.audio), lastRefreshAt: 0, refreshPromise: null })
    return { bvid, cid, page: part.page, duration, mpd }
  }

  function waitForRetry(delayMs, signal) {
    return new Promise((resolve, reject) => {
      if (signal.aborted) return reject(new Error('MEDIA_REQUEST_CANCELLED'))
      const onAbort = () => {
        clearTimeout(timer)
        reject(new Error('MEDIA_REQUEST_CANCELLED'))
      }
      const timer = setTimeout(() => {
        signal.removeEventListener('abort', onAbort)
        resolve()
      }, delayMs)
      signal.addEventListener('abort', onAbort, { once: true })
    })
  }

  async function refreshMediaCandidates(entry, token) {
    if (Date.now() - entry.lastRefreshAt < 60000) return
    if (!entry.refreshPromise) {
      entry.lastRefreshAt = Date.now()
      entry.refreshPromise = (async () => {
        let timer
        let candidates
        try {
          candidates = await Promise.race([
            entry.refresh(),
            new Promise((_, reject) => {
              timer = setTimeout(() => reject(new Error('BILIBILI_REFRESH_TIMEOUT')), 10000)
            })
          ])
        } finally {
          clearTimeout(timer)
        }
        if (mediaEntries.get(token) !== entry) return
        entry.usableCandidates = candidates
        entry.url = candidates[0]
      })().catch(() => {}).finally(() => { entry.refreshPromise = null })
    }
    await entry.refreshPromise
  }

  async function fetchMediaChunk(entry, token, start, end, signal) {
    let candidate = entry.url
    let failedAttempts = 0
    const expectedBytes = end - start + 1
    while (!signal.aborted && mediaEntries.get(token) === entry && Date.now() < entry.expiresAt) {
      const controller = new AbortController()
      const onAbort = () => controller.abort()
      signal.addEventListener('abort', onAbort, { once: true })
      const timer = setTimeout(() => controller.abort(), MEDIA_ATTEMPT_TIMEOUT_MS)
      try {
        const upstream = await net.fetch(candidate, {
          method: 'GET',
          headers: { Referer: REFERER, Range: `bytes=${start}-${end}` },
          credentials: 'omit',
          cache: failedAttempts ? 'no-store' : 'default',
          redirect: 'error',
          signal: controller.signal
        })
        const delivered = /^bytes (\d+)-(\d+)\/(\d+)$/i.exec(upstream.headers.get('content-range') ?? '')
        if (upstream.status !== 206 || !delivered || Number(delivered[1]) !== start ||
            Number(delivered[2]) !== end || Number(delivered[3]) !== entry.totalBytes) {
          await upstream.body?.cancel()
          throw new Error('BILIBILI_CDN_INVALID_RANGE')
        }
        const chunk = new Uint8Array(await upstream.arrayBuffer())
        if (chunk.byteLength !== expectedBytes) throw new Error('BILIBILI_CDN_TRUNCATED')
        entry.url = candidate
        return chunk
      } catch (error) {
        if (signal.aborted) throw new Error('MEDIA_REQUEST_CANCELLED')
        failedAttempts++
        const next = nextMediaCandidate(entry.usableCandidates, candidate)
        if (next) candidate = next
        if (entry.url !== candidate) entry.url = candidate
        if (failedAttempts % entry.usableCandidates.length === 0) {
          await refreshMediaCandidates(entry, token)
          candidate = entry.url
          entry.expiresAt = Date.now() + MEDIA_LIFETIME_MS
          const rounds = Math.floor(failedAttempts / entry.usableCandidates.length)
          await waitForRetry(Math.min(10000, 1000 * 2 ** Math.min(rounds - 1, 4)), signal)
        }
      } finally {
        clearTimeout(timer)
        signal.removeEventListener('abort', onAbort)
      }
    }
    throw new Error('MEDIA_REQUEST_CANCELLED')
  }

  async function mediaResponse(request) {
    const url = new URL(request.url)
    if (url.hostname !== 'app' || url.search || url.hash) return new Response('Not found', { status: 404 })
    const requestOrigin = request.headers.get('origin')
    if (requestOrigin && requestOrigin !== appOrigin) return new Response('Forbidden', { status: 403 })
    const match = /^\/media\/([0-9a-f]{40})$/.exec(url.pathname)
    if (!match) return new Response('Not found', { status: 404 })
    const entry = mediaEntries.get(match[1])
    if (!entry || Date.now() >= entry.expiresAt) {
      mediaEntries.delete(match[1])
      return new Response('Media expired', { status: 410 })
    }
    entry.expiresAt = Date.now() + MEDIA_LIFETIME_MS
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: {
      'Access-Control-Allow-Origin': appOrigin,
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Range'
    } })
    if (request.method !== 'GET') return new Response('Method not allowed', { status: 405 })
    const range = request.headers.get('range')
    if (range && !/^bytes=\d+-\d*$/.test(range)) return new Response('Invalid Range', { status: 416 })
    const totalBytes = entry.totalBytes
    if (!Number.isSafeInteger(totalBytes) || totalBytes <= 0) return new Response('Media unavailable', { status: 502 })
    const requested = range ? /^bytes=(\d+)-(\d*)$/.exec(range) : null
    const start = requested ? Number(requested[1]) : 0
    const end = requested && requested[2] ? Number(requested[2]) : totalBytes - 1
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start > end || end >= totalBytes) {
      return new Response('Invalid Range', { status: 416, headers: { 'Content-Range': `bytes */${totalBytes}` } })
    }
    const lifecycle = new AbortController()
    const onRequestAbort = () => lifecycle.abort()
    request.signal?.addEventListener('abort', onRequestAbort, { once: true })
    if (request.signal?.aborted) lifecycle.abort()
    let offset = start
    const cleanup = () => request.signal?.removeEventListener('abort', onRequestAbort)
    const body = new ReadableStream({
      async pull(controller) {
        if (lifecycle.signal.aborted) {
          cleanup()
          controller.error(new Error('MEDIA_REQUEST_CANCELLED'))
          return
        }
        try {
          const chunkEnd = Math.min(end, offset + MEDIA_CHUNK_BYTES - 1)
          const chunk = await fetchMediaChunk(entry, match[1], offset, chunkEnd, lifecycle.signal)
          if (lifecycle.signal.aborted) return
          controller.enqueue(chunk)
          offset = chunkEnd + 1
          if (offset > end) {
            cleanup()
            controller.close()
          }
        } catch (error) {
          cleanup()
          if (!lifecycle.signal.aborted) controller.error(error)
        }
      },
      cancel() {
        lifecycle.abort()
        cleanup()
      }
    })
    const responseHeaders = new Headers({
      'Access-Control-Allow-Origin': appOrigin,
      'Access-Control-Expose-Headers': 'Content-Length, Content-Range, Accept-Ranges',
      'Cache-Control': 'private, max-age=300',
      'Content-Type': `${entry.kind}/mp4`,
      'Content-Length': String(end - start + 1),
      'Accept-Ranges': 'bytes'
    })
    if (range) responseHeaders.set('Content-Range', `bytes ${start}-${end}/${totalBytes}`)
    return new Response(body, { status: range ? 206 : 200, headers: responseHeaders })
  }

  ipcMain.handle('bilibili:resolve', resolve)
  session.defaultSession.protocol.handle('icinema-bili', mediaResponse)
  return { clearUser }
}

module.exports = { setupBilibiliPlayback }
