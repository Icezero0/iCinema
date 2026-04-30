<script setup lang="ts">
withDefaults(
  defineProps<{
    type?: "button" | "submit";
    disabled?: boolean;
    loading?: boolean;
    variant?: "default" | "primary" | "danger";
  }>(),
  {
    type: "button",
    variant: "default",
    disabled: false,
    loading: false,
  }
);
</script>

<template>
  <button
    class="btn"
    :class="variant"
    :type="type"
    :disabled="disabled || loading"
  >
    <span class="content" :class="{ hidden: loading }">
      <slot />
    </span>
    <span v-if="loading" class="loading" aria-hidden="true" />
  </button>
</template>

<style scoped>
.btn {
  height: 40px;
  min-height: 40px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 14px;
  border-radius: var(--r-2);
  cursor: pointer !important;
  gap: 8px;

  font-weight: 500;
  transition: background 0.15s ease, border-color 0.15s ease, opacity 0.15s ease;
  position: relative;
}

.btn.default {
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text);
}
.btn.default:hover:not(:disabled) {
  background: var(--c-hover);
}

.btn.primary {
  border: 1px solid transparent;
  background: var(--c-primary);
  color: var(--c-primary-text);
}
.btn.primary:hover:not(:disabled) {
  background: var(--c-primary-hover);
}

.btn.danger {
  border: 1px solid transparent;
  background: var(--c-danger);
  color: var(--c-danger-text, var(--c-primary-text));
}
.btn.danger:hover:not(:disabled) {
  background: var(--c-danger-hover, var(--c-danger));
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed !important;
}

.content.hidden {
  opacity: 0;
}

.content,
.loading {
  pointer-events: none;
}

.loading {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  position: absolute;
  inset: 0;
  margin: auto;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
