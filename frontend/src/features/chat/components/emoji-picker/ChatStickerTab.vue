<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, toRef } from "vue";
import { useI18n } from "vue-i18n";
import { resolveMediaUrl } from "@/infra/media";
import type { StickerTabProps } from "./types";
import { useStickerPointerDrag } from "./useStickerPointerDrag";

const props = defineProps<StickerTabProps>();

const emit = defineEmits<{
  action: [actionKey: string];
  select: [stickerId: number];
  remove: [stickerId: number];
  reorder: [stickerIds: number[]];
}>();

const { t } = useI18n();
const previewRef = ref<HTMLElement | null>(null);
const hoveredStickerId = ref<number | null>(null);
const previewOpen = ref(false);
const previewX = ref(0);
const previewY = ref(0);
const previewEnabled = ref(true);
const floatingTeleportTarget = ref<HTMLElement | "body">("body");
let previewOpenTimer: number | null = null;
let pointerMediaQuery: MediaQueryList | null = null;
let removePointerListener: (() => void) | null = null;

const hoveredSticker = computed(() => (
  hoveredStickerId.value == null
    ? null
    : props.stickerLibrary.find((sticker) => sticker.id === hoveredStickerId.value) ?? null
));
const {
  draggedSticker,
  draggingStickerId,
  dragOverlayStyle,
  setDragOverlayRef,
  pointerDragState,
  handleStickerPointerDown,
} = useStickerPointerDrag({
  stickerLibrary: toRef(props, "stickerLibrary"),
  isEditing: toRef(props, "isEditing"),
  closePreview,
  reorder: (stickerIds) => emit("reorder", stickerIds),
});

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
  const viewport = window.visualViewport;
  const viewportLeft = viewport?.offsetLeft ?? 0;
  const viewportTop = viewport?.offsetTop ?? 0;
  const viewportWidth = viewport?.width ?? window.innerWidth;
  const viewportHeight = viewport?.height ?? window.innerHeight;
  const minX = viewportLeft + viewportPadding;
  const maxX = viewportLeft + viewportWidth - viewportPadding;
  const minY = viewportTop + viewportPadding;
  const maxY = viewportTop + viewportHeight - viewportPadding;
  const rect = preview.getBoundingClientRect();
  let nextX = previewX.value;
  let nextY = previewY.value;

  if (nextX + rect.width > maxX) {
    nextX = Math.max(minX, nextX - rect.width - offset * 2);
  }

  if (nextY + rect.height > maxY) {
    nextY = Math.max(minY, maxY - rect.height);
  }

  nextX = Math.max(minX, Math.min(nextX, maxX - rect.width));
  nextY = Math.max(minY, Math.min(nextY, maxY - rect.height));

  previewX.value = nextX;
  previewY.value = nextY;
}

async function openPreview(stickerId: number, event: MouseEvent | FocusEvent) {
  if (!previewEnabled.value || props.isEditing) return;

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
  if (!previewEnabled.value || props.isEditing) return;

  previewX.value = event.clientX + 16;
  previewY.value = event.clientY - 8;

  if (!previewOpen.value) return;
  clampPreviewPosition();
}

function syncFloatingTeleportTarget() {
  floatingTeleportTarget.value = document.fullscreenElement instanceof HTMLElement
    ? document.fullscreenElement
    : "body";
}

onBeforeUnmount(() => {
  if (previewOpenTimer != null) {
    window.clearTimeout(previewOpenTimer);
    previewOpenTimer = null;
  }
  removePointerListener?.();
  document.removeEventListener("fullscreenchange", syncFloatingTeleportTarget);
});

onMounted(() => {
  if (typeof window === "undefined") return;
  syncFloatingTeleportTarget();
  document.addEventListener("fullscreenchange", syncFloatingTeleportTarget);

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
  if (props.isEditing) return;
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
        <div
          v-for="sticker in stickerLibrary"
          :key="`sticker-${sticker.id}`"
          class="emojiOption stickerOption"
          :class="{
            stickerOptionEditing: isEditing,
            stickerOptionDragging: draggingStickerId === sticker.id,
            stickerOptionDropTarget: pointerDragState?.targetStickerId === sticker.id,
          }"
          :data-sticker-id="sticker.id"
          role="button"
          tabindex="0"
          :aria-label="`Sticker ${sticker.id}`"
          @mouseenter="openPreview(sticker.id, $event)"
          @mousemove="updatePreviewPosition"
          @mouseleave="closePreview"
          @focus="openPreview(sticker.id, $event)"
          @blur="closePreview"
          @pointerdown="handleStickerPointerDown(sticker.id, $event)"
          @click="handleStickerClick(sticker.id)"
          @keydown.enter.prevent="handleStickerClick(sticker.id)"
          @keydown.space.prevent="handleStickerClick(sticker.id)"
        >
          <button
            v-if="isEditing && draggingStickerId !== sticker.id"
            class="stickerRemoveButton"
            type="button"
            :aria-label="`Remove sticker ${sticker.id}`"
            @mousedown.stop
            @click.stop="emit('remove', sticker.id)"
          >
            ×
          </button>
          <img
            v-if="draggingStickerId !== sticker.id"
            class="stickerOptionImage"
            :src="sticker.display_url || resolveMediaUrl(sticker.url)"
            :alt="`Sticker ${sticker.id}`"
          >
          <span
            v-else
            class="stickerDragPlaceholder"
            aria-hidden="true"
          />
        </div>
      </div>
    </section>
  </div>

  <Teleport :to="floatingTeleportTarget">
    <div
      v-if="pointerDragState && draggedSticker"
      :ref="setDragOverlayRef"
      class="stickerDragOverlay emojiOption stickerOption"
      :style="dragOverlayStyle"
      aria-hidden="true"
    >
      <img
        class="stickerOptionImage"
        :src="draggedSticker.display_url || resolveMediaUrl(draggedSticker.url)"
        :alt="`Sticker ${draggedSticker.id}`"
      >
    </div>

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
        :src="hoveredSticker.display_url || resolveMediaUrl(hoveredSticker.url)"
        :alt="`Sticker ${hoveredSticker.id}`"
      >
    </div>
  </Teleport>
</template>

<style scoped>
.stickerHoverPreview {
  position: fixed;
  z-index: 260;
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

:deep(.stickerOptionEditing) {
  cursor: grab;
  touch-action: none;
  user-select: none;
}

:deep(.stickerOptionEditing:active) {
  cursor: grabbing;
}

:deep(.stickerOptionDragging) {
  border-color: color-mix(in srgb, var(--c-border) 72%, transparent);
  background: color-mix(in srgb, var(--c-surface) 58%, transparent);
  box-shadow: none;
}

:deep(.stickerOptionDropTarget) {
  border-color: color-mix(in srgb, var(--c-primary) 48%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c-primary) 34%, transparent);
}

.stickerRemoveButton {
  position: absolute;
  top: -5px;
  right: -5px;
  z-index: 2;
  width: 18px;
  height: 18px;
  border: 1px solid color-mix(in srgb, #ef4444 72%, white);
  border-radius: 999px;
  background: #ef4444;
  color: white;
  display: grid;
  place-items: center;
  padding: 0;
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  box-shadow: 0 6px 14px rgb(239 68 68 / 0.26);
}

.stickerRemoveButton:hover {
  background: #dc2626;
}

.stickerDragPlaceholder {
  width: 100%;
  max-width: 46px;
  aspect-ratio: 1;
  border-radius: 9px;
  border: 1px dashed color-mix(in srgb, var(--c-text-muted) 32%, transparent);
  background: color-mix(in srgb, var(--c-surface) 72%, transparent);
}

.stickerDragOverlay {
  position: fixed;
  z-index: 220;
  display: grid;
  place-items: center;
  min-height: 58px;
  padding: 6px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 24%, var(--c-border));
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-surface) 94%, var(--c-bg));
  box-shadow: 0 16px 34px rgb(0 0 0 / 0.2);
  pointer-events: none;
}

.stickerDragOverlay .stickerOptionImage {
  width: 100%;
  max-width: 46px;
  height: auto;
  max-height: 46px;
  object-fit: contain;
}
</style>
