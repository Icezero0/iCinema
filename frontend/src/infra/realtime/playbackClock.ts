let serverAnchor: number | null = null;
let localAnchor = 0;

export function observeServerTime(serverMs: number, localMs = performance.now()) {
  if (!Number.isFinite(serverMs)) return;
  serverAnchor = serverMs;
  localAnchor = localMs;
}

export function serverNowMs(localMs = performance.now()) {
  return serverAnchor == null ? Date.now() : serverAnchor + Math.max(0, localMs - localAnchor);
}

export function projectedPlaybackPosition(state: {
  status: string; position_seconds: number; anchor_ts_ms: number; playback_rate: number;
}, nowMs = serverNowMs()) {
  const elapsed = state.status === "playing" ? Math.max(0, nowMs - state.anchor_ts_ms) / 1000 : 0;
  return Math.max(0, state.position_seconds + elapsed * state.playback_rate);
}
