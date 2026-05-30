<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
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
import { toMediaEngineLoadInput } from "@/features/room/video/mediaEngineTypes";
import { useRoomMediaEngine } from "@/features/room/video/useRoomMediaEngine";
import type { MediaHealthState } from "@/features/room/video/types";

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
  (e: "resource-status-change", value: "idle" | "ready" | "stalling" | "error"): void;
  (e: "duration-change", value: number): void;
  (e: "time-change", value: number): void;
  (e: "buffered-progress-change", value: number): void;
  (e: "buffered-ranges-change", value: Array<{ startPercent: number; endPercent: number }>): void;
  (e: "seek-capability-change", value: boolean): void;
  (e: "waiting-change", value: boolean): void;
  (e: "error", value: string): void;
}>();

const shellRef = ref<HTMLElement | null>(null);
const isVideoFullscreen = ref(false);
const controlsVisible = ref(false);
const pointerIdle = ref(false);
let controlsHideTimer = 0;

const player = useRoomMediaEngine({
  writeLog: () => {},
});
const videoRef = player.videoRef;
const hasSource = computed(() => Boolean(player.appliedUrl.value));
const displayedResourceStatus = computed(() =>
  toDisplayedResourceStatus(player.mediaHealthState.value, hasSource.value));
const showEmptyState = computed(() => !hasSource.value);
const showWaitingState = computed(() => hasSource.value && player.mediaHealthState.value === "stalling");
const showPausedState = computed(() =>
  hasSource.value &&
  player.mediaHealthState.value === "ready" &&
  player.playerState.value === "paused" &&
  !player.errorMessage.value);
const shouldAutoHideActions = computed(() =>
  isVideoFullscreen.value || Boolean(props.isTheaterMode));

function toDisplayedResourceStatus(status: MediaHealthState, sourceAvailable: boolean) {
  if (!sourceAvailable) return "idle";
  if (status === "unknown") return "stalling";
  return status;
}

function setVideoRef(el: unknown) {
  videoRef.value = el instanceof HTMLVideoElement ? el : null;
  if (videoRef.value) {
    player.setVolume(props.volume);
  }
}

async function loadCurrentSource() {
  if (!videoRef.value) return;

  const input = toMediaEngineLoadInput(props.sourceType, props.sourceUrl, props.sourceFile);
  await player.loadSource(input ?? "");
}

async function playVideo() {
  const video = videoRef.value;
  await player.applyPlayback({
    status: "playing",
    position_seconds: player.currentTime.value,
    playback_rate: video?.playbackRate || 1,
  }, { syncPosition: false });
}

function pauseVideo() {
  const video = videoRef.value;
  void player.applyPlayback({
    status: "paused",
    position_seconds: player.currentTime.value,
    playback_rate: video?.playbackRate || 1,
  }, { syncPosition: false });
}

async function togglePlayback() {
  if (player.playerState.value === "playing") {
    pauseVideo();
    return;
  }

  await playVideo();
}

function seekToPercent(percent: number) {
  const nextTime = player.seekToPercent(percent);
  if (nextTime === null) return;

  const video = videoRef.value;
  void player.applyPlayback({
    status: "paused",
    position_seconds: nextTime,
    playback_rate: video?.playbackRate || 1,
  }, { syncPosition: false });
}

async function seekToSeconds(seconds: number) {
  const video = videoRef.value;
  await player.applyPlayback({
    status: "paused",
    position_seconds: Math.max(0, seconds),
    playback_rate: video?.playbackRate || 1,
  }, { syncPosition: true });
}

async function captureCurrentFrame() {
  const video = videoRef.value;
  if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    throw new Error("screenshotNoFrame");
  }

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("screenshotFailed");
  }

  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) {
    throw new Error("screenshotFailed");
  }

  return blob;
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

watch(
  () => [props.sourceType, props.sourceUrl, props.sourceFile, props.sourceRevision, videoRef.value] as const,
  () => {
    void loadCurrentSource();
  },
  { immediate: true },
);
watch(
  () => props.volume,
  (value) => player.setVolume(value),
  { immediate: true },
);
watch(player.playerState, (value) => {
  emit("play-state-change", value === "playing");
}, { immediate: true });
watch(displayedResourceStatus, (value) => {
  emit("resource-status-change", value);
  emit("waiting-change", value === "stalling");
}, { immediate: true });
watch(player.duration, (value) => emit("duration-change", value), { immediate: true });
watch(player.currentTime, (value) => emit("time-change", value), { immediate: true });
watch(player.bufferedProgressPercent, (value) => emit("buffered-progress-change", value), { immediate: true });
watch(player.bufferedRangePercents, (value) => emit("buffered-ranges-change", value), { immediate: true });
watch(player.canSeek, (value) => emit("seek-capability-change", value), { immediate: true });
watch(player.errorMessage, (value) => {
  if (value) emit("error", value);
});

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
  playVideo,
  pauseVideo,
  togglePlayback,
  seekToPercent,
  seekToSeconds,
  captureCurrentFrame,
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
        v-show="hasSource && player.mediaHealthState.value !== 'error'"
        :ref="setVideoRef"
        class="playerVideo"
        playsinline
        preload="auto"
        @loadstart="player.handleVideoEvent('loadstart')"
        @loadedmetadata="player.handleVideoEvent('loadedmetadata')"
        @durationchange="player.handleVideoEvent('durationchange')"
        @timeupdate="player.handleTimeUpdate"
        @play="player.handleVideoEvent('play')"
        @playing="player.handleVideoEvent('playing')"
        @pause="player.handleVideoEvent('pause')"
        @waiting="player.handleVideoEvent('waiting')"
        @stalled="player.handleVideoEvent('stalled')"
        @canplay="player.handleVideoEvent('canplay')"
        @canplaythrough="player.handleVideoEvent('canplaythrough')"
        @progress="player.handleProgress"
        @seeking="player.handleVideoEvent('seeking')"
        @seeked="player.handleVideoEvent('seeked')"
        @ended="player.handleVideoEvent('ended')"
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
      <div v-else-if="player.mediaHealthState.value === 'error'" class="playerOverlay playerOverlayError">
        <div class="overlayIcon">
          <AppIcon :icon="ExclamationTriangleIcon" :size="30" />
        </div>
        <div class="overlayText">{{ player.errorMessage.value }}</div>
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
  z-index: 2;
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
  z-index: 4;
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
