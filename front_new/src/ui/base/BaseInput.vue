<script setup lang="ts">
defineProps<{
  modelValue: string
  type?: string
  placeholder?: string
  disabled?: boolean
}>()

defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <input
    class="inp"
    :type="type ?? 'text'"
    :placeholder="placeholder"
    :disabled="disabled"
    :value="modelValue"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

<style scoped>
.inp {
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: var(--c-surface);
  color: var(--c-text);
  outline: none;
}
.inp:focus {
  border-color: rgba(127, 127, 127, 0.6);
}
</style>
