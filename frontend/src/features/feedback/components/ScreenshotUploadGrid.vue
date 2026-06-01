<script setup lang="ts">
import { computed, ref } from "vue";
import { PlusIcon, XMarkIcon } from "@heroicons/vue/24/outline";
import type { LocalImagePreview } from "@/features/feedback/composables/useLocalImagePreviews";
import AppIcon from "@/ui/base/AppIcon.vue";

const props = defineProps<{
  items: LocalImagePreview[];
  maxCount: number;
  addLabel: string;
  removeLabel: string;
}>();

const emit = defineEmits<{
  "files-selected": [files: File[]];
  remove: [id: number];
}>();

const inputRef = ref<HTMLInputElement | null>(null);
const isFull = computed(() => props.items.length >= props.maxCount);

function openPicker() {
  if (isFull.value) return;
  inputRef.value?.click();
}

function handleChange(event: Event) {
  const input = event.target as HTMLInputElement | null;
  const files = Array.from(input?.files ?? []);
  if (files.length > 0) {
    emit("files-selected", files);
  }
  if (input) {
    input.value = "";
  }
}
</script>

<template>
  <div class="screenshotGrid">
    <div
      v-for="item in items"
      :key="item.id"
      class="screenshotTile"
    >
      <img :src="item.url" :alt="item.file.name">
      <button
        class="removeScreenshotButton"
        type="button"
        :aria-label="removeLabel"
        @click="emit('remove', item.id)"
      >
        <AppIcon :icon="XMarkIcon" :size="14" />
      </button>
    </div>

    <button
      class="addScreenshotButton"
      type="button"
      :aria-label="addLabel"
      :disabled="isFull"
      @click="openPicker"
    >
      <AppIcon :icon="PlusIcon" :size="24" />
    </button>

    <input
      ref="inputRef"
      class="srOnlyFile"
      type="file"
      accept="image/png,image/jpeg,image/webp"
      multiple
      @change="handleChange"
    >
  </div>
</template>

<style scoped>
.screenshotGrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 10px;
}

.screenshotTile,
.addScreenshotButton {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: var(--c-surface);
  transition: border-color 0.16s ease, background 0.16s ease,
    transform 0.16s ease, box-shadow 0.16s ease;
}

.screenshotTile:hover,
.addScreenshotButton:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--c-primary) 42%, var(--c-border));
  background: var(--c-hover);
  transform: translateY(-1px);
  box-shadow: 0 8px 22px color-mix(in srgb, var(--c-text) 8%, transparent);
}

.screenshotTile img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.addScreenshotButton {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--c-primary);
  cursor: pointer;
}

.addScreenshotButton:disabled {
  color: var(--c-text-muted);
  cursor: not-allowed;
  opacity: 0.62;
}

.removeScreenshotButton {
  position: absolute;
  top: 6px;
  right: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 1px solid color-mix(in srgb, var(--c-border) 60%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-surface) 88%, transparent);
  color: var(--c-text);
  cursor: pointer;
  transition: background 0.16s ease, border-color 0.16s ease;
}

.removeScreenshotButton:hover {
  border-color: color-mix(in srgb, var(--c-danger) 42%, var(--c-border));
  background: color-mix(in srgb, var(--c-danger) 10%, var(--c-surface));
  color: var(--c-danger);
}

.srOnlyFile {
  position: fixed;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}
</style>
