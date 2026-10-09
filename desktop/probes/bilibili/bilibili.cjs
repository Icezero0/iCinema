const crypto = require('node:crypto')

const BVID_PATTERN = /^BV[0-9A-Za-z]{10}$/
const RANGE_PATTERN = /^\d+-\d+$/

function parseVideoInput(value) {
  const raw = String(value ?? '').trim()
  if (BVID_PATTERN.test(raw)) return { bvid: raw, page: 1 }

  let url
  try {
    url = new URL(raw)
  } catch {
    throw new Error('请输入 BV 号或 bilibili.com/video 链接')
  }
  if (url.protocol !== 'https:' || !['www.bilibili.com', 'm.bilibili.com'].includes(url.hostname)) {
    throw new Error('仅接受 B 站 HTTPS 视频链接')
  }
  const match = /^\/video\/(BV[0-9A-Za-z]{10})\/?$/.exec(url.pathname)
  if (!match) throw new Error('链接中没有有效 BV 号')
  const pageValues = url.searchParams.getAll('p')
  if (pageValues.length > 1 || (pageValues.length === 1 && !/^[1-9]\d{0,2}$/.test(pageValues[0]))) {
    throw new Error('分 P 参数无效')
  }
  return { bvid: match[1], page: pageValues.length ? Number(pageValues[0]) : 1 }
}

function isAllowedMediaUrl(value) {
  try {
    const url = new URL(value)
    const host = url.hostname.toLowerCase()
    const allowedHost = host.endsWith('.bilivideo.com') ||
      /^upos-[a-z0-9-]+\.akamaized\.net$/.test(host)
    return url.protocol === 'https:' && allowedHost &&
      url.username === '' && url.password === '' && url.port === ''
  } catch {
    return false
  }
}

function describeVideoTracks(dash, maxQuality, selectedTrack) {
  return (dash?.video ?? [])
    .filter(track => Number(track.id) <= maxQuality)
    .slice(0, 20)
    .map(track => {
      const rawUrls = [track.baseUrl ?? track.base_url,
        ...(Array.isArray(track.backupUrl ?? track.backup_url)
          ? track.backupUrl ?? track.backup_url : [])]
      const hosts = rawUrls.flatMap(value => {
        try {
          const host = new URL(value).hostname.toLowerCase()
          return [{ host, allowed: isAllowedMediaUrl(value) }]
        } catch {
          return []
        }
      }).filter((item, index, items) =>
        items.findIndex(other => other.host === item.host) === index)
      return {
        quality: Number(track.id),
        codec: String(track.codecs ?? '').split('.')[0],
        bandwidth: Number(track.bandwidth) || 0,
        selected: track === selectedTrack,
        hosts
      }
    })
    .sort((a, b) => b.quality - a.quality || b.bandwidth - a.bandwidth)
}

function candidateUrls(track) {
  const primary = track.baseUrl ?? track.base_url
  const backup = track.backupUrl ?? track.backup_url ?? []
  return [primary, ...(Array.isArray(backup) ? backup : [])].filter(isAllowedMediaUrl)
}

function segmentBase(track) {
  const segment = track.SegmentBase ?? track.segmentBase ?? track.segment_base
  const initialization = segment?.Initialization ?? segment?.initialization
  const indexRange = segment?.indexRange ?? segment?.index_range
  if (!RANGE_PATTERN.test(initialization ?? '') || !RANGE_PATTERN.test(indexRange ?? '')) {
    throw new Error('DASH 轨道缺少有效的 SegmentBase 字节范围')
  }
  return { initialization, indexRange }
}

function pickTracks(dash, maxQuality = 80) {
  if (![32, 64, 80].includes(maxQuality)) throw new Error('画质上限无效')
  const videos = (dash?.video ?? []).filter(track =>
    String(track.codecs ?? '').startsWith('avc1.') &&
    Number(track.id) <= maxQuality && candidateUrls(track).length > 0)
  const audios = (dash?.audio ?? []).filter(track =>
    String(track.codecs ?? '').startsWith('mp4a.') && candidateUrls(track).length > 0)
  videos.sort((a, b) => Number(b.id ?? 0) - Number(a.id ?? 0) || Number(b.bandwidth ?? 0) - Number(a.bandwidth ?? 0))
  audios.sort((a, b) => Number(b.bandwidth ?? 0) - Number(a.bandwidth ?? 0))
  if (!videos.length || !audios.length) throw new Error('没有可用的普通 AVC/AAC DASH 轨道')
  segmentBase(videos[0])
  segmentBase(audios[0])
  return { video: videos[0], audio: audios[0] }
}

function mediaToken() {
  return crypto.randomBytes(20).toString('hex')
}

function benchmarkRanges(totalBytes) {
  const total = Number(totalBytes)
  if (!Number.isSafeInteger(total) || total < 256 * 1024) {
    throw new Error('媒体文件太小，无法进行分段测速')
  }
  const size = Math.min(512 * 1024, Math.floor(total / 4))
  const firstStart = Math.floor(total / 3)
  const secondStart = firstStart + size
  return [firstStart, secondStart].map(start => `bytes=${start}-${start + size - 1}`)
}

function fastestMediaProbe(probes) {
  const usable = probes.filter(Boolean)
  if (!usable.length) return null
  return usable.reduce((best, probe) =>
    probe.sampleMbps > best.sampleMbps ? probe : best)
}

function nextMediaCandidate(usableCandidates, currentUrl) {
  const index = usableCandidates.indexOf(currentUrl)
  return index >= 0 ? usableCandidates[index + 1] ?? null : null
}

function checkedMediaStream(source, expectedBytes, onChunk) {
  let received = 0
  const monitor = new TransformStream({
    transform(chunk, controller) {
      received += chunk.byteLength
      onChunk(received)
      if (expectedBytes > 0 && received > expectedBytes) {
        throw new Error('media segment length mismatch')
      }
      controller.enqueue(chunk)
    },
    flush() {
      if (expectedBytes > 0 && received !== expectedBytes) {
        throw new Error('media segment length mismatch')
      }
    }
  })
  return { readable: monitor.readable, completed: source.pipeTo(monitor.writable) }
}

function xmlAttribute(value) {
  return String(value).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[ch])
}

function representation(track, kind, token) {
  const segment = segmentBase(track)
  const bandwidth = Math.max(1, Number(track.bandwidth) || 1)
  const dimensions = kind === 'video'
    ? ` width="${Math.max(1, Number(track.width) || 1)}" height="${Math.max(1, Number(track.height) || 1)}"`
    : ''
  return `<AdaptationSet mimeType="${kind}/mp4" segmentAlignment="true"><Representation id="${kind}" bandwidth="${bandwidth}" codecs="${xmlAttribute(track.codecs)}"${dimensions}><BaseURL>icinema-probe://app/media/${token}</BaseURL><SegmentBase indexRange="${segment.indexRange}"><Initialization range="${segment.initialization}"/></SegmentBase></Representation></AdaptationSet>`
}

function buildMpd(tracks, durationSeconds, tokens) {
  const duration = Number(durationSeconds)
  if (!Number.isFinite(duration) || duration <= 0) throw new Error('上游没有有效的播放时长')
  return `<?xml version="1.0" encoding="UTF-8"?><MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" mediaPresentationDuration="PT${duration}S" minBufferTime="PT1.5S" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011"><Period>${representation(tracks.video, 'video', tokens.video)}${representation(tracks.audio, 'audio', tokens.audio)}</Period></MPD>`
}

module.exports = { parseVideoInput, isAllowedMediaUrl, candidateUrls, describeVideoTracks, segmentBase, pickTracks, mediaToken, benchmarkRanges, fastestMediaProbe, nextMediaCandidate, checkedMediaStream, buildMpd }
