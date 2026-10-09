const video = document.getElementById('video')
const statusNode = document.getElementById('status')
const titleNode = document.getElementById('video-title')
const metricsNode = document.getElementById('metrics')
const trafficNode = document.getElementById('media-traffic')
const seekButton = document.getElementById('seek')
const rateButton = document.getElementById('rate')
const resolveButton = document.getElementById('resolve')
const benchmarkButton = document.getElementById('benchmark')
const benchmarkNode = document.getElementById('benchmark-result')
const sourceNode = document.getElementById('source-overview')
const MAX_BUFFER_AHEAD_SECONDS = 300
let player
let manifestUrl
let localSchemeRegistered = false
let waitingCount = 0
let trafficLoading = false
let bufferingGoalSeconds = 10
const mediaEvents = []
let lastObservedTime = 0
let lastObservedBufferEnd = 0

function recordMediaEvent(message) {
  mediaEvents.push(`${new Date().toLocaleTimeString('zh-CN', { hour12: false })} · ${message} · 位置 ${video.currentTime.toFixed(1)} 秒`)
  if (mediaEvents.length > 8) mediaEvents.shift()
}

function setStatus(message, error = false) {
  statusNode.textContent = message
  statusNode.classList.toggle('error', error)
}

function errorText(error) {
  if (error?.code) {
    const uri = Array.isArray(error.data)
      ? error.data.find(value => typeof value === 'string' && /^[a-z][a-z\d+.-]*:/i.test(value))
      : undefined
    const scheme = uri?.split(':', 1)[0]
    return `播放器错误 ${error.code}${scheme ? `（协议：${scheme}）` : ''}`
  }
  return error?.message ?? String(error)
}

async function run(task) {
  try { await task() } catch (error) { setStatus(errorText(error), true) }
}

document.getElementById('login').addEventListener('click', () => run(async () => {
  await window.desktopProbe.openLogin()
  setStatus('请在弹出的 B 站窗口登录。登录成功后窗口会自动关闭。')
}))

window.desktopProbe.onLoginSuccess(result => {
  setStatus(`已登录：${result.name || 'B 站用户'}。登录状态已保存在本机。`)
})

document.getElementById('check').addEventListener('click', () => run(async () => {
  setStatus('正在检查本机会话…')
  const result = await window.desktopProbe.status()
  setStatus(result.loggedIn ? `已登录：${result.name || 'B 站用户'}` : '未登录；请在 B 站窗口完成登录。')
}))

document.getElementById('logout').addEventListener('click', () => run(async () => {
  if (player) await player.unload()
  if (manifestUrl) URL.revokeObjectURL(manifestUrl)
  manifestUrl = undefined
  seekButton.disabled = true
  rateButton.disabled = true
  benchmarkButton.disabled = true
  benchmarkNode.textContent = ''
  sourceNode.textContent = ''
  titleNode.textContent = ''
  await window.desktopProbe.logout()
  setStatus('本机 B 站登录状态已清除。')
}))

resolveButton.addEventListener('click', () => run(async () => {
  resolveButton.disabled = true
  try {
    setStatus('正在用本机登录态解析 B 站视频…')
    if (player) await player.unload()
    if (manifestUrl) URL.revokeObjectURL(manifestUrl)
    manifestUrl = undefined
    waitingCount = 0
    lastObservedTime = 0
    lastObservedBufferEnd = 0
    mediaEvents.length = 0
    recordMediaEvent('开始加载')
    seekButton.disabled = true
    rateButton.disabled = true
    benchmarkButton.disabled = true
    benchmarkNode.textContent = ''
    sourceNode.textContent = ''

    const result = await window.desktopProbe.resolve(
      document.getElementById('video-input').value,
      Number(document.getElementById('quality').value)
    )
    titleNode.textContent = `${result.title} · BV ${result.bvid} · P${result.page} · 画质 ${result.quality}`
    sourceNode.textContent = result.videoTracks.map(track =>
      `${track.selected ? '当前 ' : ''}${track.quality} · ${track.codec} · ${(track.bandwidth / 1e6).toFixed(1)} Mbps · ` +
      (track.hosts.length ? track.hosts.map(item =>
        `${item.host}${item.allowed ? '' : '（未允许）'}`).join(' / ') : '无候选主机'))
      .join('\n')
    if (!window.shaka) throw new Error('Shaka 未加载，请确认已按说明安装依赖')
    shaka.polyfill.installAll()
    if (!shaka.Player.isBrowserSupported()) {
      throw new Error('此 Chromium 环境不支持 Shaka 所需的播放能力')
    }
    if (!localSchemeRegistered) {
      if (!shaka.net?.HttpFetchPlugin?.parse) {
        throw new Error('Shaka 缺少本机媒体协议所需的 Fetch 插件')
      }
      shaka.net.NetworkingEngine.registerScheme(
        'icinema-probe',
        shaka.net.HttpFetchPlugin.parse,
        shaka.net.NetworkingEngine.PluginPriority.PREFERRED,
        true
      )
      localSchemeRegistered = true
    }
    if (!player) {
      player = new shaka.Player()
      await player.attach(video)
      player.addEventListener('error', event => {
        recordMediaEvent(errorText(event.detail))
        setStatus(errorText(event.detail), true)
      })
    }
    bufferingGoalSeconds = Math.min(Math.ceil(result.duration), MAX_BUFFER_AHEAD_SECONDS)
    if (!player.configure({ streaming: { bufferingGoal: bufferingGoalSeconds } })) {
      throw new Error('播放器拒绝了预缓冲配置')
    }
    manifestUrl = URL.createObjectURL(new Blob([result.mpd], { type: 'application/dash+xml' }))
    setStatus('已取得 DASH，正在通过本机媒体协议加载…')
    const loadStartedAt = performance.now()
    await player.load(manifestUrl)
    seekButton.disabled = false
    rateButton.disabled = false
    benchmarkButton.disabled = false
    const loadSeconds = (performance.now() - loadStartedAt) / 1000
    const probeLabel = mbps => mbps > 0 ? `预检 ${mbps.toFixed(1)} Mbps` : '预检未完成'
    setStatus(`媒体已加载。解析 ${result.resolveSeconds.toFixed(1)} 秒；播放器加载 ${loadSeconds.toFixed(1)} 秒。请按播放键。\n视频 CDN：${result.videoHost}（${probeLabel(result.videoProbeMbps)}）；音频 CDN：${result.audioHost}（${probeLabel(result.audioProbeMbps)}）。VPS 未参与。`)
  } finally {
    resolveButton.disabled = false
  }
}))

benchmarkButton.addEventListener('click', () => run(async () => {
  benchmarkButton.disabled = true
  resolveButton.disabled = true
  benchmarkNode.textContent = '正在对比 CDN 直连与本机协议的分段下载速度…'
  await player.unload()
  try {
    const direct = await window.desktopProbe.benchmarkVideo()
    const directLines = direct.results.map(result => {
      const measured = result.error ? result.error :
        `${result.mbps.toFixed(1)} Mbps（首响应 ${result.headerSeconds.toFixed(2)} 秒，总计 ${result.seconds.toFixed(2)} 秒）`
      const normal = result.normalRequest
        ? `；普通请求 ${result.normalRequest.error || `${result.normalRequest.mbps.toFixed(1)} Mbps`}` : ''
      return `候选 ${result.index}${result.selected ? '（当前）' : ''} ${result.host}：无缓存 ${measured}${normal}`
    })
    benchmarkNode.textContent = directLines.join('\n')
    const selected = direct.results.find(result => result.selected)
    if (!selected || selected.error) {
      benchmarkNode.textContent += '\n当前 CDN 直连测速失败，跳过本机协议对比。'
      return
    }
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 15000)
    let localBytes
    let localSeconds
    let localHeaderSeconds
    try {
      const startedAt = performance.now()
      const response = await fetch(`${direct.localUrl}?benchmark=1`, {
        headers: { Range: direct.localRange },
        cache: 'no-store',
        signal: controller.signal
      })
      localHeaderSeconds = (performance.now() - startedAt) / 1000
      if (response.status !== 206) throw new Error(`本机协议测速返回 HTTP ${response.status}`)
      localBytes = (await response.arrayBuffer()).byteLength
      localSeconds = (performance.now() - startedAt) / 1000
      if (localBytes !== direct.directBytes) throw new Error('两次测速的分段大小不一致')
    } catch (error) {
      if (controller.signal.aborted) throw new Error('本机协议测速超过 15 秒')
      throw error
    } finally {
      clearTimeout(timer)
    }
    const localMbps = localBytes * 8 / localSeconds / 1e6
    benchmarkNode.textContent += `\n经本机协议 ${localMbps.toFixed(1)} Mbps（首响应 ${localHeaderSeconds.toFixed(2)} 秒，总计 ${localSeconds.toFixed(2)} 秒；样本 ${(localBytes / 1024).toFixed(0)} KiB）`
  } catch (error) {
    benchmarkNode.textContent = errorText(error)
  } finally {
    try {
      await player.load(manifestUrl)
      setStatus('测速结束，媒体已重新加载。请按播放键。')
      benchmarkButton.disabled = false
    } catch (error) {
      seekButton.disabled = true
      rateButton.disabled = true
      throw error
    } finally {
      resolveButton.disabled = false
    }
  }
}))

seekButton.addEventListener('click', () => { video.currentTime = Math.min(video.duration || Infinity, video.currentTime + 10) })
rateButton.addEventListener('click', () => { video.playbackRate = video.playbackRate === 1 ? 1.5 : 1 })
video.addEventListener('waiting', () => { waitingCount += 1 })
for (const name of ['loadstart', 'emptied', 'seeking', 'seeked', 'play', 'pause', 'stalled', 'ended', 'error']) {
  video.addEventListener(name, () => recordMediaEvent(`媒体事件 ${name}`))
}
setInterval(() => {
  if (!video.src && !video.currentSrc) return
  let bufferedAhead = 0
  for (let index = 0; index < video.buffered.length; index += 1) {
    if (video.buffered.start(index) <= video.currentTime && video.currentTime <= video.buffered.end(index)) {
      bufferedAhead = Math.max(0, video.buffered.end(index) - video.currentTime)
      break
    }
  }
  const bufferEnd = video.buffered.length
    ? Math.max(...Array.from({ length: video.buffered.length }, (_, index) => video.buffered.end(index))) : 0
  if (lastObservedTime > 10 && video.currentTime < lastObservedTime - 10) {
    recordMediaEvent(`播放位置从 ${lastObservedTime.toFixed(1)} 秒后退`)
  }
  if (lastObservedBufferEnd > bufferEnd + 15 && Math.abs(video.currentTime - lastObservedTime) < 2) {
    recordMediaEvent(`缓冲终点从 ${lastObservedBufferEnd.toFixed(1)} 秒缩到 ${bufferEnd.toFixed(1)} 秒`)
  }
  lastObservedTime = video.currentTime
  lastObservedBufferEnd = bufferEnd
  const stats = player?.getStats()
  const bandwidth = Number(stats?.estimatedBandwidth)
  const streamBandwidth = Number(stats?.streamBandwidth)
  const decodedFrames = Number(stats?.decodedFrames)
  const droppedFrames = Number(stats?.droppedFrames)
  const videoSize = Number.isFinite(stats?.width) && Number.isFinite(stats?.height)
    ? `${stats.width}×${stats.height}` : '?'
  metricsNode.textContent = `${video.paused ? '暂停' : '播放'} · ${video.currentTime.toFixed(1)} / ${Number.isFinite(video.duration) ? video.duration.toFixed(1) : '?'} 秒 · ${video.playbackRate}×\n` +
    `前方缓冲 ${bufferedAhead.toFixed(1)} 秒 · 缓冲终点 ${bufferEnd.toFixed(1)} 秒 · 预取目标 ${bufferingGoalSeconds} 秒 · 等待事件 ${waitingCount} 次 · 累计缓冲 ${Number(stats?.bufferingTime || 0).toFixed(1)} 秒` +
    `\n当前轨道 ${videoSize} · ${stats?.currentCodecs || '编码未知'}` +
    (Number.isFinite(streamBandwidth) && streamBandwidth > 0 ? ` · 所需码率 ${(streamBandwidth / 1e6).toFixed(1)} Mbps` : '') +
    (Number.isFinite(bandwidth) && bandwidth > 0 ? ` · 估计吞吐 ${(bandwidth / 1e6).toFixed(1)} Mbps` : '') +
    (Number.isFinite(decodedFrames) && Number.isFinite(droppedFrames)
      ? ` · 掉帧 ${droppedFrames}/${decodedFrames}` : '')
}, 1000)

setInterval(async () => {
  if (trafficLoading) return
  trafficLoading = true
  try {
    const traces = await window.desktopProbe.traffic()
    const requestText = traces.length ? '实际播放请求（最近 8 条）：\n' + traces.map(trace => {
      const state = {
        connecting: '等待 CDN 响应', receiving: '接收中',
        complete: '完成', error: `失败${trace.error ? `：${trace.error}` : ''}`
      }[trace.state] ?? trace.state
      const size = `${(trace.bytes / 1024).toFixed(0)}${trace.expectedBytes ? `/${(trace.expectedBytes / 1024).toFixed(0)}` : ''} KiB`
      const timing = [`耗时 ${(trace.elapsedMs / 1000).toFixed(1)} 秒`]
      if (trace.headerMs !== null) timing.push(`响应头 ${(trace.headerMs / 1000).toFixed(1)} 秒`)
      if (trace.firstByteMs !== null) timing.push(`首字节 ${(trace.firstByteMs / 1000).toFixed(1)} 秒`)
      return `${trace.kind === 'video' ? '视频' : '音频'} ${trace.host} · ${trace.range} · ${state} · ${size} · ${timing.join(' · ')}${trace.switchedTo ? ` · 下次改用 ${trace.switchedTo}` : ''}`
    }).join('\n') : '实际播放请求：暂无'
    trafficNode.textContent = `${requestText}\n播放事件（最近 8 条）：\n${mediaEvents.join('\n')}`
  } catch {
    trafficNode.textContent = '实际播放请求诊断暂不可用'
  } finally {
    trafficLoading = false
  }
}, 1000)

window.addEventListener('beforeunload', () => {
  if (manifestUrl) URL.revokeObjectURL(manifestUrl)
  player?.destroy()
})

run(async () => {
  setStatus('正在检查本机保存的 B 站登录状态…')
  const result = await window.desktopProbe.status()
  setStatus(result.loggedIn ? `已登录：${result.name || 'B 站用户'}` : '请先登录 B 站。')
})
