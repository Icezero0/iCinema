<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import { useToastsStore } from "@/stores/toasts.store";

const toasts = useToastsStore();
const { items } = storeToRefs(toasts);
const toastTeleportTarget = ref<HTMLElement | "body">("body");

function syncToastTeleportTarget() {
  toastTeleportTarget.value = document.fullscreenElement instanceof HTMLElement
    ? document.fullscreenElement
    : "body";
}

onMounted(() => {
  syncToastTeleportTarget();
  document.addEventListener("fullscreenchange", syncToastTeleportTarget);
});

onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", syncToastTeleportTarget);
});
</script>

<template>
  <Teleport :to="toastTeleportTarget">
    <div class="toastViewport" aria-live="polite" aria-atomic="true">
      <TransitionGroup name="toast">
        <div
          v-for="toast in items"
          :key="toast.id"
          class="toast"
          :class="`toast--${toast.tone}`"
          role="status"
        >
          <div class="toastMessage">{{ toast.message }}</div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toastViewport {
  position: fixed;
  top: 68px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 300;
  display: grid;
  gap: 10px;
  width: min(420px, calc(100vw - 24px));
  pointer-events: none;
}

.toast {
  pointer-events: auto;
  display: block;
  padding: 12px 16px;
  border-radius: 14px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 96%, var(--c-bg));
  box-shadow: 0 12px 30px rgb(0 0 0 / 0.12);
  text-align: center;
}

.toast--success {
  border-color: color-mix(in srgb, #2fb46e 26%, var(--c-border));
  background: color-mix(in srgb, #2fb46e 12%, var(--c-surface));
}

.toast--warning {
  border-color: color-mix(in srgb, var(--c-primary) 24%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface));
}

.toast--danger {
  border-color: color-mix(in srgb, var(--c-danger) 34%, var(--c-border));
  background: color-mix(in srgb, var(--c-danger) 12%, var(--c-surface));
}

.toastMessage {
  min-width: 0;
  font-size: 13px;
  line-height: 1.4;
  color: var(--c-text);
}

.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 160ms ease,
    transform 180ms ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 720px) {
  .toastViewport {
    top: 64px;
    left: 50%;
    right: auto;
    bottom: auto;
    transform: translateX(-50%);
    width: min(420px, calc(100vw - 24px));
  }
}
</style>
