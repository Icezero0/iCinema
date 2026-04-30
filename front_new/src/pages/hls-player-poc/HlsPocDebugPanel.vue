<script setup lang="ts">
import type {
  BufferedRange,
  MediaHealthState,
  PlayerState,
  SyncGateState,
} from "./types";

defineProps<{
  roomId: number;
  realtimeStatus: string;
  realtimeActive: boolean;
  syncGateState: SyncGateState;
  playerState: PlayerState;
  mediaHealthState: MediaHealthState;
  timelineLabel: string;
  bufferAhead: number;
  bufferedRanges: BufferedRange[];
  errorMessage: string;
  logText: string;
}>();

const emit = defineEmits<{
  copyLogs: [];
  clearLogs: [];
}>();
</script>

<template>
  <div class="statusGrid">
    <div>
      <span class="label">房间</span>
      <strong>#{{ roomId }}</strong>
    </div>
    <div>
      <span class="label">WS</span>
      <strong>{{ realtimeStatus }} / {{ realtimeActive ? "entered" : "idle" }}</strong>
    </div>
    <div>
      <span class="label">同步门禁</span>
      <strong>{{ syncGateState }}</strong>
    </div>
    <div>
      <span class="label">播放状态</span>
      <strong>{{ playerState }}</strong>
    </div>
    <div>
      <span class="label">媒体健康</span>
      <strong>{{ mediaHealthState }}</strong>
    </div>
    <div>
      <span class="label">时间</span>
      <strong>{{ timelineLabel }}</strong>
    </div>
    <div>
      <span class="label">前向缓冲</span>
      <strong>{{ bufferAhead.toFixed(2) }}s</strong>
    </div>
    <div>
      <span class="label">缓冲段</span>
      <strong>{{ bufferedRanges.length }}</strong>
    </div>
  </div>

  <p v-if="errorMessage" class="errorText">{{ errorMessage }}</p>

  <div class="logHeader">
    <span>调试输出</span>
    <div class="logActions">
      <button class="ghostBtn" type="button" @click="emit('copyLogs')">复制</button>
      <button class="ghostBtn" type="button" @click="emit('clearLogs')">清空</button>
    </div>
  </div>

  <textarea
    class="logOutput"
    readonly
    spellcheck="false"
    :value="logText"
    placeholder="日志会显示在这里"
  />
</template>

<style scoped>
.statusGrid {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 10px;
}

.statusGrid > div {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  background: var(--c-bg);
  display: grid;
  gap: 4px;
}

.label {
  font-size: 12px;
  color: var(--c-text-muted);
}

.statusGrid strong {
  min-width: 0;
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
}

.errorText {
  margin: 0;
  color: var(--c-danger);
  font-size: 13px;
}

.logHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  font-weight: 600;
}

.logActions {
  display: inline-flex;
  gap: 8px;
}

.ghostBtn {
  height: 32px;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  background: var(--c-bg);
  color: var(--c-text);
  padding: 0 12px;
  cursor: pointer;
}

.logOutput {
  width: 100%;
  height: 100%;
  min-height: 0;
  resize: none;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--c-bg) 94%, black);
  color: var(--c-text);
  padding: 12px;
  font-family: Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  line-height: 1.5;
  outline: none;
}

@media (max-width: 720px) {
  .statusGrid {
    grid-template-columns: 1fr;
  }
}
</style>
