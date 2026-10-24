const test = require('node:test')
const assert = require('node:assert/strict')
const { setImmediate: settle } = require('node:timers/promises')
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

async function adaptiveFixture() {
  const handlers = new Map()
  let mediaHandler
  let mediaFetch = null
  const backupUrl = 'https://upos-hz-mirrorakam.akamaized.net/video'
  const totalBytes = 4 * 1024 * 1024
  const responseFor = (options, marker = 0) => {
    const [, start, end] = /^bytes=(\d+)-(\d+)$/.exec(options.headers.Range)
    const size = Number(end) - Number(start) + 1
    return new Response(new Uint8Array(size).fill(marker), { status: 206, headers: {
      'content-length': String(size), 'content-range': `bytes ${start}-${end}/${totalBytes}`
    } })
  }
  const frame = { url: 'icinema://app/rooms/1' }
  setupBilibiliPlayback({
    ipcMain: { handle: (name, fn) => handlers.set(name, fn) },
    net: { fetch: (url, options) => mediaFetch ? mediaFetch(url, options) : Promise.resolve(responseFor(options)) },
    session: { defaultSession: { protocol: { handle: (_name, fn) => { mediaHandler = fn } } } },
    appOrigin: 'icinema://app', accountForToken: async () => ({ userId: 7, biliSession: {} }),
    fetchBilibiliStatus: async () => ({ loggedIn: true }),
    requestBilibiliJson: async (_session, url) => url.includes('/playurl') ? { code: 0, data: { dash: {
      video: [{ ...track(80, 'avc1.640033', videoUrl), backupUrl: [backupUrl] }],
      audio: [track(30280, 'mp4a.40.2', audioUrl)]
    } } } : { code: 0, data: {} },
    bilibiliVideoInfoFromView: () => ({ pages: [{ page: 16, cid: 42561176767, durationSeconds: 1492 }] })
  })
  const media = await handlers.get('bilibili:resolve')({ sender: { mainFrame: frame }, senderFrame: frame },
    'access-token', bvid, 42561176767)
  const localUrl = /<BaseURL>([^<]+)<\/BaseURL>/.exec(media.mpd)[1]
  return {
    responseFor, setFetch: fn => { mediaFetch = fn },
    request: (range = 'bytes=0-524287', signal) => mediaHandler(new Request(localUrl, { headers: { Range: range }, signal }))
  }
}

test('slow successful CDN is replaced by a validated backup and the winner handles subsequent chunks', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const fixture = await adaptiveFixture()
  const attempts = []
  let slowUrl
  let aborted = false
  fixture.setFetch((url, options) => {
    attempts.push(url)
    slowUrl ??= url
    if (url === slowUrl) return new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => { aborted = true; reject(new Error('cancelled')) })
    })
    return Promise.resolve(fixture.responseFor(options, 7))
  })
  const response = await fixture.request()
  const body = response.arrayBuffer()
  await settle()
  assert.equal(attempts.length, 1)
  t.mock.timers.tick(1500)
  assert.equal(new Uint8Array(await body)[0], 7)
  assert.equal(aborted, true)
  assert.equal(attempts.length, 2)
  assert.notEqual(attempts[0], attempts[1])
  const fastUrl = attempts[1]
  const next = await fixture.request('bytes=524288-525311')
  assert.equal((await next.arrayBuffer()).byteLength, 1024)
  assert.equal(attempts[2], fastUrl)
  t.mock.timers.tick(30000)
  assert.equal(attempts.length, 3)
})

test('fast CDN completes without downloading a duplicate backup chunk', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const fixture = await adaptiveFixture()
  let attempts = 0
  fixture.setFetch(async (_url, options) => { attempts++; return fixture.responseFor(options) })
  const response = await fixture.request()
  assert.equal((await response.arrayBuffer()).byteLength, 524288)
  t.mock.timers.tick(30000)
  assert.equal(attempts, 1)
})

test('a truncated fast backup never replaces a valid slower response', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const fixture = await adaptiveFixture()
  let attempts = 0
  fixture.setFetch((_url, options) => {
    attempts++
    if (attempts === 1) return new Promise(resolve => setTimeout(() => resolve(fixture.responseFor(options, 8)), 2200))
    const valid = fixture.responseFor(options)
    return Promise.resolve(new Response(new Uint8Array(50), { status: 206, headers: valid.headers }))
  })
  const response = await fixture.request()
  const body = response.arrayBuffer()
  await settle()
  t.mock.timers.tick(1500)
  await settle()
  assert.equal(attempts, 2)
  t.mock.timers.tick(700)
  const bytes = new Uint8Array(await body)
  assert.equal(bytes.byteLength, 524288)
  assert.equal(bytes[0], 8)
})

test('cancelling a media request aborts both CDN requests without retrying or leaving the reader pending', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const fixture = await adaptiveFixture()
  let attempts = 0
  let aborted = 0
  fixture.setFetch((_url, options) => new Promise((_resolve, reject) => {
    attempts++
    options.signal.addEventListener('abort', () => { aborted++; reject(new Error('cancelled')) })
  }))
  const controller = new AbortController()
  const response = await fixture.request('bytes=0-524287', controller.signal)
  const rejected = assert.rejects(response.arrayBuffer(), /MEDIA_REQUEST_CANCELLED/)
  await settle()
  t.mock.timers.tick(1500)
  await settle()
  assert.equal(attempts, 2)
  controller.abort()
  await rejected
  t.mock.timers.tick(60000)
  assert.equal(attempts, 2)
  assert.equal(aborted, 2)
})

test('two chunks load concurrently while validated bytes stay in the requested order', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  const fixture = await adaptiveFixture()
  const finish = new Map()
  let active = 0
  let maximum = 0
  fixture.setFetch((_url, options) => new Promise(resolve => {
    const start = Number(/^bytes=(\d+)-/.exec(options.headers.Range)[1])
    active++
    maximum = Math.max(maximum, active)
    finish.set(start, () => {
      active--
      resolve(fixture.responseFor(options, start / 524288 + 1))
    })
  }))
  const response = await fixture.request('bytes=0-1572863')
  const reader = response.body.getReader()
  let delivered = false
  const first = reader.read().then(result => { delivered = true; return result })
  await settle()
  assert.deepEqual([...finish.keys()], [0, 524288])
  finish.get(524288)()
  await settle()
  assert.equal(delivered, false)
  finish.get(0)()
  assert.equal((await first).value[0], 1)
  assert.equal((await reader.read()).value[0], 2)
  await settle()
  finish.get(1048576)()
  assert.equal((await reader.read()).value[0], 3)
  assert.equal((await reader.read()).done, true)
  assert.equal(maximum, 2)
  assert.equal(finish.size, 3)
  t.mock.timers.tick(30000)
  assert.equal(finish.size, 3)
})
