<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { resolveMediaUrl } from "@/infra/media";
import type { StickerTabProps } from "./types";

const props = defineProps<StickerTabProps>();

const emit = defineEmits<{
  action: [actionKey: string];
  select: [stickerId: number];
}>();

const { t } = useI18n();
const previewRef = ref<HTMLElement | null>(null);
const hoveredStickerId = ref<number | null>(null);
const previewOpen = ref(false);
const previewX = ref(0);
const previewY = ref(0);
const previewEnabled = ref(true);
let previewOpenTimer: number | null = null;
let pointerMediaQuery: MediaQueryList | null = null;
let removePointerListener: (() => void) | null = null;

const hoveredSticker = computed(() => (
  hoveredStickerId.value == null
    ? null
    : props.stickerLibrary.find((sticker) => sticker.id === hoveredStickerId.value) ?? null
));

function closePreview() {
  if (previewOpenTimer != null) {
    window.clearTimeout(previewOpenTimer);
    previewOpenTimer = null;
  }
  previewOpen.value = false;
  hoveredStickerId.value = null;
}

function clampPreviewPosition() {
  const preview = previewRef.value;
  if (!preview) return;

  const viewportPadding = 10;
  const offset = 16;
  const rect = preview.getBoundingClientRect();
  let nextX = previewX.value;
  let nextY = previewY.value;

  if (nextX + rect.width > window.innerWidth - viewportPadding) {
    nextX = Math.max(viewportPadding, nextX - rect.width - offset * 2);
  }

  if (nextY + rect.height > window.innerHeight - viewportPadding) {
    nextY = Math.max(viewportPadding, window.innerHeight - rect.height - viewportPadding);
  }

  previewX.value = nextX;
  previewY.value = nextY;
}

async function openPreview(stickerId: number, event: MouseEvent | FocusEvent) {
  if (!previewEnabled.value) return;

  const target = event.currentTarget as HTMLElement | null;
  const nextX = event instanceof MouseEvent
    ? event.clientX + 16
    : target
      ? target.getBoundingClientRect().right + 12
      : previewX.value;
  const nextY = event instanceof MouseEvent
    ? event.clientY - 8
    : target
      ? target.getBoundingClientRect().top
      : previewY.value;

  if (previewOpenTimer != null) {
    window.clearTimeout(previewOpenTimer);
    previewOpenTimer = null;
  }

  hoveredStickerId.value = stickerId;
  previewX.value = nextX;
  previewY.value = nextY;

  if (previewOpen.value) {
    clampPreviewPosition();
    return;
  }

  previewOpenTimer = window.setTimeout(async () => {
    previewOpenTimer = null;
    if (hoveredStickerId.value !== stickerId) return;

    previewOpen.value = true;
    await nextTick();
    clampPreviewPosition();
  }, 420);
}

function updatePreviewPosition(event: MouseEvent) {
  if (!previewEnabled.value) return;

  previewX.value = event.clientX + 16;
  previewY.value = event.clientY - 8;

  if (!previewOpen.value) return;
  clampPreviewPosition();
}

onBeforeUnmount(() => {
  if (previewOpenTimer != null) {
    window.clearTimeout(previewOpenTimer);
    previewOpenTimer = null;
  }
  removePointerListener?.();
});

onMounted(() => {
  if (typeof window === "undefined") return;

  pointerMediaQuery = window.matchMedia("(hover: hover) and (pointer: fine)");
  const syncPreviewCapability = (event?: MediaQueryList | MediaQueryListEvent) => {
    previewEnabled.value = event?.matches ?? pointerMediaQuery?.matches ?? true;
    if (!previewEnabled.value) {
      closePreview();
    }
  };

  syncPreviewCapability(pointerMediaQuery);
  pointerMediaQuery.addEventListener("change", syncPreviewCapability);
  removePointerListener = () => {
    pointerMediaQuery?.removeEventListener("change", syncPreviewCapability);
    removePointerListener = null;
    pointerMediaQuery = null;
  };
});

function handleStickerClick(stickerId: number) {
  closePreview();
  emit("select", stickerId);
}
</script>

<template>
  <div class="emojiSections stickerSections">
    <section class="emojiSection">
      <p class="emojiSectionLabel">
        {{ t("chat.emojiPanel.sections.stickerActions.title") }}
      </p>
      <div class="emojiGrid stickerActionGrid">
        <button
          v-for="item in actionItems"
          :key="item.key"
          class="emojiOption stickerActionOption"
          type="button"
          :aria-label="item.label"
          :disabled="item.disabled"
          @mousedown.prevent
          @click="emit('action', item.key)"
        >
          <component :is="item.icon" class="stickerActionIcon" />
        </button>
      </div>
    </section>

    <section class="emojiSection">
      <p class="emojiSectionLabel">
        {{ t("chat.emojiPanel.sections.stickers") }}
      </p>
      <div v-if="isLoading" class="emojiEmpty stickerEmpty">
        {{ loadingLabel || t("common.loading") }}
      </div>
      <div v-else-if="error" class="emojiEmpty stickerEmpty">
        {{ error }}
      </div>
      <div v-else-if="stickerLibrary.length === 0" class="emojiEmpty stickerEmpty">
        {{ emptyLabel }}
      </div>
      <div v-else class="emojiGrid stickerGrid">
        <button
          v-for="sticker in stickerLibrary"
          :key="`sticker-${sticker.id}`"
          class="emojiOption stickerOption"
          type="button"
          :aria-label="`Sticker ${sticker.id}`"
          @mousedown.prevent
          @mouseenter="openPreview(sticker.id, $event)"
          @mousemove="updatePreviewPosition"
          @mouseleave="closePreview"
          @focus="openPreview(sticker.id, $event)"
          @blur="closePreview"
          @click="handleStickerClick(sticker.id)"
        >
          <img
            class="stickerOptionImage"
            :src="resolveMediaUrl(sticker.url)"
            :alt="`Sticker ${sticker.id}`"
          >
        </button>
      </div>
    </section>
  </div>

  <Teleport to="body">
    <div
      v-if="previewOpen && hoveredSticker"
      ref="previewRef"
      class="stickerHoverPreview"
      :style="{
        left: `${previewX}px`,
        top: `${previewY}px`,
      }"
      aria-hidden="true"
    >
      <img
        class="stickerHoverPreviewImage"
        :src="resolveMediaUrl(hoveredSticker.url)"
        :alt="`Sticker ${hoveredSticker.id}`"
      >
    </div>
  </Teleport>
</template>

<style scoped>
.stickerHoverPreview {
  position: fixed;
  z-index: 140;
  display: grid;
  place-items: center;
  width: min(168px, calc(100vw - 20px));
  max-height: min(168px, calc(100vh - 20px));
  padding: 8px;
  border: 1px solid color-mix(in srgb, var(--c-border) 88%, white);
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 94%, var(--c-bg));
  box-shadow: 0 14px 32px rgb(0 0 0 / 0.18);
  pointer-events: none;
}

.stickerHoverPreviewImage {
  display: block;
  width: auto;
  max-width: 152px;
  height: auto;
  max-height: 152px;
  object-fit: contain;
}
</style>
