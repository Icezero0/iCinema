<script setup lang="ts">
import { ArrowPathIcon, SpeakerWaveIcon } from "@heroicons/vue/24/outline";
import { PauseIcon, PlayIcon } from "@heroicons/vue/24/solid";
import AppIcon from "@/ui/base/AppIcon.vue";

defineProps<{
  isPlaying: boolean;
  progress: number;
  timelineLabel: string;
  playLabel: string;
  pauseLabel: string;
  syncLabel: string;
  volumeLabel: string;
}>();

const emit = defineEmits<{
  (e: "toggle-play"): void;
  (e: "update:progress", value: number): void;
}>();

function onProgressInput(event: Event) {
  const target = event.target as HTMLInputElement;
  emit("update:progress", Number(target.value));
}
</script>

<template>
  <div class="controlDock">
    <div class="controlGroup">
      <button
        class="iconControlBtn"
        type="button"
        :aria-label="syncLabel"
      >
        <AppIcon :icon="ArrowPathIcon" :size="18" />
      </button>
      <button
        class="iconControlBtn prominent"
        type="button"
        :aria-label="isPlaying ? pauseLabel : playLabel"
        @click="emit('toggle-play')"
      >
        <AppIcon :icon="isPlaying ? PauseIcon : PlayIcon" :size="18" />
      </button>
    </div>

    <div class="timelineGroup">
      <input
        class="timelineSlider"
        type="range"
        min="0"
        max="100"
        :value="progress"
        @input="onProgressInput"
      >
      <span class="timelineLabel">{{ timelineLabel }}</span>
    </div>

    <div class="controlGroup rightAligned">
      <button
        class="iconControlBtn"
        type="button"
        :aria-label="volumeLabel"
      >
        <AppIcon :icon="SpeakerWaveIcon" :size="18" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.controlDock {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
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
  flex-wrap: wrap;
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
}

.iconControlBtn.prominent {
  width: 42px;
  height: 42px;
  background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface));
  border-color: color-mix(in srgb, var(--c-primary) 24%, var(--c-border));
}

.timelineGroup {
  display: grid;
  gap: 8px;
  align-content: center;
}

.timelineSlider {
  width: 100%;
  margin: 0;
  accent-color: #62a5ff;
  cursor: pointer;
}

.timelineLabel {
  font-size: 12px;
  color: var(--c-text-muted);
}

@media (max-width: 800px) {
  .controlDock {
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 8px;
    padding: 10px;
  }

  .controlGroup {
    gap: 6px;
    flex-wrap: nowrap;
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
</style>
