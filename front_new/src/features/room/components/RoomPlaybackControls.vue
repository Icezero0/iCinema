<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  ArrowPathIcon,
  FilmIcon,
  SpeakerXMarkIcon,
  SpeakerWaveIcon,
} from "@heroicons/vue/24/outline";
import { PauseIcon, PlayIcon } from "@heroicons/vue/24/solid";
import AppIcon from "@/ui/base/AppIcon.vue";
import RoomSourcePanel from "@/features/room/components/RoomSourcePanel.vue";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";

const props = defineProps<{
  isPlaying: boolean;
  progress: number;
  bufferedProgress: number;
  bufferedRanges: Array<{ startPercent: number; endPercent: number }>;
  volume: number;
  sourceType: RoomVideoSourceType;
  sourceUrl: string;
  sourceFileName: string;
  timelineLabel: string;
  playLabel: string;
  pauseLabel: string;
  syncLabel: string;
  sourceLabel: string;
  sourcePanelTitle: string;
  volumeLabel: string;
}>();

const emit = defineEmits<{
  (e: "toggle-play"): void;
  (e: "update:progress", value: number): void;
  (e: "update:volume", value: number): void;
  (e: "apply-source", value: {
    sourceType: RoomVideoSourceType;
    externalUrl: string;
    localFile: File | null;
  }): void;
}>();

const rootRef = ref<HTMLElement | null>(null);
const sourceOpen = ref(false);
const sourceTypeDraft = ref<RoomVideoSourceType>(props.sourceType);
const sourceExternalUrlDraft = ref(props.sourceUrl);
const sourceLocalFileDraft = ref<File | null>(null);
const sourceLocalFileNameDraft = ref(props.sourceFileName);
const volumeOpen = ref(false);
const syncAnimating = ref(false);
const volumeValue = computed(() =>
  Math.min(100, Math.max(0, Math.round(props.volume))));
const progressValue = computed(() =>
  Math.min(100, Math.max(0, props.progress)));
const bufferedValue = computed(() =>
  Math.max(progressValue.value, Math.min(100, Math.max(0, props.bufferedProgress))));
const shouldShowBufferedSegments = computed(() => props.sourceType === "external_url");
const bufferedSegments = computed(() => {
  if (!shouldShowBufferedSegments.value) return [];

  if (props.bufferedRanges.length > 0) {
    return props.bufferedRanges
      .map((range) => {
        const start = Math.min(100, Math.max(0, range.startPercent));
        const end = Math.min(100, Math.max(start, range.endPercent));
        return {
          left: `${start}%`,
          width: `${end - start}%`,
          minWidth: "6px",
        };
      })
      .filter((range) => Number.parseFloat(range.width) > 0);
  }

  if (bufferedValue.value <= 0) return [];
  return [{
    left: "0%",
    width: `${bufferedValue.value}%`,
    minWidth: bufferedValue.value > 0 ? "6px" : "0",
  }];
});

function onProgressInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit("update:progress", Number(target.value));
}

function handleLocalFileSelected(file: File | null) {
  sourceLocalFileDraft.value = file;
  sourceLocalFileNameDraft.value = file?.name ?? "";
}

function handleApplySourceDraft() {
  emit("apply-source", {
    sourceType: sourceTypeDraft.value,
    externalUrl: sourceExternalUrlDraft.value,
    localFile: sourceLocalFileDraft.value,
  });
  sourceOpen.value = false;
}

function toggleSourcePanel() {
  sourceOpen.value = !sourceOpen.value;
  if (sourceOpen.value) {
    sourceTypeDraft.value = props.sourceType;
    sourceExternalUrlDraft.value = props.sourceUrl;
    sourceLocalFileDraft.value = null;
    sourceLocalFileNameDraft.value = props.sourceFileName;
    volumeOpen.value = false;
  }
}

function toggleVolumePanel() {
  volumeOpen.value = !volumeOpen.value;
  if (volumeOpen.value) {
    sourceOpen.value = false;
  }
}

function triggerSyncAnimation() {
  syncAnimating.value = false;
  window.setTimeout(() => {
    syncAnimating.value = true;
  }, 0);
  window.setTimeout(() => {
    syncAnimating.value = false;
  }, 720);
}

function onVolumeInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit("update:volume", Math.min(100, Math.max(0, Math.round(Number(target.value)))));
}

function onDocumentPointerDown(event: PointerEvent) {
  const root = rootRef.value;
  const target = event.target as Node | null;
  if (!root || !target || root.contains(target)) return;

  sourceOpen.value = false;
  volumeOpen.value = false;
}

function onDocumentKeyDown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  sourceOpen.value = false;
  volumeOpen.value = false;
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown);
  document.addEventListener("keydown", onDocumentKeyDown);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onDocumentPointerDown);
  document.removeEventListener("keydown", onDocumentKeyDown);
});
</script>

<template>
  <div ref="rootRef" class="controlDock">
    <div class="controlGroup">
      <div class="popoverWrap sourceWrap">
        <button
          class="iconControlBtn"
          type="button"
          :aria-label="sourceLabel"
          :aria-expanded="sourceOpen"
          @click="toggleSourcePanel"
        >
          <AppIcon :icon="FilmIcon" :size="18" />
        </button>

        <Transition name="floating-fade">
          <div v-if="sourceOpen" class="sourcePanel">
            <RoomSourcePanel
              :title="sourcePanelTitle"
              :source-type="sourceTypeDraft"
              :external-url="sourceExternalUrlDraft"
              :local-file-name="sourceLocalFileNameDraft"
              @update:source-type="sourceTypeDraft = $event"
              @update:external-url="sourceExternalUrlDraft = $event"
              @select-local-file="handleLocalFileSelected"
              @apply="handleApplySourceDraft"
            />
          </div>
        </Transition>
      </div>

      <button
        class="iconControlBtn"
        type="button"
        :aria-label="syncLabel"
        @click="triggerSyncAnimation"
      >
        <AppIcon
          :icon="ArrowPathIcon"
          :size="18"
          class="syncIcon"
          :class="{ spinning: syncAnimating }"
        />
      </button>
      <button
        class="iconControlBtn prominent"
        type="button"
        :aria-label="isPlaying ? pauseLabel : playLabel"
        @click="emit('toggle-play')"
      >
        <Transition name="playback-icon" mode="out-in">
          <AppIcon
            :key="isPlaying ? 'pause' : 'play'"
            :icon="isPlaying ? PauseIcon : PlayIcon"
            :size="18"
          />
        </Transition>
      </button>
    </div>

    <div class="timelineGroup">
      <div class="timelineSliderWrap">
        <div class="timelineTrack" aria-hidden="true">
          <span
            v-for="(range, index) in bufferedSegments"
            :key="`buffered-${index}-${range.left}-${range.width}`"
            class="timelineBufferedSegment"
            :style="{ left: range.left, width: range.width, minWidth: range.minWidth }"
          />
          <span
            class="timelineProgressFill"
            :style="{ width: `${progressValue}%` }"
          />
        </div>
        <input
          class="timelineSlider"
          type="range"
          min="0"
          max="100"
          step="0.01"
          :value="progress"
          @input="onProgressInput"
        >
      </div>
      <span class="timelineLabel">{{ timelineLabel }}</span>
    </div>

    <div class="controlGroup rightAligned">
      <div class="popoverWrap volumeWrap">
        <button
          class="volumeTrigger"
          type="button"
          :class="{ active: volumeOpen }"
          :aria-label="volumeLabel"
          :aria-expanded="volumeOpen"
          @click="toggleVolumePanel"
        >
          <AppIcon :icon="volumeValue === 0 ? SpeakerXMarkIcon : SpeakerWaveIcon" :size="18" />
        </button>

        <Transition name="floating-fade">
          <div v-if="volumeOpen" class="volumePanel">
            <div class="volumeValue">{{ volumeValue }}%</div>
            <div class="volumeSliderWrap">
              <input
                class="volumeSlider"
                type="range"
                min="0"
                max="100"
                :value="volumeValue"
                @input="onVolumeInput"
              >
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.controlDock {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--c-border);
  border-radius: 18px;
  background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg));
}

.controlGroup {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  min-width: 0;
}

.controlGroup.rightAligned {
  justify-content: flex-end;
}

.iconControlBtn {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    transform 160ms ease,
    background-color 160ms ease,
    border-color 160ms ease,
    box-shadow 180ms ease,
    color 160ms ease;
  transform-origin: center;
}

.iconControlBtn:hover {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--c-surface) 88%, white);
  border-color: color-mix(in srgb, var(--c-primary) 16%, var(--c-border));
  box-shadow: 0 10px 18px rgb(0 0 0 / 0.06);
}

.iconControlBtn:active {
  transform: translateY(0) scale(0.96);
  box-shadow: 0 4px 8px rgb(0 0 0 / 0.08);
}

.iconControlBtn.prominent {
  width: 42px;
  height: 42px;
  background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface));
  border-color: color-mix(in srgb, var(--c-primary) 24%, var(--c-border));
}

.iconControlBtn.prominent:hover {
  background: color-mix(in srgb, var(--c-primary) 16%, var(--c-surface));
  border-color: color-mix(in srgb, var(--c-primary) 32%, var(--c-border));
}

.popoverWrap {
  position: relative;
  display: inline-flex;
}

.timelineGroup {
  display: grid;
  gap: 8px;
  align-content: center;
  min-width: 0;
}

.timelineSliderWrap {
  position: relative;
  height: 18px;
  min-width: 0;
}

.timelineTrack {
  position: absolute;
  top: 50%;
  right: 0;
  left: 0;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-border) 74%, var(--c-bg));
  transform: translateY(-50%);
  pointer-events: none;
}

.timelineBufferedSegment,
.timelineProgressFill {
  position: absolute;
  top: 0;
  bottom: 0;
  border-radius: inherit;
}

.timelineBufferedSegment {
  z-index: 1;
  background: color-mix(in srgb, var(--c-text-muted) 44%, var(--c-border));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, white 18%, transparent);
}

.timelineProgressFill {
  left: 0;
  z-index: 2;
  background: #62a5ff;
  box-shadow: 0 0 10px rgb(98 165 255 / 0.24);
}

.timelineSlider {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 18px;
  margin: 0;
  appearance: none;
  background: transparent;
  accent-color: #62a5ff;
  cursor: pointer;
}

.timelineSlider::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 999px;
  background: transparent;
}

.timelineSlider::-webkit-slider-thumb {
  width: 0;
  height: 0;
  margin-top: 0;
  border: 0;
  border-radius: 999px;
  appearance: none;
  background: transparent;
  box-shadow: none;
}

.timelineSlider::-moz-range-track {
  height: 6px;
  border-radius: 999px;
  background: transparent;
}

.timelineSlider::-moz-range-progress {
  height: 6px;
  border-radius: 999px;
  background: transparent;
}

.timelineSlider::-moz-range-thumb {
  width: 0;
  height: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  box-shadow: none;
}

.timelineLabel {
  font-size: 12px;
  color: var(--c-text-muted);
}

.syncIcon.spinning {
  animation: sync-spin 720ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.sourcePanel {
  position: absolute;
  left: 0;
  bottom: calc(100% + 12px);
  width: 340px;
  border: 1px solid var(--c-border);
  border-radius: 16px;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--c-surface) 94%, white),
      color-mix(in srgb, var(--c-surface) 90%, var(--c-bg))
    );
  box-shadow: 0 18px 40px rgb(0 0 0 / 0.12);
  padding: 12px;
  z-index: 4;
}

.volumeTrigger {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--c-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    transform 160ms ease,
    background-color 160ms ease,
    color 160ms ease,
    box-shadow 180ms ease;
}

.volumeTrigger:hover,
.volumeTrigger.active {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--c-hover) 90%, var(--c-surface));
  box-shadow: 0 8px 16px rgb(0 0 0 / 0.05);
}

.volumeTrigger:active {
  transform: translateY(0) scale(0.94);
  box-shadow: 0 4px 10px rgb(0 0 0 / 0.08);
}

.volumePanel {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 10px);
  width: 64px;
  height: 184px;
  margin-left: -32px;
  padding: 12px 10px 12px;
  border: 1px solid var(--c-border);
  border-radius: 18px;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--c-surface) 94%, white),
      color-mix(in srgb, var(--c-surface) 90%, var(--c-bg))
    );
  box-shadow: 0 18px 40px rgb(0 0 0 / 0.12);
  display: grid;
  align-content: space-between;
  justify-items: center;
  z-index: 4;
}

.volumeValue {
  font-size: 11px;
  color: var(--c-text-muted);
}

.volumeSliderWrap {
  width: 100%;
  height: 126px;
  display: grid;
  place-items: center;
}

.volumeSlider {
  width: 100%;
  height: 100%;
  margin: 0;
  writing-mode: vertical-lr;
  direction: rtl;
  accent-color: #62a5ff;
  cursor: pointer;
}

.floating-fade-enter-active,
.floating-fade-leave-active {
  transition: opacity 140ms ease, transform 160ms ease;
}

.floating-fade-enter-from,
.floating-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.floating-fade-enter-to,
.floating-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

.playback-icon-enter-active,
.playback-icon-leave-active {
  transition:
    opacity 140ms ease,
    transform 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.playback-icon-enter-from {
  opacity: 0;
  transform: scale(0.72) rotate(-10deg);
}

.playback-icon-leave-to {
  opacity: 0;
  transform: scale(0.72) rotate(10deg);
}

.playback-icon-enter-to,
.playback-icon-leave-from {
  opacity: 1;
  transform: scale(1) rotate(0deg);
}

@keyframes sync-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 860px) {
  .controlDock {
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 8px;
    padding: 10px;
  }

  .controlGroup {
    gap: 6px;
  }

  .iconControlBtn {
    width: 34px;
    height: 34px;
    border-radius: 10px;
  }

  .iconControlBtn.prominent {
    width: 38px;
    height: 38px;
  }

  .timelineGroup {
    gap: 6px;
  }

  .timelineLabel {
    font-size: 11px;
  }
}

@media (max-width: 560px) {
  .controlDock {
    padding: 10px 9px;
    gap: 6px;
  }

  .controlGroup {
    gap: 5px;
  }

  .sourcePanel {
    width: min(340px, calc(100vw - 64px));
  }

  .iconControlBtn {
    width: 32px;
    height: 32px;
    border-radius: 10px;
  }

  .iconControlBtn.prominent {
    width: 36px;
    height: 36px;
  }

  .volumeTrigger {
    width: 30px;
    height: 30px;
  }

  .timelineGroup {
    gap: 4px;
  }

  .timelineLabel {
    font-size: 10px;
  }
}
</style>
