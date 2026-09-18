<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import BaseCard from "@/ui/base/BaseCard.vue";
import BaseButton from "@/ui/base/BaseButton.vue";

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    title: string;
    message?: string;

    confirmText?: string;
    cancelText?: string;

    variant?: "default" | "danger";
    closeOnOverlay?: boolean;
    closeOnEsc?: boolean;
    lockScroll?: boolean;
    zIndex?: number;

    loading?: boolean;
    confirmDisabled?: boolean;
  }>(),
  {
    confirmText: "OK",
    cancelText: "Cancel",
    variant: "default",
    closeOnOverlay: true,
    closeOnEsc: true,
    lockScroll: true,
    zIndex: 80,
    loading: false,
    confirmDisabled: false,
  }
);

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "confirm"): void;
  (e: "cancel"): void;
}>();

const open = computed(() => props.modelValue);
const dialogRef = ref<HTMLElement | null>(null);
let previousFocus: HTMLElement | null = null;
const dialogTeleportTarget = ref<HTMLElement | "body">("body");

function syncDialogTeleportTarget() {
  dialogTeleportTarget.value = document.fullscreenElement instanceof HTMLElement
    ? document.fullscreenElement
    : "body";
}

function close() {
  emit("update:modelValue", false);
}

function onCancel() {
  emit("cancel");
  close();
}

function onConfirm() {
  if (props.loading || props.confirmDisabled) return;
  emit("confirm");
  close();
}

function onOverlayClick() {
  if (!props.closeOnOverlay) return;
  onCancel();
}

function onKeydown(e: KeyboardEvent) {
  if (!open.value) return;

  if (e.key === "Tab") {
    const buttons = Array.from(dialogRef.value?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? []);
    const first = buttons[0], last = buttons[buttons.length - 1];
    if (!first || !last) { e.preventDefault(); return; }
    if (!dialogRef.value?.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
    else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  if (e.key === "Escape" && props.closeOnEsc) {
    e.preventDefault();
    onCancel();
    return;
  }
}

watch(
  () => open.value,
  async (v, previous) => {
    if (props.lockScroll && (v || previous !== undefined)) document.documentElement.style.overflow = v ? "hidden" : "";
    if (v) {
      previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      await nextTick();
      if (open.value) dialogRef.value?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus();
    } else if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
  },
  { immediate: true },
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
  if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
});
</script>

<template>
  <Teleport :to="dialogTeleportTarget">
    <Transition name="fade">
      <div v-if="open" class="overlay" :style="{ zIndex }" role="presentation" @click="onOverlayClick">
        <Transition name="pop">
          <div ref="dialogRef" class="dialog" role="dialog" aria-modal="true" :aria-label="title" @click.stop>
            <BaseCard class="card">
              <div class="header">
                <div class="title">{{ title }}</div>
                <div v-if="message" class="message">{{ message }}</div>
              </div>

              <div class="actions">
                <BaseButton type="button" variant="default" :disabled="loading" @click="onCancel">
                  {{ cancelText }}
                </BaseButton>

                <BaseButton
                  type="button"
                  :variant="variant === 'danger' ? 'danger' : 'primary'"
                  :loading="loading"
                  :disabled="confirmDisabled"
                  @click="onConfirm"
                >
                  {{ confirmText }}
                </BaseButton>
              </div>
            </BaseCard>
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
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 16px;
  background: rgb(0 0 0 / 0.45);
}

.dialog {
  width: min(520px, 100%);
}

.card {
  padding: 18px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  border-radius: 16px;
  box-shadow: var(--shadow-lg, 0 10px 30px rgb(0 0 0 / 0.18));
}

.header {
  display: grid;
  gap: 8px;
  padding: 6px 6px 14px;
}

.title {
  font-size: 16px;
  font-weight: 650;
  color: var(--c-text);
}

.message {
  font-size: 13px;
  line-height: 1.4;
  color: var(--c-text-muted);
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 0 6px 6px;
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
  transform: translateY(6px) scale(0.98);
}
</style>
