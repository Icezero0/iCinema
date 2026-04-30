<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
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

    loading?: boolean;
    confirmDisabled?: boolean;
  }>(),
  {
    confirmText: "OK",
    cancelText: "Cancel",
    variant: "default",
    closeOnOverlay: true,
    closeOnEsc: true,
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

  if (e.key === "Escape" && props.closeOnEsc) {
    e.preventDefault();
    onCancel();
    return;
  }
}

watch(
  () => open.value,
  (v) => {
    document.documentElement.style.overflow = v ? "hidden" : "";
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
  document.documentElement.style.overflow = "";
});
</script>

<template>
  <Teleport :to="dialogTeleportTarget">
    <Transition name="fade">
      <div v-if="open" class="overlay" role="presentation" @click="onOverlayClick">
        <Transition name="pop">
          <div class="dialog" role="dialog" aria-modal="true" @click.stop>
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
