const { test } = require('node:test')
const assert = require('node:assert/strict')
const { parseVideoInput, isAllowedMediaUrl, describeVideoTracks, pickTracks, benchmarkRanges, fastestMediaProbe, nextMediaCandidate, checkedMediaStream, buildMpd } = require('./bilibili.cjs')

test('only the expected BV and video URL forms are accepted', () => {
  assert.deepEqual(parseVideoInput('BV1EGfzBREBQ'), { bvid: 'BV1EGfzBREBQ', page: 1 })
  assert.deepEqual(parseVideoInput('BV1JneT6rEaG'), { bvid: 'BV1JneT6rEaG', page: 1 })
  assert.deepEqual(parseVideoInput('https://www.bilibili.com/video/BV1EGfzBREBQ?p=2'), { bvid: 'BV1EGfzBREBQ', page: 2 })
  assert.throws(() => parseVideoInput('https://www.bilibili.com.evil.test/video/BV1EGfzBREBQ'))
  assert.throws(() => parseVideoInput('https://www.bilibili.com/video/BV1EGfzBREBQ?p=1&p=2'))
})

test('media host filter rejects arbitrary and deceptive URLs', () => {
  assert.equal(isAllowedMediaUrl('https://upos.example.bilivideo.com/a.m4s'), true)
  assert.equal(isAllowedMediaUrl('https://upos-hz-mirrorakam.akamaized.net/a.m4s'), true)
  for (const url of [
    'http://upos.example.bilivideo.com/a.m4s',
    'https://evilbilivideo.com/a.m4s',
    'https://upos.example.bilivideo.com.evil.test/a.m4s',
    'https://upos-hz-mirrorakam.akamaized.net.evil.test/a.m4s',
    'https://other-tenant.akamaized.net/a.m4s',
    'https://user:pass@upos.example.bilivideo.com/a.m4s',
    'https://127.0.0.1/a.m4s'
  ]) assert.equal(isAllowedMediaUrl(url), false, url)
})

test('track diagnostics expose host names but not signed URLs', () => {
  const url = 'https://upos-hz-mirrorakam.akamaized.net/media?deadline=secret'
  const track = { id: 80, codecs: 'avc1.640033', bandwidth: 1500000, baseUrl: url }
  const description = describeVideoTracks({ video: [track] }, 80, track)
  assert.deepEqual(description[0].hosts, [{ host: 'upos-hz-mirrorakam.akamaized.net', allowed: true }])
  assert.equal(description[0].selected, true)
  assert.doesNotMatch(JSON.stringify(description), /secret|deadline|\/media/)
})

test('AVC/AAC tracks become a SegmentBase MPD using only local media IDs', () => {
  const segment = { initialization: '0-999', indexRange: '1000-1999' }
  const url = 'https://upos.example.bilivideo.com/private?deadline=123'
  const tracks = pickTracks({
    video: [
      { id: 80, codecs: 'hev1.1.6.L93', baseUrl: url, SegmentBase: segment },
      { id: 64, codecs: 'avc1.640028', bandwidth: 1000000, width: 1280, height: 720, baseUrl: url, SegmentBase: segment }
    ],
    audio: [{ id: 30280, codecs: 'mp4a.40.2', bandwidth: 128000, baseUrl: url, SegmentBase: segment }]
  })
  const mpd = buildMpd(tracks, 120, { video: 'video-token', audio: 'audio-token' })
  assert.match(mpd, /SegmentBase indexRange="1000-1999"/)
  assert.match(mpd, /icinema-probe:\/\/app\/media\/video-token/)
  assert.doesNotMatch(mpd, /bilivideo\.com|deadline=/)
})

test('quality cap selects a lower AVC track for comparison', () => {
  const segment = { initialization: '0-100', indexRange: '101-200' }
  const baseUrl = 'https://upos.example.bilivideo.com/media'
  const dash = {
    video: [32, 64, 80].map(id => ({ id, codecs: 'avc1.640028', baseUrl, SegmentBase: segment })),
    audio: [{ codecs: 'mp4a.40.2', baseUrl, SegmentBase: segment }]
  }
  assert.equal(pickTracks(dash, 32).video.id, 32)
  assert.equal(pickTracks(dash, 64).video.id, 64)
  assert.equal(pickTracks(dash, 80).video.id, 80)
})

test('benchmark ranges are bounded, equal-sized, and distinct', () => {
  const total = 8 * 1024 * 1024
  const ranges = benchmarkRanges(total).map(value => {
    const match = /^bytes=(\d+)-(\d+)$/.exec(value)
    assert.ok(match)
    return [Number(match[1]), Number(match[2])]
  })
  assert.equal(ranges[0][1] - ranges[0][0], ranges[1][1] - ranges[1][0])
  assert.ok(ranges[0][1] < ranges[1][0])
  assert.ok(ranges[1][1] < total)
  assert.throws(() => benchmarkRanges(100))
})

test('a slow but Range-valid primary CDN loses to a faster backup', () => {
  const primary = { url: 'primary', sampleMbps: 0.4 }
  const backup = { url: 'backup', sampleMbps: 4.5 }
  assert.equal(fastestMediaProbe([primary, backup]), backup)
  assert.equal(fastestMediaProbe([primary, null]), primary)
  assert.equal(fastestMediaProbe([primary, { url: 'failed sample', sampleMbps: 0 }]), primary)
  assert.equal(fastestMediaProbe([null, null]), null)
})

test('a failed media request can move to the next validated CDN without cycling back', () => {
  const candidates = ['https://primary.example/video', 'https://backup.example/video']
  assert.equal(nextMediaCandidate(candidates, candidates[0]), candidates[1])
  assert.equal(nextMediaCandidate(candidates, candidates[1]), null)
  assert.equal(nextMediaCandidate(candidates, 'https://unknown.example/video'), null)
})

test('a short media body cannot be reported as a complete Range response', async () => {
  const source = new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array(3))
      controller.close()
    }
  })
  const lengths = []
  const stream = checkedMediaStream(source, 5, received => lengths.push(received))
  const completion = stream.completed.catch(error => error)
  await assert.rejects(new Response(stream.readable).arrayBuffer(), /media segment length mismatch/)
  assert.match((await completion).message, /media segment length mismatch/)
  assert.deepEqual(lengths, [3])

  const fullSource = new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array(5))
      controller.close()
    }
  })
  const full = checkedMediaStream(fullSource, 5, () => {})
  assert.equal((await new Response(full.readable).arrayBuffer()).byteLength, 5)
  await full.completed
})
