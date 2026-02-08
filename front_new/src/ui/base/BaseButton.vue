<script setup lang="ts">
defineProps<{
  type?: "button" | "submit";
  disabled?: boolean;
  variant?: "default" | "primary";
}>();
</script>

<template>
  <button
    class="btn"
    :class="variant ?? 'default'"
    :type="type ?? 'button'"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

<style scoped>
.btn {
  height: 40px;
  padding: 0 14px;
  border-radius: var(--r-2);
  cursor: pointer;

  font-weight: 500;
  transition: background 0.15s ease, border-color 0.15s ease;
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

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>