<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue: boolean;

    // overlay / keyboard
    closeOnOverlay?: boolean;
    closeOnEsc?: boolean;

    // layout
    maxWidth?: number; // e.g. 520
    zIndex?: number; // default 80

    // behavior
    lockScroll?: boolean;

    // a11y
    ariaLabel?: string;
  }>(),
  {
    closeOnOverlay: true,
    closeOnEsc: true,
    maxWidth: 520,
    zIndex: 80,
    lockScroll: true,
    ariaLabel: "Dialog",
  }
);

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "close"): void; // 统一关闭事件（overlay/esc/外部关闭都走这个语义）
}>();

const open = computed(() => props.modelValue);
const pointerDownOnOverlay = ref(false);
const dialogTeleportTarget = ref<HTMLElement | "body">("body");

function syncDialogTeleportTarget() {
  dialogTeleportTarget.value = document.fullscreenElement instanceof HTMLElement
    ? document.fullscreenElement
    : "body";
}

function close() {
  emit("update:modelValue", false);
  emit("close");
}

function onOverlayPointerDown(event: PointerEvent) {
  if (event.button !== 0) return;
  pointerDownOnOverlay.value = true;
}

function onOverlayPointerUp(event: PointerEvent) {
  if (event.button !== 0) return;
  if (!props.closeOnOverlay || !pointerDownOnOverlay.value) return;
  pointerDownOnOverlay.value = false;
  close();
}

function onDialogPointerDown() {
  pointerDownOnOverlay.value = false;
}

function onKeydown(e: KeyboardEvent) {
  if (!open.value) return;
  if (e.key !== "Escape") return;
  if (!props.closeOnEsc) return;

  e.preventDefault();
  close();
}

watch(
  () => open.value,
  (v) => {
    if (!props.lockScroll) return;
    document.documentElement.style.overflow = v ? "hidden" : "";
    if (!v) {
      pointerDownOnOverlay.value = false;
    }
  }
);

onMounted(() => {
  syncDialogTeleportTarget();
  window.addEventListener("keydown", onKeydown);
  document.addEventListener("fullscreenchange", syncDialogTeleportTarget);
});
onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown);
  document.removeEventListener("fullscreenchange", syncDialogTeleportTarget);
  if (props.lockScroll) document.documentElement.style.overflow = "";
});

const overlayStyle = computed(() => ({ zIndex: String(props.zIndex) }));
const dialogStyle = computed(() => ({ maxWidth: `${props.maxWidth}px` }));
</script>

<template>
  <Teleport :to="dialogTeleportTarget">
    <Transition name="fade">
      <div
        v-if="open"
        class="overlay"
        :style="overlayStyle"
        role="presentation"
        @pointerdown.self="onOverlayPointerDown"
        @pointerup.self="onOverlayPointerUp"
      >
        <Transition name="pop">
          <div
            class="dialog"
            :style="dialogStyle"
            role="dialog"
            aria-modal="true"
            :aria-label="ariaLabel"
            @pointerdown="onDialogPointerDown"
            @click.stop
          >
            <slot />
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;

  padding:
    calc(16px + env(safe-area-inset-top))
    calc(16px + env(safe-area-inset-right))
    calc(16px + env(safe-area-inset-bottom))
    calc(16px + env(safe-area-inset-left));

  background: rgb(0 0 0 / 0.45);

  overflow: auto;
}

.dialog {
  width: 100%;
  max-width: min(100%, var(--dialog-maxw, 520px));

  overflow: hidden;

  max-height: calc(100dvh - 32px - env(safe-area-inset-top) - env(safe-area-inset-bottom));
}

@media (max-width: 640px) {
  .overlay {
    padding:
      calc(12px + env(safe-area-inset-top))
      calc(12px + env(safe-area-inset-right))
      calc(12px + env(safe-area-inset-bottom))
      calc(12px + env(safe-area-inset-left));
  }

  .dialog {
    max-height: calc(100dvh - 24px - env(safe-area-inset-top) - env(safe-area-inset-bottom));
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 180ms ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.pop-enter-active,
.pop-leave-active {
  transition: transform 180ms ease, opacity 180ms ease;
  will-change: transform, opacity;
}
.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
