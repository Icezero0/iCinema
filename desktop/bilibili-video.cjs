const BVID_PATTERN = /^BV[A-Za-z0-9]{10}$/

function bilibiliImageUrl(value) {
  if (typeof value !== 'string' || !value) return null
  try {
    const url = new URL(value.startsWith('//') ? `https:${value}` : value)
    if (url.protocol === 'http:') url.protocol = 'https:'
    if (url.protocol !== 'https:' || url.username || url.password ||
        (url.hostname !== 'hdslb.com' && !url.hostname.endsWith('.hdslb.com'))) return null
    return url.href
  } catch {
    return null
  }
}

function cleanText(value, limit) {
  return typeof value === 'string' ? value.trim().slice(0, limit) : ''
}

function positiveInteger(value) {
  return Number.isSafeInteger(value) && value > 0 ? value : null
}

function duration(value) {
  return Number.isSafeInteger(value) && value >= 0 ? value : 0
}

function bilibiliVideoInfoFromView(response, requestedBvid) {
  if (!BVID_PATTERN.test(requestedBvid)) throw new Error('BILIBILI_BVID_INVALID')
  if (response?.code !== 0 || !response.data || typeof response.data !== 'object') {
    throw new Error('BILIBILI_VIDEO_UNAVAILABLE')
  }
  const data = response.data
  const title = cleanText(data.title, 300)
  if (!title) throw new Error('BILIBILI_VIDEO_UNAVAILABLE')

  const pages = []
  const seenPages = new Set()
  if (Array.isArray(data.pages)) {
    for (const item of data.pages.slice(0, 1000)) {
      const page = positiveInteger(item?.page)
      const cid = positiveInteger(item?.cid)
      if (!page || !cid || seenPages.has(page)) continue
      seenPages.add(page)
      pages.push({
        page,
        cid,
        title: cleanText(item.part, 200) || `P${page}`,
        durationSeconds: duration(item.duration)
      })
    }
  }
  if (!pages.length && positiveInteger(data.cid)) {
    pages.push({ page: 1, cid: data.cid, title, durationSeconds: duration(data.duration) })
  }
  if (!pages.length) throw new Error('BILIBILI_VIDEO_UNAVAILABLE')

  return {
    bvid: requestedBvid,
    title,
    coverUrl: bilibiliImageUrl(data.pic),
    description: cleanText(data.desc, 4000),
    uploader: cleanText(data.owner?.name, 100),
    durationSeconds: duration(data.duration),
    pages
  }
}

module.exports = { BVID_PATTERN, bilibiliImageUrl, bilibiliVideoInfoFromView }
