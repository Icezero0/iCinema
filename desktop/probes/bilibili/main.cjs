const { app, BrowserWindow, ipcMain, net, protocol, session } = require('electron')
const fs = require('node:fs/promises')
const path = require('node:path')
const {
  parseVideoInput, candidateUrls, describeVideoTracks, pickTracks, mediaToken, benchmarkRanges, fastestMediaProbe, nextMediaCandidate, checkedMediaStream, buildMpd
} = require('./bilibili.cjs')

const APP_ORIGIN = 'icinema-probe://app'
const BILI_PARTITION = 'persist:icinema-bilibili-probe'
const MAX_JSON_BYTES = 2 * 1024 * 1024
const mediaEntries = new Map()
const mediaTraces = []
let nextMediaTraceId = 1
let currentVideoToken
let biliSession
let loginWindow
let mainWindow
let loginCheckTimer
let authGeneration = 0

protocol.registerSchemesAsPrivileged([{
  scheme: 'icinema-probe',
  privileges: { standard: true, secure: true, supportFetchAPI: true, stream: true }
}])

function assertAppFrame(event) {
  if (!event.senderFrame?.url.startsWith(`${APP_ORIGIN}/`)) {
    throw new Error('仅允许原型窗口调用此操作')
  }
}

function apiJson(pathname) {
  return new Promise((resolve, reject) => {
    const request = net.request({
      url: `https://api.bilibili.com${pathname}`,
      session: biliSession,
      useSessionCookies: true,
      redirect: 'error'
    })
    request.setHeader('Referer', 'https://www.bilibili.com/')
    request.setHeader('Accept', 'application/json')
    let complete = false
    const timer = setTimeout(() => request.abort(), 15000)
    const finish = (error, result) => {
      if (complete) return
      complete = true
      clearTimeout(timer)
      if (error) reject(error)
      else resolve(result)
    }
    request.on('error', () => finish(new Error('B 站 API 网络请求失败或超时')))
    request.on('abort', () => finish(new Error('B 站 API 请求超时')))
    request.on('response', response => {
      const chunks = []
      let size = 0
      response.on('data', chunk => {
        size += chunk.length
        if (size > MAX_JSON_BYTES) {
          request.abort()
          finish(new Error('B 站 API 响应过大'))
          return
        }
        chunks.push(chunk)
      })
      response.on('error', () => finish(new Error('读取 B 站 API 响应失败')))
      response.on('end', () => {
        if (response.statusCode !== 200) {
          finish(new Error(`B 站 API 返回 HTTP ${response.statusCode}`))
          return
        }
        try {
          const parsed = JSON.parse(Buffer.concat(chunks).toString('utf8'))
          if (parsed.code !== 0) {
            finish(new Error(`B 站 API 业务码 ${parsed.code}: ${String(parsed.message ?? '').slice(0, 100)}`))
            return
          }
          finish(null, parsed.data)
        } catch {
          finish(new Error('B 站 API 未返回有效 JSON'))
        }
      })
    })
    request.end()
  })
}

async function loginStatus() {
  const data = await apiJson('/x/web-interface/nav')
  return { loggedIn: data?.isLogin === true, name: data?.isLogin ? String(data.uname ?? '') : '' }
}

function openLoginWindow() {
  if (loginWindow && !loginWindow.isDestroyed()) {
    loginWindow.focus()
    return
  }
  loginWindow = new BrowserWindow({
    width: 1120,
    height: 800,
    title: 'B 站登录（仅保存在本机）',
    webPreferences: {
      partition: BILI_PARTITION,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  })
  loginWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      const parsed = new URL(url)
      if (parsed.protocol === 'https:' &&
        (parsed.hostname === 'bilibili.com' || parsed.hostname.endsWith('.bilibili.com'))) {
        return { action: 'allow', overrideBrowserWindowOptions: { webPreferences: {
          partition: BILI_PARTITION, nodeIntegration: false, contextIsolation: true, sandbox: true
        } } }
      }
    } catch { /* reject malformed popup URL */ }
    return { action: 'deny' }
  })
  loginWindow.on('closed', () => {
    loginWindow = null
    clearTimeout(loginCheckTimer)
  })
  loginWindow.loadURL('https://www.bilibili.com/')
}

async function completeLogin(status, generation, expectedWindow) {
  if (!status.loggedIn || generation !== authGeneration ||
    loginWindow !== expectedWindow) return
  await biliSession.cookies.flushStore()
  if (generation !== authGeneration || loginWindow !== expectedWindow) return
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('probe:login-success', status)
  }
  if (loginWindow && !loginWindow.isDestroyed()) loginWindow.close()
}

function scheduleLoginCheck() {
  if (!loginWindow || loginWindow.isDestroyed()) return
  clearTimeout(loginCheckTimer)
  const generation = authGeneration
  const expectedWindow = loginWindow
  loginCheckTimer = setTimeout(async () => {
    try {
      const status = await loginStatus()
      await completeLogin(status, generation, expectedWindow)
    } catch {
      // Network or session errors leave the login window open for a manual check.
    }
  }, 500)
}

async function probeMediaCandidate(url) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 5000)
  let totalBytes
  try {
    const response = await net.fetch(url, {
      method: 'GET',
      headers: { Referer: 'https://www.bilibili.com/', Range: 'bytes=0-1' },
      credentials: 'omit',
      redirect: 'error',
      signal: controller.signal
    })
    const rangeMatch = /^bytes 0-1\/(\d+)$/i.exec(response.headers.get('content-range') ?? '')
    await response.body?.cancel()
    if (response.status !== 206 || !rangeMatch) return null
    totalBytes = Number(rangeMatch[1])
  } catch {
    return null
  } finally {
    clearTimeout(timer)
  }
  const result = { url, totalBytes, sampleMbps: 0 }
  try {
    const [range] = benchmarkRanges(totalBytes)
    const [, startByte, endByte] = /^bytes=(\d+)-(\d+)$/.exec(range)
    const expectedBytes = Number(endByte) - Number(startByte) + 1
    const sample = await sampleMediaRange(url, range, expectedBytes, 'no-store', 4000)
    if (!sample.error) result.sampleMbps = sample.mbps
  } catch {
    // Small files and failed samples remain usable after the short Range check.
  }
  return result
}

async function chooseMediaUrl(track) {
  const candidates = candidateUrls(track).slice(0, 4)
  if (!candidates.length) throw new Error('没有受允许的 CDN 候选地址')
  const usableProbes = (await Promise.all(candidates.map(probeMediaCandidate))).filter(Boolean)
  const selected = fastestMediaProbe(usableProbes)
  if (!selected) throw new Error('所有 CDN 候选地址均未通过 Range 验证')
  const usableCandidates = [selected, ...usableProbes.filter(probe =>
    probe !== selected && probe.totalBytes === selected.totalBytes)
    .sort((a, b) => b.sampleMbps - a.sampleMbps)].map(probe => probe.url)
  return { ...selected, candidates, usableCandidates }
}

async function resolveVideo(input, requestedQuality) {
  const startedAt = performance.now()
  const maxQuality = Number(requestedQuality)
  if (![32, 64, 80].includes(maxQuality)) throw new Error('画质上限无效')
  const status = await loginStatus()
  if (!status.loggedIn) throw new Error('请先在弹出的 B 站窗口登录，然后检查登录状态')
  const { bvid, page } = parseVideoInput(input)
  const pages = await apiJson(`/x/player/pagelist?bvid=${encodeURIComponent(bvid)}`)
  if (!Array.isArray(pages) || !pages[page - 1]) throw new Error('分 P 不存在')
  const selectedPage = pages[page - 1]
  const data = await apiJson(`/x/player/playurl?bvid=${encodeURIComponent(bvid)}&cid=${encodeURIComponent(selectedPage.cid)}&qn=${maxQuality}&fnval=16&fourk=1`)
  if (!data?.dash) throw new Error('上游没有返回普通 DASH；可能需要会员、地区许可或不支持此视频')
  const tracks = pickTracks(data.dash, maxQuality)
  const [videoMedia, audioMedia] = await Promise.all([
    chooseMediaUrl(tracks.video), chooseMediaUrl(tracks.audio)
  ])
  const tokens = { video: mediaToken(), audio: mediaToken() }
  const duration = Number(selectedPage.duration) || Number(data.timelength) / 1000
  const mpd = buildMpd(tracks, duration, tokens)

  mediaEntries.clear()
  mediaTraces.length = 0
  currentVideoToken = tokens.video
  const expiresAt = Date.now() + 10 * 60 * 1000
  mediaEntries.set(tokens.video, { ...videoMedia, kind: 'video', expiresAt })
  mediaEntries.set(tokens.audio, { ...audioMedia, kind: 'audio', expiresAt })

  return {
    mpd,
    bvid,
    cid: Number(selectedPage.cid),
    title: String(selectedPage.part || bvid),
    page,
    quality: Number(tracks.video.id),
    videoTracks: describeVideoTracks(data.dash, maxQuality, tracks.video),
    duration,
    resolveSeconds: (performance.now() - startedAt) / 1000,
    videoHost: new URL(videoMedia.url).hostname,
    audioHost: new URL(audioMedia.url).hostname,
    videoProbeMbps: videoMedia.sampleMbps,
    audioProbeMbps: audioMedia.sampleMbps
  }
}

async function sampleMediaRange(url, range, expectedBytes, cacheMode, timeoutMs = 12000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const startedAt = performance.now()
  const result = {}
  try {
    const response = await net.fetch(url, {
      method: 'GET',
      headers: { Referer: 'https://www.bilibili.com/', Range: range },
      credentials: 'omit',
      cache: cacheMode,
      redirect: 'error',
      signal: controller.signal
    })
    result.headerSeconds = (performance.now() - startedAt) / 1000
    if (response.status !== 206) {
      await response.body?.cancel()
      throw new Error(`HTTP ${response.status}`)
    }
    const bytes = (await response.arrayBuffer()).byteLength
    if (bytes !== expectedBytes) throw new Error('返回字节数不符')
    result.seconds = (performance.now() - startedAt) / 1000
    result.mbps = bytes * 8 / result.seconds / 1e6
  } catch (error) {
    const code = /net::[A-Z0-9_]+/.exec(String(error?.message ?? ''))?.[0]
    result.error = controller.signal.aborted ? `超过 ${timeoutMs / 1000} 秒` :
      code ?? (/^HTTP \d+$/.test(error?.message) ? error.message : '请求失败')
  } finally {
    clearTimeout(timer)
  }
  return result
}

async function benchmarkVideo() {
  const entry = mediaEntries.get(currentVideoToken)
  if (!entry || Date.now() >= entry.expiresAt) {
    throw new Error('当前媒体地址已过期，请重新解析')
  }
  const [directRange, localRange] = benchmarkRanges(entry.totalBytes)
  const [, startByte, endByte] = /^bytes=(\d+)-(\d+)$/.exec(directRange)
  const expectedBytes = Number(endByte) - Number(startByte) + 1
  const results = []
  for (const [index, url] of entry.candidates.entries()) {
    const result = {
      index: index + 1,
      host: new URL(url).hostname,
      selected: url === entry.url,
      ...(await sampleMediaRange(url, directRange, expectedBytes, 'no-store'))
    }
    if (result.selected && result.error) {
      result.normalRequest = await sampleMediaRange(url, localRange, expectedBytes, 'default')
    }
    results.push(result)
  }
  return {
    results,
    directBytes: expectedBytes,
    localRange,
    localUrl: `${APP_ORIGIN}/media/${currentVideoToken}`
  }
}

function failOverMedia(entry, failedUrl, trace) {
  if (!entry || entry.url !== failedUrl) return
  const nextUrl = nextMediaCandidate(entry.usableCandidates, failedUrl)
  if (!nextUrl) return
  entry.url = nextUrl
  if (trace) trace.switchedTo = new URL(nextUrl).hostname
}

async function mediaResponse(request, token) {
  const entry = mediaEntries.get(token)
  if (!entry || Date.now() >= entry.expiresAt) {
    return new Response('Media token expired', { status: 410 })
  }
  const range = request.headers.get('range')
  if (range && !/^bytes=\d+-\d*$/.test(range)) {
    return new Response('Invalid Range', { status: 416 })
  }
  const benchmark = new URL(request.url).searchParams.get('benchmark') === '1'
  const mediaUrl = entry.url
  const trace = benchmark ? null : {
    id: nextMediaTraceId++, kind: entry.kind, host: new URL(mediaUrl).hostname,
    range: range ?? 'full', startedAt: Date.now(), state: 'connecting',
    bytes: 0, expectedBytes: 0, headerMs: null, firstByteMs: null, finishedAt: null,
    statusCode: null, error: null, switchedTo: null
  }
  if (trace) {
    mediaTraces.push(trace)
    if (mediaTraces.length > 20) mediaTraces.shift()
  }
  try {
    const headers = { Referer: 'https://www.bilibili.com/' }
    if (range) headers.Range = range
    const upstream = await net.fetch(mediaUrl, {
      method: 'GET',
      headers,
      credentials: 'omit',
      cache: benchmark ? 'no-store' : 'default',
      redirect: 'error'
    })
    if (trace) {
      trace.headerMs = Date.now() - trace.startedAt
      trace.statusCode = upstream.status
      trace.expectedBytes = Number(upstream.headers.get('content-length')) || 0
      trace.state = 'receiving'
    }
    if (range && upstream.status !== 206) {
      await upstream.body?.cancel()
      if (trace) { trace.state = 'error'; trace.error = 'Range rejected'; trace.finishedAt = Date.now() }
      if (!benchmark) failOverMedia(entry, mediaUrl, trace)
      console.warn('[desktop probe] CDN did not honor Range:', upstream.status)
      return new Response('CDN did not honor Range', { status: 502 })
    }
    const responseHeaders = new Headers({ 'Access-Control-Allow-Origin': APP_ORIGIN })
    for (const name of ['content-type', 'content-length', 'content-range', 'accept-ranges']) {
      const value = upstream.headers.get(name)
      if (value) responseHeaders.set(name, value)
    }
    if (!upstream.ok) {
      await upstream.body?.cancel()
      if (trace) { trace.state = 'error'; trace.error = `HTTP ${upstream.status}`; trace.finishedAt = Date.now() }
      if (!benchmark) failOverMedia(entry, mediaUrl, trace)
      console.warn('[desktop probe] CDN request failed:', upstream.status)
      return new Response(`CDN returned HTTP ${upstream.status}`, { status: 502 })
    }
    if (!trace || !upstream.body) {
      return new Response(upstream.body, { status: upstream.status, headers: responseHeaders })
    }
    const monitored = checkedMediaStream(upstream.body, trace.expectedBytes, received => {
      if (trace.firstByteMs === null) trace.firstByteMs = Date.now() - trace.startedAt
      trace.bytes = received
    })
    monitored.completed.then(() => {
      trace.state = 'complete'
      trace.finishedAt = Date.now()
    }).catch(error => {
      trace.state = 'error'
      trace.finishedAt = Date.now()
      trace.error = error?.message === 'media segment length mismatch' ? 'segment truncated' :
        (/net::[A-Z0-9_]+/.exec(String(error?.message ?? ''))?.[0] ??
          (error?.name === 'AbortError' ? 'stream aborted' : 'stream interrupted'))
      if (trace.expectedBytes > trace.bytes &&
        (trace.error === 'segment truncated' || trace.finishedAt - trace.startedAt >= 2000)) {
        failOverMedia(entry, mediaUrl, trace)
      }
    })
    return new Response(monitored.readable, { status: upstream.status, headers: responseHeaders })
  } catch (error) {
    if (trace) {
      trace.state = 'error'
      trace.finishedAt = Date.now()
      trace.error = /net::[A-Z0-9_]+/.exec(String(error?.message ?? ''))?.[0] ?? 'request failed'
    }
    if (!benchmark) failOverMedia(entry, mediaUrl, trace)
    return new Response('CDN request failed', { status: 502 })
  }
}

async function appResponse(request) {
  if (request.method !== 'GET') return new Response('Method not allowed', { status: 405 })
  const url = new URL(request.url)
  if (url.hostname !== 'app') return new Response('Not found', { status: 404 })
  const mediaMatch = /^\/media\/([0-9a-f]{40})$/.exec(url.pathname)
  if (mediaMatch) return mediaResponse(request, mediaMatch[1])

  const staticFiles = {
    '/': ['index.html', 'text/html; charset=utf-8'],
    '/index.html': ['index.html', 'text/html; charset=utf-8'],
    '/renderer.js': ['renderer.js', 'text/javascript; charset=utf-8'],
    '/shaka.js': ['node_modules/shaka-player/dist/shaka-player.compiled.js', 'text/javascript; charset=utf-8']
  }
  const selected = staticFiles[url.pathname]
  if (!selected) return new Response('Not found', { status: 404 })
  try {
    const body = await fs.readFile(path.join(__dirname, selected[0]))
    return new Response(body, { headers: { 'Content-Type': selected[1], 'Cache-Control': 'no-store' } })
  } catch {
    return new Response('Required file missing; run npm install in this probe directory', { status: 500 })
  }
}

app.whenReady().then(() => {
  biliSession = session.fromPartition(BILI_PARTITION)
  biliSession.cookies.on('changed', (_event, cookie, _cause, removed) => {
    if (!removed && cookie.name === 'SESSDATA' &&
      /(^|\.)bilibili\.com$/.test(cookie.domain)) scheduleLoginCheck()
  })
  session.defaultSession.protocol.handle('icinema-probe', appResponse)

  ipcMain.handle('probe:open-login', event => { assertAppFrame(event); openLoginWindow() })
  ipcMain.handle('probe:status', async event => {
    assertAppFrame(event)
    const generation = authGeneration
    const expectedWindow = loginWindow
    const status = await loginStatus()
    if (expectedWindow) await completeLogin(status, generation, expectedWindow)
    return status
  })
  ipcMain.handle('probe:resolve', (event, input, quality) => { assertAppFrame(event); return resolveVideo(input, quality) })
  ipcMain.handle('probe:benchmark', event => { assertAppFrame(event); return benchmarkVideo() })
  ipcMain.handle('probe:traffic', event => {
    assertAppFrame(event)
    const now = Date.now()
    return mediaTraces.slice(-8).reverse().map(trace => ({
      id: trace.id, kind: trace.kind, host: trace.host, range: trace.range,
      state: trace.state, bytes: trace.bytes, expectedBytes: trace.expectedBytes,
      elapsedMs: (trace.finishedAt ?? now) - trace.startedAt,
      headerMs: trace.headerMs, firstByteMs: trace.firstByteMs,
      statusCode: trace.statusCode, error: trace.error, switchedTo: trace.switchedTo
    }))
  })
  ipcMain.handle('probe:logout', async event => {
    assertAppFrame(event)
    authGeneration += 1
    mediaEntries.clear()
    mediaTraces.length = 0
    currentVideoToken = undefined
    clearTimeout(loginCheckTimer)
    if (loginWindow && !loginWindow.isDestroyed()) loginWindow.close()
    await biliSession.clearStorageData()
    await biliSession.clearCache()
    await biliSession.cookies.flushStore()
    return { loggedIn: false }
  })

  mainWindow = new BrowserWindow({
    width: 1060,
    height: 860,
    title: 'iCinema B 站桌面播放验证',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  })
  mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
  mainWindow.loadURL(`${APP_ORIGIN}/`)
})

app.on('window-all-closed', () => app.quit())
