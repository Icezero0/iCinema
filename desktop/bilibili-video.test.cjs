const assert = require('node:assert/strict')
const test = require('node:test')
const { bilibiliVideoInfoFromView } = require('./bilibili-video.cjs')

test('Bilibili video metadata keeps each part and its own CID', () => {
  const bvid = 'BV1a5t264Em6'
  const info = bilibiliVideoInfoFromView({ code: 0, data: {
    title: '  Video title  ', pic: 'http://i0.hdslb.com/bfs/archive/cover.jpg',
    desc: 'Description', duration: 300, cid: 101,
    owner: { name: 'Uploader' },
    pages: [
      { page: 1, cid: 101, part: 'First part', duration: 120 },
      { page: 2, cid: 202, part: 'Second part', duration: 180 }
    ]
  } }, bvid)
  assert.equal(info.bvid, bvid)
  assert.equal(info.title, 'Video title')
  assert.equal(info.coverUrl, 'https://i0.hdslb.com/bfs/archive/cover.jpg')
  assert.equal(info.uploader, 'Uploader')
  assert.deepEqual(info.pages, [
    { page: 1, cid: 101, title: 'First part', durationSeconds: 120 },
    { page: 2, cid: 202, title: 'Second part', durationSeconds: 180 }
  ])
})

test('Bilibili metadata rejects unsafe image URLs and invalid responses', () => {
  const bvid = 'BV1a5t264Em6'
  const data = { title: 'Video', pic: 'https://hdslb.com.evil.example/cover.jpg', cid: 101 }
  assert.equal(bilibiliVideoInfoFromView({ code: 0, data }, bvid).coverUrl, null)
  assert.deepEqual(bilibiliVideoInfoFromView({ code: 0, data }, bvid).pages, [
    { page: 1, cid: 101, title: 'Video', durationSeconds: 0 }
  ])
  assert.throws(() => bilibiliVideoInfoFromView({ code: -404 }, bvid))
  assert.throws(() => bilibiliVideoInfoFromView({ code: 0, data }, 'not-a-BV'))
  assert.throws(() => bilibiliVideoInfoFromView({ code: 0, data: { title: 'Video' } }, bvid))
})
