<script setup lang="ts">
defineProps<{
  type?: "button" | "submit";
  disabled?: boolean;
  ariaLabel?: string;
}>();
</script>

<template>
  <button
    class="iconBtn"
    :type="type ?? 'button'"
    :disabled="disabled"
    :aria-label="ariaLabel"
  >
    <slot />
  </button>
</template>

<style scoped>
.iconBtn {
  width: 40px;
  height: 40px;

  display: grid;
  place-items: center;

  border: none;
  background: transparent;
  padding: 0;
  border-radius: var(--r-2);

  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;

  transition: background 0.15s ease;

  color: var(--c-text);
}

.iconBtn:hover:not(:disabled) {
  background: var(--c-hover);
}

.iconBtn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
