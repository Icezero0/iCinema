const test = require('node:test')
const assert = require('node:assert/strict')
const {
  isAllowedMediaUrl, candidateUrls, pickTracks, buildMpd,
  fastestMediaProbe, nextMediaCandidate
} = require('./bilibili-media.cjs')

function track(id, codecs, url) {
  return {
    id, codecs, bandwidth: 1_000_000, width: 1920, height: 1080,
    baseUrl: url,
    backupUrl: ['https://upos-hz-mirrorakam.akamaized.net/backup'],
    SegmentBase: { Initialization: '0-1023', indexRange: '1024-2047' }
  }
}

test('Bilibili media URLs stay within the proven CDN allowlist', () => {
  assert.equal(isAllowedMediaUrl('https://upos-sz-mirrorcosov.bilivideo.com/video'), true)
  assert.equal(isAllowedMediaUrl('https://upos-hz-mirrorakam.akamaized.net/video'), true)
  assert.equal(isAllowedMediaUrl('https://bilivideo.com.evil.example/video'), false)
  assert.equal(isAllowedMediaUrl('https://127.0.0.1/video'), false)
  assert.equal(isAllowedMediaUrl('http://upos-sz-mirrorcosov.bilivideo.com/video'), false)
  assert.equal(isAllowedMediaUrl('https://user@upos-sz-mirrorcosov.bilivideo.com/video'), false)
})

test('DASH selection excludes unsupported codecs and keeps only allowed candidates', () => {
  const dash = {
    video: [
      track(80, 'hvc1.1.6', 'https://upos-sz-mirrorcosov.bilivideo.com/h265'),
      track(80, 'avc1.640033', 'https://upos-sz-mirrorcosov.bilivideo.com/h264')
    ],
    audio: [track(30280, 'mp4a.40.2', 'https://127.0.0.1/not-allowed')]
  }
  const selected = pickTracks(dash, 80)
  assert.equal(selected.video.codecs, 'avc1.640033')
  assert.deepEqual(candidateUrls(selected.audio), ['https://upos-hz-mirrorakam.akamaized.net/backup'])
  const mpd = buildMpd(selected, 357, { video: 'a'.repeat(40), audio: 'b'.repeat(40) }, 'icinema-bili://app')
  assert.match(mpd, /icinema-bili:\/\/app\/media\/a{40}/)
  assert.doesNotMatch(mpd, /bilivideo\.com|akamaized\.net/)
  assert.throws(() => buildMpd(selected, 357, { video: 'a', audio: 'b' }, 'https://evil.example'))
})

test('CDN selection prefers the faster validated candidate and advances on failure', () => {
  const probes = [
    { url: 'slow', sampleMbps: 0.4 },
    { url: 'fast', sampleMbps: 4.5 }
  ]
  assert.equal(fastestMediaProbe(probes).url, 'fast')
  assert.equal(nextMediaCandidate(['fast', 'slow'], 'fast'), 'slow')
  assert.equal(nextMediaCandidate(['fast', 'slow'], 'slow'), 'fast')
})
