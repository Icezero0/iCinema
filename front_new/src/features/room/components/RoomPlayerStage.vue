<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, toRef } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowsPointingInIcon,
  ArrowsPointingOutIcon,
  ExclamationTriangleIcon,
  FilmIcon,
  PauseCircleIcon,
  RectangleGroupIcon,
} from "@heroicons/vue/24/outline";
import AppIcon from "@/ui/base/AppIcon.vue";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";
import { useRoomVideoPlayer } from "@/features/room/composables/useRoomVideoPlayer";

const { t } = useI18n();

const props = defineProps<{
  title: string;
  hint: string;
  sourceType: RoomVideoSourceType;
  sourceUrl: string;
  sourceFile: File | null;
  sourceRevision: number;
  volume: number;
  videoFullscreenLabel: string;
  exitVideoFullscreenLabel: string;
  theaterModeLabel: string;
  exitTheaterModeLabel: string;
  isTheaterMode?: boolean;
  theaterModeAvailable?: boolean;
}>();

const emit = defineEmits<{
  (e: "toggle-theater-mode"): void;
  (e: "play-state-change", value: boolean): void;
  (e: "player-status-change", value: "idle" | "ready" | "stalling" | "error"): void;
  (e: "duration-change", value: number): void;
  (e: "time-change", value: number): void;
  (e: "buffered-progress-change", value: number): void;
  (e: "buffered-ranges-change", value: Array<{ startPercent: number; endPercent: number }>): void;
  (e: "waiting-change", value: boolean): void;
  (e: "error", value: string): void;
}>();

const shellRef = ref<HTMLElement | null>(null);
const isVideoFullscreen = ref(false);
const controlsVisible = ref(false);
const pointerIdle = ref(false);
let controlsHideTimer = 0;
const shouldAutoHideActions = computed(() =>
  isVideoFullscreen.value || Boolean(props.isTheaterMode));

const player = useRoomVideoPlayer({
  sourceType: toRef(props, "sourceType"),
  sourceUrl: toRef(props, "sourceUrl"),
  sourceFile: toRef(props, "sourceFile"),
  sourceRevision: toRef(props, "sourceRevision"),
  volume: toRef(props, "volume"),
  messages: {
    hlsLoadFailed: t("room.playback.errors.hlsLoadFailed"),
    hlsUnsupported: t("room.playback.errors.hlsUnsupported"),
    sourceLoadFailed: t("room.playback.errors.sourceLoadFailed"),
    playFailed: t("room.playback.errors.playFailed"),
    playFailedWithSource: t("room.playback.errors.playFailedWithSource"),
    screenshotNoFrame: t("room.playback.screenshotNoFrame"),
    screenshotFailed: t("room.playback.screenshotFailed"),
  },
  emit: {
    playStateChange: (value) => emit("play-state-change", value),
    statusChange: (value) => emit("player-status-change", value),
    durationChange: (value) => emit("duration-change", value),
    timeChange: (value) => emit("time-change", value),
    bufferedProgressChange: (value) => emit("buffered-progress-change", value),
    bufferedRangesChange: (value) => emit("buffered-ranges-change", value),
    waitingChange: (value) => emit("waiting-change", value),
    error: (value) => emit("error", value),
  },
});

const videoRef = player.videoRef;
const showEmptyState = computed(() => !player.hasSource.value);
const showWaitingState = computed(() =>
  player.hasSource.value && player.playerStatus.value === "stalling");
const showPausedState = computed(() =>
  player.hasSource.value &&
  player.hasLoadedMetadata.value &&
  player.playerStatus.value === "ready" &&
  !player.isPlaying.value &&
  !player.playerError.value);

function setVideoRef(el: unknown) {
  videoRef.value = el instanceof HTMLVideoElement ? el : null;
}

function showPlayerActions() {
  controlsVisible.value = true;
  pointerIdle.value = false;

  if (controlsHideTimer) {
    window.clearTimeout(controlsHideTimer);
  }

  if (shouldAutoHideActions.value) {
    controlsHideTimer = window.setTimeout(() => {
      controlsVisible.value = false;
      pointerIdle.value = true;
      controlsHideTimer = 0;
    }, 1800);
  }
}

function hidePlayerActions(event?: PointerEvent) {
  if (event?.pointerType === "touch") return;

  if (controlsHideTimer) {
    window.clearTimeout(controlsHideTimer);
    controlsHideTimer = 0;
  }
  controlsVisible.value = false;
  pointerIdle.value = false;
}

function hidePlayerActionsFromOutside(event: PointerEvent) {
  if (event.pointerType !== "touch" || !controlsVisible.value) return;
  const target = event.target as Node | null;
  if (!target || shellRef.value?.contains(target)) return;
  hidePlayerActions();
}

function syncFullscreenState() {
  isVideoFullscreen.value = document.fullscreenElement === shellRef.value;
  if (!isVideoFullscreen.value) {
    void (screen.orientation as any)?.unlock?.();
  }
}

async function toggleVideoFullscreen() {
  if (isVideoFullscreen.value) {
    await document.exitFullscreen?.();
    return;
  }

  await shellRef.value?.requestFullscreen?.();
  try {
    await (screen.orientation as any)?.lock?.("landscape");
  } catch {
    // Orientation lock is not available or not allowed in every browser.
  }
}

onMounted(() => {
  document.addEventListener("fullscreenchange", syncFullscreenState);
  document.addEventListener("pointerdown", hidePlayerActionsFromOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", syncFullscreenState);
  document.removeEventListener("pointerdown", hidePlayerActionsFromOutside);
  if (controlsHideTimer) {
    window.clearTimeout(controlsHideTimer);
  }
});

defineExpose({
  playVideo: player.playVideo,
  pauseVideo: player.pauseVideo,
  togglePlayback: player.togglePlayback,
  seekToPercent: player.seekToPercent,
  seekToSeconds: player.seekToSeconds,
  captureCurrentFrame: player.captureCurrentFrame,
});
</script>

<template>
  <div
    ref="shellRef"
    class="playerShell"
    :class="{ pointerIdle }"
    role="presentation"
    @pointerenter="showPlayerActions"
    @pointermove="showPlayerActions"
    @pointerdown="showPlayerActions"
    @pointerleave="hidePlayerActions"
  >
    <div class="playerSurface">
      <video
        v-show="player.hasSource.value && player.playerStatus.value !== 'error'"
        :ref="setVideoRef"
        class="playerVideo"
        playsinline
        preload="auto"
        @loadedmetadata="player.handleLoadedMetadata"
        @durationchange="player.handleDurationChange"
        @timeupdate="player.handleTimeUpdate"
        @play="player.handlePlay"
        @pause="player.handlePause"
        @waiting="player.handleWaiting"
        @stalled="player.handleWaiting"
        @canplay="player.handleCanPlay"
        @playing="player.handleCanPlay"
        @progress="player.handleProgress"
        @seeking="player.handleSeeking"
        @seeked="player.handleSeeked"
        @ended="player.handleEnded"
        @error="player.handleVideoError"
      />

      <div v-if="showEmptyState" class="playerEmptyState">
        <div class="emptyIcon">
          <AppIcon :icon="FilmIcon" :size="28" />
        </div>
        <div class="emptyText">
          <div class="emptyTitle">{{ title }}</div>
          <div class="emptyHint">{{ hint }}</div>
        </div>
      </div>
      <div v-else-if="player.playerStatus.value === 'error'" class="playerOverlay playerOverlayError">
        <div class="overlayIcon">
          <AppIcon :icon="ExclamationTriangleIcon" :size="30" />
        </div>
        <div class="overlayText">{{ player.playerError.value }}</div>
      </div>
      <div v-else-if="showWaitingState" class="playerOverlay">
        <div class="loadingSpinner" aria-hidden="true" />
      </div>
      <div v-else-if="showPausedState" class="playerOverlay pausedOverlay">
        <div class="overlayIcon">
          <AppIcon :icon="PauseCircleIcon" :size="44" />
        </div>
      </div>

      <div class="playerQuickActions" :class="{ visible: controlsVisible }">
        <button
          v-if="!isTheaterMode"
          class="playerActionBtn"
          type="button"
          :aria-label="isVideoFullscreen ? exitVideoFullscreenLabel : videoFullscreenLabel"
          :title="isVideoFullscreen ? exitVideoFullscreenLabel : videoFullscreenLabel"
          @click="toggleVideoFullscreen"
        >
          <AppIcon :icon="isVideoFullscreen ? ArrowsPointingInIcon : ArrowsPointingOutIcon" :size="18" />
        </button>
        <button
          v-if="!isVideoFullscreen && (isTheaterMode || theaterModeAvailable)"
          class="playerActionBtn"
          type="button"
          :aria-label="isTheaterMode ? exitTheaterModeLabel : theaterModeLabel"
          :title="isTheaterMode ? exitTheaterModeLabel : theaterModeLabel"
          @click="emit('toggle-theater-mode')"
        >
          <AppIcon
            :icon="isTheaterMode ? ArrowsPointingInIcon : RectangleGroupIcon"
            :size="18"
          />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.playerShell {
  width: 100%;
  border-radius: 22px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 16%, var(--c-border));
  background:
    linear-gradient(145deg, rgb(17 23 31), rgb(37 50 68)),
    radial-gradient(circle at top left, rgb(255 255 255 / 0.06), transparent 30%);
  box-shadow: 0 20px 60px rgb(0 0 0 / 0.18);
}

.playerShell.pointerIdle {
  cursor: none;
}

.playerShell:fullscreen {
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 0;
  background: #05070a;
  box-shadow: none;
}

.playerSurface {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  display: grid;
  place-items: center;
  border-radius: inherit;
  overflow: hidden;
}

.playerShell:fullscreen .playerSurface {
  height: 100%;
  aspect-ratio: auto;
  border-radius: 0;
}

.playerVideo {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #05070a;
  border-radius: inherit;
}

.playerShell:fullscreen .playerVideo {
  border-radius: 0;
}

.playerEmptyState {
  width: min(360px, calc(100% - 48px));
  display: grid;
  justify-items: center;
  gap: 12px;
  text-align: center;
  color: white;
}

.playerOverlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgb(3 7 12 / 0.32);
  color: rgb(241 246 252 / 0.94);
  text-align: center;
  pointer-events: none;
}

.pausedOverlay {
  pointer-events: none;
}

.playerOverlayError {
  gap: 10px;
  align-content: center;
  background: rgb(3 7 12 / 0.68);
  padding: 24px;
}

.overlayIcon {
  display: grid;
  place-items: center;
  filter: drop-shadow(0 10px 22px rgb(0 0 0 / 0.28));
}

.overlayText {
  max-width: min(420px, calc(100% - 48px));
  font-size: 13px;
  line-height: 1.5;
  color: rgb(239 245 252 / 0.9);
}

.loadingSpinner {
  width: 42px;
  height: 42px;
  border: 3px solid rgb(245 248 252 / 0.22);
  border-top-color: rgb(245 248 252 / 0.92);
  border-right-color: rgb(245 248 252 / 0.56);
  border-radius: 999px;
  box-shadow: 0 10px 26px rgb(0 0 0 / 0.28);
  animation: loading-spin 780ms linear infinite;
}

.emptyIcon {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  border: 1px solid rgb(255 255 255 / 0.14);
  background: rgb(255 255 255 / 0.08);
  display: grid;
  place-items: center;
  color: rgb(232 239 248 / 0.92);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.08);
}

.emptyText {
  display: grid;
  gap: 7px;
}

.emptyTitle {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0;
}

.emptyHint {
  font-size: 13px;
  line-height: 1.5;
  color: rgb(226 233 242 / 0.78);
}

.playerQuickActions {
  position: absolute;
  right: 14px;
  bottom: 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  opacity: 0;
  transform: translateY(4px);
  pointer-events: none;
  transition:
    opacity 160ms ease,
    transform 180ms ease;
}

.playerQuickActions.visible,
.playerShell:focus-within .playerQuickActions {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

.playerActionBtn {
  width: 36px;
  height: 36px;
  border: 1px solid rgb(255 255 255 / 0.16);
  border-radius: 12px;
  background: rgb(11 16 23 / 0.72);
  color: rgb(238 244 252 / 0.94);
  backdrop-filter: blur(10px);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    box-shadow 180ms ease;
}

.playerActionBtn:hover {
  background: rgb(22 31 44 / 0.86);
  border-color: rgb(255 255 255 / 0.26);
  box-shadow: 0 10px 24px rgb(0 0 0 / 0.24);
}

@media (max-width: 640px) {
  .playerEmptyState {
    width: min(300px, calc(100% - 32px));
    gap: 10px;
  }

  .emptyIcon {
    width: 48px;
    height: 48px;
    border-radius: 16px;
  }

  .emptyTitle {
    font-size: 18px;
  }

  .emptyHint {
    font-size: 12px;
  }

  .playerQuickActions {
    right: 10px;
    bottom: 10px;
  }

  .playerActionBtn {
    width: 32px;
    height: 32px;
    border-radius: 10px;
  }
}

@keyframes loading-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
