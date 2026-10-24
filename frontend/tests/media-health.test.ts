import assert from 'node:assert/strict';
import { test, type TestContext } from 'node:test';
import { createRenderer, markRaw } from 'vue';
import { useNativeVideoCore, type NativeVideoCore } from '../src/features/room/video/useNativeVideoCore';
import { ROOM_PLAYER_CONFIG } from '../src/features/room/video/playerConfig';
import type { BufferedRange } from '../src/features/room/video/types';
import type { MediaEngineKind } from '../src/features/room/video/mediaEngineTypes';

async function playerFixture(t: TestContext, kind: MediaEngineKind = 'hls') {
  t.mock.timers.enable({ apis: ['Date', 'setTimeout'], now: 1000 });
  const previousWindow = globalThis.window;
  const previousMediaElement = globalThis.HTMLMediaElement;
  globalThis.window = { ...previousWindow, setTimeout, clearTimeout } as any;
  globalThis.HTMLMediaElement = { HAVE_METADATA: 1, HAVE_CURRENT_DATA: 2, HAVE_FUTURE_DATA: 3 } as any;
  let buffered: BufferedRange[] = [];
  const video = markRaw({
    currentTime: 0, duration: 1430.593, readyState: 1, networkState: 2,
    paused: true, ended: false, seeking: false, error: null as { code: number; message: string } | null,
    volume: 1, playbackRate: 1, src: '',
    buffered: { get length() { return buffered.length; }, start: (i: number) => buffered[i]!.start, end: (i: number) => buffered[i]!.end },
    seekable: { length: 1, start: () => 0, end: () => 1430.593 },
    load() {}, pause() { this.paused = true; }, async play() { this.paused = false; },
    removeAttribute() { this.src = ''; },
  });
  let core!: NativeVideoCore;
  const renderer = createRenderer<any, any>({
    patchProp() {}, insert() {}, remove() {}, createElement: () => ({}),
    createText: () => ({}), createComment: () => ({}), setText() {}, setElementText() {},
    parentNode: () => null, nextSibling: () => null,
  });
  const app = renderer.createApp({
    setup() { core = useNativeVideoCore({ writeLog() {}, config: { ...ROOM_PLAYER_CONFIG, readyConfirmDelayMs: 10 } }); return () => null; },
  });
  app.mount({});
  core.videoRef.value = video as unknown as HTMLVideoElement;
  t.after(() => {
    app.unmount();
    globalThis.window = previousWindow;
    globalThis.HTMLMediaElement = previousMediaElement;
  });
  await core.loadSource('https://media.example/test', null, kind, { attachMediaSource: false });
  return { core, video, setBuffer: (ranges: BufferedRange[]) => { buffered = ranges; } };
}

test('paused HLS with a 166ms initial timestamp offset becomes ready without pressing play', async t => {
  const { core, video, setBuffer } = await playerFixture(t);
  setBuffer([{ start: 0.166, end: 40 }]);
  video.readyState = 4;
  core.handleBufferAppended('hls:bufferAppended');
  t.mock.timers.tick(10);
  assert.equal(video.currentTime, 0.166);
  assert.equal(video.paused, true);
  assert.equal(core.mediaHealthState.value, 'ready');
  assert.equal(core.bufferAhead.value, 39.834);
  t.mock.timers.tick(60000);
  assert.equal(core.mediaHealthState.value, 'ready');
  assert.equal(core.errorMessage.value, '');
  // A room paused at zero or the user dragging to the beginning must stay in playable data.
  await core.applyPlayback({ status: 'paused', position_seconds: 0, playback_rate: 1 }, { syncPosition: true });
  assert.equal(video.currentTime, 0.166);
  assert.equal(core.seekToPercent(0), 0.166);
});

test('a network stalled event with playable HLS or MP4 buffer does not block the room', async t => {
  for (const kind of ['hls', 'direct_video'] as const) {
    await t.test(kind, async sub => {
      const { core, video, setBuffer } = await playerFixture(sub, kind);
      video.readyState = 4;
      setBuffer([{ start: 0, end: 40 }]);
      core.handleVideoEvent('canplay');
      sub.mock.timers.tick(10);
      assert.equal(core.mediaHealthState.value, 'ready');
      core.handleVideoEvent('stalled');
      assert.equal(core.mediaHealthState.value, 'ready');
      sub.mock.timers.tick(60000);
      assert.equal(core.mediaHealthState.value, 'ready');
    });
  }
});

test('timeout rechecks playable buffer even if the browser omitted progress and canplay events', async t => {
  const { core, video, setBuffer } = await playerFixture(t, 'direct_video');
  video.readyState = 4;
  setBuffer([{ start: 0, end: 40 }]);
  // First timeout sees newly downloaded data, second one sees a buffer that stopped growing.
  t.mock.timers.tick(30000);
  t.mock.timers.tick(30000);
  t.mock.timers.tick(10);
  assert.equal(core.mediaHealthState.value, 'ready');
  assert.equal(core.errorMessage.value, '');
});

test('late buffer can recover from an application timeout but not a fatal decoder error', async t => {
  const { core, video, setBuffer } = await playerFixture(t);
  t.mock.timers.tick(30000);
  assert.equal(core.mediaHealthState.value, 'error');
  video.readyState = 4;
  setBuffer([{ start: 0, end: 40 }]);
  core.handleBufferAppended('lateBuffer');
  t.mock.timers.tick(10);
  assert.equal(core.mediaHealthState.value, 'ready');
  assert.equal(core.errorMessage.value, '');
  video.error = { code: 3, message: 'decode error' };
  core.handleVideoError();
  core.handleProgress();
  t.mock.timers.tick(10);
  assert.equal(core.mediaHealthState.value, 'error');
  assert.equal(core.errorMessage.value, 'decode error');
});

test('large gaps, missing data at a seek target and undecodable buffers still wait', async t => {
  const { core, video, setBuffer } = await playerFixture(t);
  video.readyState = 4;
  setBuffer([{ start: 5, end: 45 }]);
  core.handleBufferAppended('largeGap');
  t.mock.timers.tick(10);
  assert.equal(video.currentTime, 0);
  assert.equal(core.mediaHealthState.value, 'stalling');
  video.currentTime = 60;
  setBuffer([{ start: 60.166, end: 100 }]);
  core.handleProgress();
  t.mock.timers.tick(10);
  assert.equal(video.currentTime, 60);
  assert.equal(core.mediaHealthState.value, 'stalling');
  video.currentTime = 70;
  video.readyState = 2;
  core.handleVideoEvent('waiting');
  t.mock.timers.tick(10);
  assert.equal(core.mediaHealthState.value, 'stalling');
});

test('normal MP4 and Bilibili DASH time zero is not changed by HLS startup alignment', async t => {
  for (const kind of ['direct_video', 'bilibili_dash'] as const) {
    await t.test(kind, async sub => {
      const { core, video, setBuffer } = await playerFixture(sub, kind);
      video.readyState = 4;
      setBuffer([{ start: 0.166, end: 40 }]);
      core.handleProgress();
      assert.equal(video.currentTime, 0);
      setBuffer([{ start: 0, end: 40 }]);
      core.handleProgress();
      sub.mock.timers.tick(10);
      assert.equal(core.mediaHealthState.value, 'ready');
    });
  }
});
