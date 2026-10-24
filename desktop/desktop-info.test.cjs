const test = require('node:test')
const assert = require('node:assert/strict')
const { compareVersions, releaseResult, createUpdateChecker, setupDesktopInfo } = require('./desktop-info.cjs')

test('version checks use numeric ordering and handle current release tags and prereleases', () => {
  assert.equal(compareVersions('v0.1.10', '0.1.9'), 1)
  assert.equal(compareVersions('v1.0.0', '0.9.99'), 1)
  assert.equal(compareVersions('0.1.1+build.2', 'v0.1.1'), 0)
  assert.equal(compareVersions('v0.1.0-desktop-beta', '0.1.0'), -1)
  assert.equal(compareVersions('v0.1.1', '0.1.1-beta.2'), 1)
  assert.equal(compareVersions('v0.1.1-beta.10', '0.1.1-beta.2'), 1)
  assert.equal(compareVersions('v0.1.1-beta', '0.1.1-beta.2'), -1)
  assert.throws(() => compareVersions('latest', '0.1.1'))
  assert.throws(() => compareVersions('0.1.1-beta.01', '0.1.1'))
})

function release(tag = 'v0.1.2') {
  return { tag_name: tag, draft: false, prerelease: false, html_url: 'https://untrusted.example' }
}

test('update results only link to this repository, and older releases are not offered as upgrades', () => {
  const newer = releaseResult(release(), '0.1.1')
  assert.equal(newer.status, 'available')
  assert.equal(newer.latestVersion, '0.1.2')
  assert.equal(newer.releaseUrl, 'https://github.com/Icezero0/iCinema/releases/tag/v0.1.2')
  assert.equal(releaseResult(release('v0.1.0-desktop-beta'), '0.1.1').status, 'current')
  assert.throws(() => releaseResult({ ...release(), prerelease: true }, '0.1.1'))
  assert.throws(() => releaseResult({ ...release(), draft: true }, '0.1.1'))
})

test('concurrent update checks share one request and cache a successful result', async () => {
  let requests = 0
  let now = 1000
  const check = createUpdateChecker(async (url, options) => {
    requests++
    assert.equal(url, 'https://api.github.com/repos/Icezero0/iCinema/releases/latest')
    assert.equal(options.credentials, 'omit')
    assert.equal(options.redirect, 'error')
    return { ok: true, status: 200, json: async () => release() }
  }, '0.1.1', () => now)
  const [a, b] = await Promise.all([check(), check()])
  assert.deepEqual(a, b)
  assert.equal(requests, 1)
  await check()
  assert.equal(requests, 1)
  now += 60001
  await check()
  assert.equal(requests, 2)
})

test('missing releases are distinguished from rate limits and network failures', async () => {
  const missing = createUpdateChecker(async () => ({ status: 404 }), '0.1.1')
  assert.equal((await missing()).status, 'unpublished')
  for (const status of [403, 429, 500]) {
    let requests = 0
    const check = createUpdateChecker(async () => { requests++; return { status, ok: false } }, '0.1.1')
    await assert.rejects(check(), /UPDATE_CHECK_UNAVAILABLE/)
    await assert.rejects(check(), /UPDATE_CHECK_UNAVAILABLE/)
    assert.equal(requests, 1)
  }
  const offline = createUpdateChecker(async () => { throw new Error('offline') }, '0.1.1')
  await assert.rejects(offline(), /UPDATE_CHECK_UNAVAILABLE/)
})

test('timeout aborts a stalled network request', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  let signal
  const check = createUpdateChecker(async (_url, options) => new Promise((_resolve, reject) => {
    signal = options.signal
    signal.addEventListener('abort', () => reject(new Error('aborted')))
  }), '0.1.1')
  const pending = assert.rejects(check(), /UPDATE_CHECK_UNAVAILABLE/)
  t.mock.timers.tick(12000)
  await pending
  assert.equal(signal.aborted, true)
})

test('desktop IPC rejects external pages and subframes and only opens its fixed data folder', async () => {
  const handlers = new Map()
  let opened
  setupDesktopInfo({
    ipcMain: { handle: (name, fn) => handlers.set(name, fn) },
    net: {}, shell: { openPath: async value => { opened = value; return '' } },
    appOrigin: 'icinema://app/', version: '0.1.1', storagePath: 'C:\\Users\\test\\AppData\\Local\\iCinema', mode: 'portable'
  })
  const frame = { url: 'icinema://app/desktop' }
  const event = { senderFrame: frame, sender: { mainFrame: frame } }
  assert.equal(handlers.get('desktop:info')(event).version, '0.1.1')
  await handlers.get('desktop:open-data')(event, 'C:\\untrusted')
  assert.equal(opened, 'C:\\Users\\test\\AppData\\Local\\iCinema')
  frame.url = 'https://untrusted.example'
  assert.throws(() => handlers.get('desktop:info')(event), /INVALID_APP_FRAME/)
  frame.url = 'icinema://app/'
  event.senderFrame = { url: frame.url }
  assert.throws(() => handlers.get('desktop:check-updates')(event), /INVALID_APP_FRAME/)
})
