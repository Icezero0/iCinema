<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: "default" | "accent" | "muted";
    size?: "sm" | "md";
  }>(),
  {
    tone: "default",
    size: "md",
  },
);
</script>

<template>
  <span class="pill" :class="[`tone-${tone}`, `size-${size}`]">
    <slot />
  </span>
</template>

<style scoped>
.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid var(--c-border);
  white-space: nowrap;
  user-select: none;
  -webkit-user-select: none;
}

.size-sm {
  min-height: 22px;
  padding: 0 10px;
  font-size: 12px;
}

.size-md {
  min-height: 28px;
  padding: 0 12px;
  font-size: 12px;
}

.tone-default {
  background: color-mix(in srgb, var(--c-surface) 80%, white);
  color: var(--c-text);
  border-color: color-mix(in srgb, var(--c-primary) 18%, var(--c-border));
}

.tone-accent {
  background: color-mix(in srgb, var(--c-primary) 10%, var(--c-surface));
  color: var(--c-text);
  border-color: color-mix(in srgb, var(--c-primary) 32%, var(--c-border));
}

.tone-muted {
  background: color-mix(in srgb, var(--c-surface) 70%, var(--c-bg));
  color: var(--c-text-muted);
  border-color: var(--c-border);
}
</style>
