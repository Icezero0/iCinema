import assert from 'node:assert/strict';
import { test } from 'node:test';
import axios from 'axios';
import { computed, createApp, ref } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import en from '../src/infra/i18n/locales/en';
import zhCN from '../src/infra/i18n/locales/zh-CN';
import { toMediaEngineLoadInput } from '../src/features/room/video/mediaEngineTypes';

test('catalog translations have matching keys and change with the selected language', () => {
  function keys(value: Record<string, unknown>, prefix = ''): string[] {
    return Object.entries(value).flatMap(([key, entry]) => typeof entry === 'string'
      ? [prefix + key] : keys(entry as Record<string, unknown>, prefix + key + '.')).sort();
  }
  assert.deepEqual(keys(en.catalogAdmin), keys(zhCN.catalogAdmin));
  assert.deepEqual(keys(en.catalogDetail), keys(zhCN.catalogDetail));
  assert.deepEqual(keys(en.catalogImport), keys(zhCN.catalogImport));
  assert.deepEqual(keys(en.omofun), keys(zhCN.omofun));
  assert.ok(!keys(en.catalogDetail).includes('fields.season'));
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en, 'zh-CN': zhCN } });
  assert.equal(i18n.global.t('catalogAdmin.title'), 'Video resources');
  assert.equal(i18n.global.t('catalogAdmin.editTitle', { id: 7 }), 'Edit resource #7');
  assert.equal(i18n.global.t('catalogDetail.lineCount', { count: 2, total: 3 }), '2 enabled direct-play lines / 3 configured lines');
  assert.equal(i18n.global.t('catalogDetail.episodeLabel', { kind: 'Episode', number: 1, title: 'Test' }), 'Episode 1 · Test');
  i18n.global.locale.value = 'zh-CN';
  assert.equal(i18n.global.t('catalogAdmin.title'), '视频资源管理');
  assert.equal(i18n.global.t('catalogDetail.lineCount', { count: 2, total: 3 }), '可直接预览 2 条 / 已配置 3 条线路');
  assert.equal(i18n.global.t('catalogDetail.manualSource'), '手动录入');
  for (const key of keys(en.catalogAdmin)) assert.ok(i18n.global.te('catalogAdmin.' + key));
  for (const key of keys(en.catalogDetail)) assert.ok(i18n.global.te('catalogDetail.' + key));
  for (const key of keys(en.catalogImport)) assert.ok(i18n.global.te('catalogImport.' + key));
});

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
const { useRoomsStore } = await import('../src/stores/rooms.store');
const { useMessagesStore } = await import('../src/stores/messages.store');
const { http } = await import('../src/infra/http/client');
const { useRoomJoinRequests } = await import('../src/features/room/composables/useRoomJoinRequests');

test('room invitation already approved by the room cannot be reviewed again', async () => {
  setActivePinia(createPinia());
  const original = http.defaults.adapter;
  let calls = 0;
  http.defaults.adapter = async () => { calls++; throw new Error('Unexpected review'); };
  try {
    const permitted = ref(true);
    const requests = useRoomJoinRequests({ roomId: computed(() => 1),
      canManageRoomRequests: computed(() => permitted.value), optimisticInviteUserIds: ref([]), t: key => key });
    const request = { id: 1, room_id: 1, initiator_user_id: 1, target_user_id: 2,
      source: 'invite', status: 'pending', room_action: 'approved', target_action: 'pending',
      created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' } as any;
    requests.roomJoinRequests.value = [request];
    assert.deepEqual(requests.roomRequestItems.value, []);
    assert.deepEqual(requests.pendingMemberInviteStates.value, [{ userId: 2, source: 'invite' }]);
    await requests.approveRequest(1);
    await requests.rejectRequest(1);
    assert.equal(calls, 0);
    requests.roomJoinRequests.value = [{ ...request, source: 'apply', room_action: 'pending', target_action: 'approved' }];
    assert.equal(requests.roomRequestItems.value[0]?.canReview, true);
    permitted.value = false;
    assert.deepEqual(requests.roomRequestItems.value, []);
    permitted.value = true;
    requests.roomJoinRequests.value = [{ ...request, status: 'cancelled', room_action: 'pending' }];
    assert.deepEqual(requests.roomRequestItems.value, []);
  } finally { http.defaults.adapter = original; setActivePinia(pinia); }
});

test('home includes joined rooms without depending on the public directory', async () => {
  setActivePinia(createPinia());
  const original = http.defaults.adapter;
  const requests: string[] = [];
  http.defaults.adapter = async config => {
    requests.push(config.url!);
    if (config.url !== '/users/me/rooms') throw new Error('Public directory unavailable');
    assert.equal(config.params.role, undefined);
    return { config, status: 200, statusText: 'OK', headers: {}, data: {
      items: [
        { id: 1, name: 'Owned', owner_id: 1, owner: { id: 1, username: 'Me' }, my_role: 'owner', is_public: false },
        { id: 2, name: 'Joined', owner_id: 2, owner: { id: 2, username: 'Other' }, my_role: 'member', is_public: true },
      ], total: 2, page: 1, page_size: 100, total_pages: 1,
    } };
  };
  try {
    const rooms = useRoomsStore();
    await rooms.fetchHomeRooms();
    assert.deepEqual(rooms.myRooms.map(room => [room.id, room.my_role]), [[1, 'owner'], [2, 'member']]);
    assert.equal(rooms.error, null);
    assert.deepEqual(requests, ['/users/me/rooms']);
  } finally { http.defaults.adapter = original; setActivePinia(pinia); }
});

test('historical messages do not imply that their sender is currently online', () => {
  setActivePinia(createPinia());
  try {
    const messages = useMessagesStore();
    messages.appendRealtimeMessage({ id: 1, room_id: 1, sender_user_id: 2,
      sender: { id: 2, username: 'Offline sender', email: 'offline@example.invalid', auto_accept: false, avatar_url: null },
      content: { segments: [{ type: 'text', text: 'Old message' }] }, created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });
    assert.equal(messages.getRoomChatMessages(1)[0]?.status, 'offline');
  } finally { setActivePinia(pinia); }
});
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

test('Omofun room source uses the URL engine while preserving the user-facing mode', () => {
  const playback = useRoomPlaybackState({ roomId: ref(1), playerStageRef: ref(null), t: (key) => key });
  playback.applyRealtimeVideoSource({ room_id: 1, source_type: 'omofun', file_hash: null,
    external_url: 'https://media.example/episode.m3u8?token=1', source_revision: 7,
    omofun: { work_id: '123', episode_id: 'ep1', line_id: 'line', cache_version: 3 } });
  assert.equal(playback.playbackSourceType.value, 'omofun');
  assert.deepEqual(toMediaEngineLoadInput(playback.playbackSourceType.value, playback.playbackSourceUrl.value, null), {
    sourceType: 'external_url', externalUrl: 'https://media.example/episode.m3u8?token=1', localFile: null,
  });
  playback.applyRealtimeVideoSource({ room_id: 1, source_type: 'local_file', file_hash: 'abc', external_url: null });
  assert.equal(playback.playbackSourceUrl.value, '');
  assert.equal(toMediaEngineLoadInput('local_file', '', null), null);
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
