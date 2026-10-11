const test = require('node:test')
const assert = require('node:assert/strict')
const { setupBilibiliPlayback } = require('./bilibili-playback.cjs')

const bvid = 'BV1JneT6rEaG'
const videoUrl = 'https://upos-sz-mirrorcosov.bilivideo.com/video'
const audioUrl = 'https://upos-sz-mirrorcosov.bilivideo.com/audio'

function track(id, codecs, url) {
  return {
    id, codecs, bandwidth: 1_000_000,
    baseUrl: url, backupUrl: [],
    SegmentBase: { Initialization: '0-1023', indexRange: '1024-2047' }
  }
}

test('local resolve keeps CDN URLs private and serves validated Range requests', async () => {
  const handlers = new Map()
  let mediaHandler
  const protocol = { handle: (_scheme, handler) => { mediaHandler = handler } }
  const appOrigin = 'http://localhost:5173'
  const frame = { url: `${appOrigin}/rooms/1` }
  const sender = { mainFrame: frame }
  const event = { sender, senderFrame: frame }
  const net = { fetch: async (_url, options) => {
    const range = options.headers.Range
    const [, start, end] = /^bytes=(\d+)-(\d+)$/.exec(range)
    const size = Number(end) - Number(start) + 1
    return new Response(new Uint8Array(size), { status: 206, headers: {
      'content-type': 'video/mp4',
      'content-length': String(size),
      'content-range': `bytes ${start}-${end}/1000000`,
      'accept-ranges': 'bytes'
    } })
  } }
  const playback = setupBilibiliPlayback({
    ipcMain: { handle: (name, handler) => handlers.set(name, handler) },
    net, protocol, session: { defaultSession: { protocol } }, appOrigin,
    accountForToken: async token => {
      assert.equal(token, 'access-token')
      return { userId: 7, biliSession: {} }
    },
    fetchBilibiliStatus: async () => ({ loggedIn: true }),
    requestBilibiliJson: async (_session, url) => url.includes('/x/player/playurl')
      ? { code: 0, data: { dash: {
        video: [track(80, 'avc1.640033', videoUrl)],
        audio: [track(30280, 'mp4a.40.2', audioUrl)]
      } } }
      : { code: 0, data: {} },
    bilibiliVideoInfoFromView: () => ({ pages: [
      { page: 1, cid: 123, durationSeconds: 357 }
    ] })
  })

  const media = await handlers.get('bilibili:resolve')(event, 'access-token', bvid, 123)
  assert.equal(media.cid, 123)
  assert.equal(media.page, 1)
  assert.doesNotMatch(media.mpd, /bilivideo\.com/)
  const mediaUrl = /<BaseURL>([^<]+)<\/BaseURL>/.exec(media.mpd)[1]
  const response = await mediaHandler(new Request(mediaUrl, { headers: { Range: 'bytes=0-1023' } }))
  assert.equal(response.status, 206)
  assert.equal(response.headers.get('content-range'), 'bytes 0-1023/1000000')
  assert.equal((await response.arrayBuffer()).byteLength, 1024)
  playback.clearUser(7)
  assert.equal((await mediaHandler(new Request(mediaUrl))).status, 410)
})

test('interrupted media range cycles CDNs, refreshes URLs and completes without exposing partial bytes', async () => {
  const backupUrl = 'https://upos-hz-mirrorakam.akamaized.net/video'
  const refreshedUrl = 'https://upos-hz-mirrorakam.akamaized.net/video?fresh=1'
  const handlers = new Map()
  let mediaHandler
  let playback = false
  let playUrlCalls = 0
  const attempts = []
  const totalBytes = 2_000_000
  const net = { fetch: async (url, options) => {
    const [, start, end] = /^bytes=(\d+)-(\d+)$/.exec(options.headers.Range)
    const size = Number(end) - Number(start) + 1
    const headers = {
      'content-length': String(size),
      'content-range': `bytes ${start}-${end}/${totalBytes}`
    }
    if (playback) {
      attempts.push({ url, range: options.headers.Range })
      if (attempts.length === 2) {
        return new Response(new ReadableStream({
          start(controller) {
            controller.enqueue(new Uint8Array(100))
            controller.error(new Error('stream interrupted'))
          }
        }), { status: 206, headers })
      }
      if (attempts.length === 3) throw new Error('CDN unavailable')
    }
    return new Response(new Uint8Array(size), { status: 206, headers })
  } }
  const appOrigin = 'http://localhost:5173'
  const frame = { url: `${appOrigin}/rooms/1` }
  setupBilibiliPlayback({
    ipcMain: { handle: (name, handler) => handlers.set(name, handler) },
    net, protocol: { handle: (_scheme, handler) => { mediaHandler = handler } },
    session: { defaultSession: { protocol: { handle: (_scheme, handler) => { mediaHandler = handler } } } },
    appOrigin, accountForToken: async () => ({ userId: 7, biliSession: {} }),
    fetchBilibiliStatus: async () => ({ loggedIn: true }),
    requestBilibiliJson: async (_session, url) => {
      if (!url.includes('/x/player/playurl')) return { code: 0, data: {} }
      playUrlCalls++
      return { code: 0, data: { dash: {
        video: playUrlCalls === 1
          ? [{ ...track(80, 'avc1.640033', videoUrl), backupUrl: [backupUrl] }]
          : [track(80, 'avc1.640033', refreshedUrl)],
        audio: [track(30280, 'mp4a.40.2', audioUrl)]
      } } }
    },
    bilibiliVideoInfoFromView: () => ({ pages: [{ page: 1, cid: 123, durationSeconds: 357 }] })
  })
  const media = await handlers.get('bilibili:resolve')({ sender: { mainFrame: frame }, senderFrame: frame },
    'access-token', bvid, 123)
  const mediaUrl = /<BaseURL>([^<]+)<\/BaseURL>/.exec(media.mpd)[1]
  playback = true
  const response = await mediaHandler(new Request(mediaUrl, { headers: { Range: 'bytes=300000-1000000' } }))
  assert.equal(response.status, 206)
  assert.equal((await response.arrayBuffer()).byteLength, 700001)
  assert.equal(attempts.length, 4)
  assert.equal(attempts[0].range, 'bytes=300000-824287')
  assert.equal(attempts[1].range, 'bytes=824288-1000000')
  assert.notEqual(attempts[1].url, attempts[2].url)
  assert.equal(attempts[3].url, refreshedUrl)
  assert.equal(playUrlCalls, 2)
  assert.deepEqual(new Set(attempts.map(attempt => attempt.url)), new Set([videoUrl, backupUrl, refreshedUrl]))
})
