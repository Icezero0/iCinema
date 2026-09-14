import assert from 'node:assert/strict';
import { test } from 'node:test';
import axios from 'axios';
import { createApp, ref } from 'vue';
import { createPinia, setActivePinia } from 'pinia';

const storage: Record<string, any> = {};
Object.defineProperties(storage, {
  getItem: { value: (key: string) => storage[key] ?? null },
  setItem: { value: (key: string, value: string) => { storage[key] = value; } },
  removeItem: { value: (key: string) => { delete storage[key]; } },
});
globalThis.localStorage = storage as Storage;
const redirects: string[] = [];
const browserEvents = new EventTarget();
let reloads = 0;
globalThis.window = {
  addEventListener: browserEvents.addEventListener.bind(browserEvents),
  setTimeout, clearTimeout, setInterval, clearInterval,
  location: { origin: 'http://localhost:5173', hostname: 'localhost', host: 'localhost:5173', port: '5173', protocol: 'http:',
    pathname: '/rooms/1', search: '', hash: '', assign: (url: string) => redirects.push(url), reload: () => { reloads++; } },
} as any;
let rejectOldToken = false;
const sockets: FakeSocket[] = [];
class FakeSocket extends EventTarget {
  static OPEN = 1;
  readyState = 0;
  constructor(_url: string) {
    super(); sockets.push(this);
    queueMicrotask(() => { this.readyState = 1; this.dispatchEvent(new Event('open')); });
  }
  send(raw: string) {
    const message = JSON.parse(raw);
    const unauthorized = message.type === 'auth' && rejectOldToken && message.payload.token === 'old';
    const response = message.type === 'heartbeat'
      ? { type: 'heartbeat', payload: { action: 'pong' } }
      : unauthorized ? { type: 'error', payload: { code: 'unauthorized', message: 'expired', reason: 'invalid_token' } }
      : { type: 'ack', payload: {} };
    queueMicrotask(() => this.dispatchEvent(new MessageEvent('message', { data: JSON.stringify({ v: 1, server_ts_ms: Date.now(), ...response }) })));
  }
  close() {
    this.readyState = 3;
    queueMicrotask(() => this.dispatchEvent(new Event('close')));
  }
}
globalThis.WebSocket = FakeSocket as any;

const session = await import('../src/infra/auth/session');
const { default: ws } = await import('../src/infra/realtime/wsClient');
const clock = await import('../src/infra/realtime/playbackClock');
const { resetStoresOnSessionChange } = await import('../src/infra/auth/sessionPinia');
const { useStickersStore } = await import('../src/stores/stickers.store');
const { useAuthStore } = await import('../src/stores/auth.store');
const { useRoomPlaybackState } = await import('../src/features/room/composables/useRoomPlaybackState');
const pinia = createPinia();
pinia.use(resetStoresOnSessionChange);
createApp({}).use(pinia);
setActivePinia(pinia);

test('account changes in another tab clear caches, invalidate requests and reload identity', async () => {
  const stickers = useStickersStore();
  stickers.libraryIds = [42];
  await ws.connect('account-a');
  const oldSocket = sockets.at(-1)!;
  storage.setItem('icinema:stickers-store', 'old-account');
  const previousGeneration = session.sessionGeneration();
  const event = new Event('storage');
  Object.assign(event, { key: 'icinema:session-change', storageArea: storage });
  browserEvents.dispatchEvent(event);
  assert.equal(storage.getItem('icinema:stickers-store'), null);
  assert.deepEqual(stickers.libraryIds, []);
  assert.equal(oldSocket.readyState, 3);
  assert.equal(session.sessionGeneration(), previousGeneration + 1);
  assert.equal(reloads, 1);
  const tokenEvent = new Event('storage');
  Object.assign(tokenEvent, { key: 'access_token', storageArea: storage });
  browserEvents.dispatchEvent(tokenEvent);
  assert.equal(reloads, 1, 'routine token refresh does not reload other tabs');
});

test('playing snapshots project elapsed server time and rate; paused states stay fixed', () => {
  const state = { status: 'playing', position_seconds: 10, anchor_ts_ms: 1000, playback_rate: 2 };
  clock.observeServerTime(601000, 100);
  assert.equal(clock.projectedPlaybackPosition(state, clock.serverNowMs(100)), 1210);
  assert.equal(clock.projectedPlaybackPosition(state, clock.serverNowMs(2100)), 1214);
  assert.equal(clock.projectedPlaybackPosition({ ...state, status: 'paused' }, clock.serverNowMs(2100)), 10);
});

test('deferred player application includes time spent loading', async () => {
  const seeks: number[] = [];
  const rates: number[] = [];
  const player = ref({ seekToSeconds: async (n: number) => { seeks.push(n); },
    playVideo: async () => {}, pauseVideo() {}, togglePlayback: async () => {}, seekToPercent() {},
    captureCurrentFrame: async () => new Blob(), setPlaybackRate: (n: number) => rates.push(n) });
  const playback = useRoomPlaybackState({ roomId: ref(1), playerStageRef: player, t: (key) => key });
  clock.observeServerTime(601000);
  await playback.applyRealtimePlaybackState({ room_id: 1, status: 'playing', position_seconds: 0, anchor_ts_ms: 1000, playback_rate: 1 }, { syncPosition: true });
  assert.equal(seeks.length, 0);
  clock.observeServerTime(606000);
  playback.handlePlaybackDurationChange(1000);
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.ok(seeks[0]! >= 605 && seeks[0]! < 606);
  assert.equal(rates[0], 1);
});

test('HTTP and WS refresh callers share one request', async () => {
  storage.setItem('refresh_token', 'refresh');
  let calls = 0;
  const original = axios.post;
  axios.post = (async () => { calls++; await Promise.resolve(); return { data: { access_token: 'new', refresh_token: 'next' } }; }) as any;
  try {
    assert.deepEqual(await Promise.all([session.refreshAccessTokenOnce(), session.refreshAccessTokenOnce()]), ['new', 'new']);
    assert.equal(calls, 1);
  } finally { axios.post = original; }
});

test('refresh completion after logout cannot restore a previous account', async () => {
  storage.setItem('refresh_token', 'old-refresh');
  let resolve!: (value: any) => void;
  const original = axios.post;
  axios.post = (() => new Promise(r => { resolve = r; })) as any;
  try {
    const pending = session.refreshAccessTokenOnce();
    session.resetSessionData();
    storage.setItem('access_token', 'other-account');
    storage.setItem('refresh_token', 'other-refresh');
    resolve({ data: { access_token: 'old-account', refresh_token: 'old-next' } });
    await assert.rejects(pending, /Session changed/);
    assert.equal(storage.getItem('access_token'), 'other-account');
  } finally { axios.post = original; }
});

test('logout clears persisted and in-memory collections before another login', () => {
  const stickers = useStickersStore();
  stickers.libraryIds = [42];
  storage.setItem('icinema:stickers-store', JSON.stringify({ libraryIds: [42], stickersById: {}, recentStickerIds: [] }));
  useAuthStore().logout();
  assert.deepEqual(stickers.libraryIds, []);
  assert.equal(storage.getItem('icinema:stickers-store'), null);
});

test('expired access token refreshes after a network reconnect', async () => {
  redirects.length = 0;
  storage.setItem('access_token', 'old'); storage.setItem('refresh_token', 'refresh');
  const original = axios.post;
  let refreshed = 0;
  axios.post = (async () => { refreshed++; return { data: { access_token: 'new', refresh_token: 'next' } }; }) as any;
  try {
    rejectOldToken = false;
    await ws.connect('old');
    assert.equal(ws.connectionStatus, 'ready');
    rejectOldToken = true;
    sockets.at(-1)!.close();
    const deadline = Date.now() + 5000;
    while ((!refreshed || ws.connectionStatus !== 'ready') && Date.now() < deadline) await new Promise(r => setTimeout(r, 20));
    assert.equal(refreshed, 1);
    assert.equal(ws.connectionStatus, 'ready');
    assert.equal(redirects.length, 0);
  } finally { ws.disconnect(); axios.post = original; }
});
