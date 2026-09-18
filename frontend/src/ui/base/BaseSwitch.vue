<script setup lang="ts">
import { useAttrs, type StyleValue } from 'vue';
defineOptions({ inheritAttrs: false });
const attrs = useAttrs();
function inputAttrs() { return Object.fromEntries(Object.entries(attrs).filter(([key]) => key !== 'class' && key !== 'style')); }
withDefaults(defineProps<{ modelValue: boolean; disabled?: boolean }>(), { disabled: false });
const emit = defineEmits<{ (event: 'update:modelValue', value: boolean): void }>();
function change(event: Event) { emit('update:modelValue', (event.target as HTMLInputElement).checked); }
</script>

<template>
  <label class="baseSwitch" :class="$attrs.class" :style="$attrs.style as StyleValue">
    <span class="control">
      <input v-bind="inputAttrs()" class="input" type="checkbox" role="switch" :checked="modelValue" :disabled="disabled" @change="change" />
      <span class="visual" aria-hidden="true" />
    </span>
    <span class="label"><slot /></span>
  </label>
</template>

<style scoped>
.baseSwitch { display: inline-flex; align-items: center; gap: var(--s-2); font-size: 13px; color: var(--c-text); cursor: pointer; }
.control { position: relative; width: 42px; height: 24px; display: inline-flex; align-items: center; flex: 0 0 auto; }
.input { position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; opacity: 0; cursor: pointer; }
.visual { width: 42px; height: 24px; border-radius: 999px; border: 1px solid var(--c-border); background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg)); box-shadow: inset 0 1px 2px rgb(15 23 42 / 0.08); pointer-events: none; transition: background-color 160ms ease, border-color 160ms ease, box-shadow 160ms ease; }
.visual::after { content: ''; position: absolute; top: 4px; left: 4px; width: 16px; height: 16px; border-radius: 999px; background: color-mix(in srgb, var(--c-text-muted) 68%, white); box-shadow: 0 2px 5px rgb(15 23 42 / 0.18); transition: background-color 160ms ease, transform 180ms ease; }
.input:checked + .visual { border-color: color-mix(in srgb, var(--c-primary) 52%, var(--c-border)); background: color-mix(in srgb, var(--c-primary) 24%, var(--c-surface)); box-shadow: inset 0 1px 2px rgb(15 23 42 / 0.08), 0 0 0 3px color-mix(in srgb, var(--c-primary) 10%, transparent); }
.input:checked + .visual::after { background: var(--c-primary); transform: translateX(18px); }
.input:focus-visible + .visual { outline: 2px solid color-mix(in srgb, var(--c-primary) 54%, transparent); outline-offset: 2px; }
.input:disabled { cursor: not-allowed; } .input:disabled + .visual { opacity: 0.62; }
.label { overflow-wrap: anywhere; }
@media (prefers-reduced-motion: reduce) { .visual, .visual::after { transition: none; } }
</style>
