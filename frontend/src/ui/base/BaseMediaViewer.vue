<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useMediaViewerStore } from "@/stores/media-viewer.store";

const viewer = useMediaViewerStore();
const { open, src, alt, scale } = storeToRefs(viewer);
const stageRef = ref<HTMLElement | null>(null);
const imageNaturalWidth = ref(0);
const imageNaturalHeight = ref(0);
const stageWidth = ref(0);
const stageHeight = ref(0);
const offsetX = ref(0);
const offsetY = ref(0);
const isDragging = ref(false);
const suppressCloseUntil = ref(0);
const viewerTeleportTarget = ref<HTMLElement | "body">("body");
let dragPointerId: number | null = null;
let dragStartX = 0;
let dragStartY = 0;
let dragOriginOffsetX = 0;
let dragOriginOffsetY = 0;
let stageResizeObserver: ResizeObserver | null = null;

const baseScale = computed(() => {
  const naturalWidth = imageNaturalWidth.value;
  const naturalHeight = imageNaturalHeight.value;
  const nextStageWidth = stageWidth.value;
  const nextStageHeight = stageHeight.value;

  if (!naturalWidth || !naturalHeight || !nextStageWidth || !nextStageHeight) {
    return 1;
  }

  return Math.min(
    1,
    nextStageWidth / naturalWidth,
    nextStageHeight / naturalHeight,
  );
});

const effectiveScale = computed(() => baseScale.value * scale.value);

const renderedWidth = computed(() => imageNaturalWidth.value * effectiveScale.value);
const renderedHeight = computed(() => imageNaturalHeight.value * effectiveScale.value);
const overflowX = computed(() => Math.max(0, (renderedWidth.value - stageWidth.value) / 2));
const overflowY = computed(() => Math.max(0, (renderedHeight.value - stageHeight.value) / 2));
const canPanX = computed(() => overflowX.value > 0.5);
const canPanY = computed(() => overflowY.value > 0.5);

const imageStyle = computed(() => ({
  left: `calc(50% + ${offsetX.value}px)`,
  top: `calc(50% + ${offsetY.value}px)`,
  width: renderedWidth.value > 0 ? `${renderedWidth.value}px` : undefined,
  height: renderedHeight.value > 0 ? `${renderedHeight.value}px` : undefined,
  transform: "translate(-50%, -50%)",
  transition: isDragging.value
    ? "none"
    : "left 90ms ease-out, top 90ms ease-out, width 90ms ease-out, height 90ms ease-out",
  cursor: isDragging.value ? "grabbing" : "grab",
}));

function closeViewer() {
  viewer.closeViewer();
}

function syncViewerTeleportTarget() {
  viewerTeleportTarget.value = document.fullscreenElement instanceof HTMLElement
    ? document.fullscreenElement
    : "body";
}

function resetViewerState() {
  imageNaturalWidth.value = 0;
  imageNaturalHeight.value = 0;
  stageWidth.value = 0;
  stageHeight.value = 0;
  offsetX.value = 0;
  offsetY.value = 0;
  isDragging.value = false;
  dragPointerId = null;
}

function syncStageSize() {
  const stage = stageRef.value;
  if (!stage) return;

  stageWidth.value = stage.clientWidth;
  stageHeight.value = stage.clientHeight;
}

function attachStageObserver() {
  if (typeof ResizeObserver === "undefined" || !stageRef.value) return;

  stageResizeObserver?.disconnect();
  stageResizeObserver = new ResizeObserver(() => {
    syncStageSize();
    clampOffset();
  });
  stageResizeObserver.observe(stageRef.value);
}

function clampOffset() {
  offsetX.value = canPanX.value
    ? Math.max(-overflowX.value, Math.min(overflowX.value, offsetX.value))
    : 0;
  offsetY.value = canPanY.value
    ? Math.max(-overflowY.value, Math.min(overflowY.value, offsetY.value))
    : 0;
}

function requestClose() {
  if (Date.now() < suppressCloseUntil.value) return;
  closeViewer();
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape" || !open.value) return;
  closeViewer();
}

function handleImageLoad(event: Event) {
  const target = event.target as HTMLImageElement | null;
  if (!target) return;

  imageNaturalWidth.value = target.naturalWidth;
  imageNaturalHeight.value = target.naturalHeight;
}

function handleWheel(event: WheelEvent) {
  event.preventDefault();
  const step = event.deltaY < 0 ? 0.16 : -0.16;
  viewer.zoomBy(step);
}

function handlePointerDown(event: PointerEvent) {
  if (!open.value) return;

  dragPointerId = event.pointerId;
  dragStartX = event.clientX;
  dragStartY = event.clientY;
  dragOriginOffsetX = offsetX.value;
  dragOriginOffsetY = offsetY.value;
  isDragging.value = false;
}

function handlePointerMove(event: PointerEvent) {
  if (!open.value || dragPointerId !== event.pointerId) return;

  const deltaX = event.clientX - dragStartX;
  const deltaY = event.clientY - dragStartY;

  if (!isDragging.value && Math.hypot(deltaX, deltaY) > 4) {
    isDragging.value = true;
  }

  offsetX.value = canPanX.value ? dragOriginOffsetX + deltaX : 0;
  offsetY.value = canPanY.value ? dragOriginOffsetY + deltaY : 0;
  clampOffset();
}

function handlePointerUp(event: PointerEvent) {
  if (dragPointerId !== event.pointerId) return;

  if (isDragging.value) {
    suppressCloseUntil.value = Date.now() + 120;
  }

  dragPointerId = null;
  isDragging.value = false;
}

onMounted(() => {
  syncViewerTeleportTarget();
  window.addEventListener("keydown", handleKeydown);
  window.addEventListener("pointermove", handlePointerMove, { passive: true });
  window.addEventListener("pointerup", handlePointerUp, { passive: true });
  window.addEventListener("pointercancel", handlePointerUp, { passive: true });
  document.addEventListener("fullscreenchange", syncViewerTeleportTarget);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleKeydown);
  window.removeEventListener("pointermove", handlePointerMove);
  window.removeEventListener("pointerup", handlePointerUp);
  window.removeEventListener("pointercancel", handlePointerUp);
  document.removeEventListener("fullscreenchange", syncViewerTeleportTarget);
  stageResizeObserver?.disconnect();
  stageResizeObserver = null;
});

watch(open, (isOpen) => {
  if (!isOpen) {
    stageResizeObserver?.disconnect();
    stageResizeObserver = null;
    resetViewerState();
    return;
  }

  syncViewerTeleportTarget();
  void nextTick(() => {
    syncStageSize();
    attachStageObserver();
    clampOffset();
  });
});

watch(src, () => {
  resetViewerState();
});

watch(
  [effectiveScale, renderedWidth, renderedHeight, stageWidth, stageHeight],
  () => {
    clampOffset();
  },
);
</script>

<template>
  <Teleport :to="viewerTeleportTarget">
    <Transition name="viewer-fade">
      <div
        v-if="open"
        class="viewerOverlay"
        role="dialog"
        aria-modal="true"
        :aria-label="alt || 'Media viewer'"
        @click="requestClose"
        @wheel.prevent="handleWheel"
      >
        <div ref="stageRef" class="viewerStage">
          <img
            class="viewerImage"
            :src="src"
            :alt="alt"
            :style="imageStyle"
            @click="requestClose"
            @wheel.prevent="handleWheel"
            @load="handleImageLoad"
            @pointerdown.stop="handlePointerDown"
          >
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.viewerOverlay {
  position: fixed;
  inset: 0;
  z-index: 260;
  display: grid;
  place-items: center;
  background: rgb(0 0 0 / 0.84);
  padding:
    calc(24px + env(safe-area-inset-top))
    calc(24px + env(safe-area-inset-right))
    calc(24px + env(safe-area-inset-bottom))
    calc(24px + env(safe-area-inset-left));
}

.viewerStage {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.viewerImage {
  position: absolute;
  object-fit: contain;
  transform-origin: center center;
  user-select: none;
  -webkit-user-drag: none;
  border-radius: 0;
  box-shadow: 0 24px 64px rgb(0 0 0 / 0.36);
}

.viewer-fade-enter-active,
.viewer-fade-leave-active {
  transition: opacity 160ms ease;
}

.viewer-fade-enter-from,
.viewer-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .viewerOverlay {
    padding:
      calc(12px + env(safe-area-inset-top))
      calc(12px + env(safe-area-inset-right))
      calc(12px + env(safe-area-inset-bottom))
      calc(12px + env(safe-area-inset-left));
  }

  .viewerImage {
    border-radius: 0;
  }
}
</style>
