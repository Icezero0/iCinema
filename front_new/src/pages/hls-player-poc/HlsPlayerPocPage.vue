<script setup lang="ts">
import RoomPlaybackControls from "@/features/room/components/RoomPlaybackControls.vue";
import HlsPocDebugPanel from "./HlsPocDebugPanel.vue";
import { useHlsPlayerPocController } from "./useHlsPlayerPocController";

const {
  POC_ROOM_ID,
  videoRef,
  sourceUrl,
  syncGateState,
  playerState,
  mediaHealthState,
  realtimeStatus,
  realtimeActive,
  errorMessage,
  currentTime,
  duration,
  bufferedRanges,
  seekableRanges,
  canSeek,
  seekRestrictionMessage,
  sourceType,
  engineKind,
  volume,
  logText,
  timelineLabel,
  progressPercent,
  bufferedProgressPercent,
  bufferedRangePercents,
  bufferAhead,
  unlockSyncGate,
  applySourceFromControls,
  togglePlayback,
  handleProgressChange,
  handleVolumeChange,
  handleVideoEvent,
  handleVideoError,
  handleTimeUpdate,
  handleProgress,
  copyLogs,
  clearLogs,
} = useHlsPlayerPocController();
</script>

<template>
  <main class="pocPage">
    <section class="playerBand">
      <div class="playerFrame">
        <video
          ref="videoRef"
          class="video"
          playsinline
          preload="auto"
          @loadstart="handleVideoEvent('loadstart')"
          @loadedmetadata="handleVideoEvent('loadedmetadata')"
          @durationchange="handleVideoEvent('durationchange')"
          @canplay="handleVideoEvent('canplay')"
          @canplaythrough="handleVideoEvent('canplaythrough')"
          @play="handleVideoEvent('play')"
          @playing="handleVideoEvent('playing')"
          @pause="handleVideoEvent('pause')"
          @waiting="handleVideoEvent('waiting')"
          @stalled="handleVideoEvent('stalled')"
          @seeking="handleVideoEvent('seeking')"
          @seeked="handleVideoEvent('seeked')"
          @ended="handleVideoEvent('ended')"
          @timeupdate="handleTimeUpdate"
          @progress="handleProgress"
          @error="handleVideoError"
        />

        <button
          v-if="syncGateState === 'locked'"
          class="syncGateOverlay"
          type="button"
          @click="unlockSyncGate"
        >
          <span class="syncGateTitle">点击以开始同步</span>
        </button>
      </div>
    </section>

    <section class="workspace">
      <RoomPlaybackControls
        class="pocPlaybackControls"
        :is-playing="playerState === 'playing'"
        :progress="progressPercent"
        :buffered-progress="bufferedProgressPercent"
        :buffered-ranges="bufferedRangePercents"
        :volume="volume"
        :seek-disabled="!canSeek"
        source-type="external_url"
        :source-url="sourceUrl"
        source-file-name=""
        :current-time="currentTime"
        :duration="duration"
        :timeline-label="timelineLabel"
        play-label="播放"
        pause-label="暂停"
        sync-label="同步"
        source-label="片源"
        source-panel-title="片源"
        volume-label="音量"
        @toggle-play="togglePlayback"
        @update:progress="handleProgressChange"
        @update:volume="handleVolumeChange"
        @apply-source="applySourceFromControls"
      />

      <HlsPocDebugPanel
        :room-id="POC_ROOM_ID"
        :realtime-status="realtimeStatus"
        :realtime-active="realtimeActive"
        :sync-gate-state="syncGateState"
        :player-state="playerState"
        :media-health-state="mediaHealthState"
        :timeline-label="timelineLabel"
        :buffer-ahead="bufferAhead"
        :buffered-ranges="bufferedRanges"
        :seekable-ranges="seekableRanges"
        :can-seek="canSeek"
        :source-type="sourceType"
        :engine-kind="engineKind"
        :error-message="errorMessage"
        :seek-restriction-message="seekRestrictionMessage"
        :log-text="logText"
        @copy-logs="copyLogs"
        @clear-logs="clearLogs"
      />
    </section>
  </main>
</template>

<style scoped>
.pocPage {
  min-height: 100dvh;
  display: grid;
  grid-template-rows: minmax(320px, 58dvh) minmax(0, 1fr);
  background: var(--c-bg);
  color: var(--c-text);
}

.playerBand {
  min-height: 0;
  padding: 18px;
  background: #05070a;
}

.playerFrame {
  height: 100%;
  display: grid;
  place-items: center;
  background: #000;
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.syncGateOverlay {
  position: absolute;
  inset: 0;
  border: 0;
  background: rgb(3 7 12 / 0.72);
  color: rgb(245 248 252 / 0.96);
  display: grid;
  place-items: center;
  cursor: pointer;
}

.syncGateOverlay:hover {
  background: rgb(3 7 12 / 0.64);
}

.syncGateTitle {
  padding: 14px 20px;
  border: 1px solid rgb(255 255 255 / 0.18);
  border-radius: 8px;
  background: rgb(255 255 255 / 0.08);
  font-size: 18px;
  font-weight: 700;
  box-shadow: 0 18px 42px rgb(0 0 0 / 0.3);
}

.workspace {
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto auto auto minmax(0, 1fr);
  gap: 12px;
  padding: 16px 18px 18px;
  background: var(--c-surface);
  border-top: 1px solid var(--c-border);
}

@media (max-width: 720px) {
  .pocPage {
    grid-template-rows: minmax(220px, 42dvh) minmax(0, 1fr);
  }

  .playerBand,
  .workspace {
    padding: 10px;
  }

}
</style>
