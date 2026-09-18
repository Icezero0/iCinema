<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/vue/24/outline';
import AppIcon from './AppIcon.vue';
import BaseIconButton from './BaseIconButton.vue';

defineOptions({ inheritAttrs: false });
const props = withDefaults(defineProps<{
  modelValue: string;
  min?: number;
  max?: number;
  step?: number | 'any';
  emptyValue?: number;
  placeholder?: string;
  disabled?: boolean;
}>(), { step: 1, disabled: false });
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>();
const { t } = useI18n();
const input = ref<HTMLInputElement | null>(null);
const atMin = computed(() => props.modelValue !== '' && props.min !== undefined && Number(props.modelValue) <= props.min);
const atMax = computed(() => props.modelValue !== '' && props.max !== undefined && Number(props.modelValue) >= props.max);

function change(direction: number) {
  const element = input.value;
  if (!element || props.disabled || element.matches(':disabled')) return;
  if (element.value === '') {
    element.value = String(Math.min(props.max ?? Infinity, Math.max(props.min ?? -Infinity, props.emptyValue ?? props.min ?? 0)));
  } else if (props.step === 'any') {
    element.value = String(Math.min(props.max ?? Infinity, Math.max(props.min ?? -Infinity, Number((Number(element.value) + direction).toFixed(10)))));
  } else if (direction > 0) element.stepUp();
  else element.stepDown();
  emit('update:modelValue', element.value);
  element.focus({ preventScroll: true });
}
</script>

<template>
  <div class="numberInput" :class="{ disabled }">
    <input ref="input" v-bind="$attrs" type="number" :value="modelValue" :min="min" :max="max" :step="step"
      :disabled="disabled" :placeholder="placeholder"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)" />
    <div class="steppers">
      <BaseIconButton class="stepButton" :disabled="disabled || atMax" :aria-label="t('numberInput.increase')" @click="change(1)">
        <AppIcon :icon="ChevronUpIcon" :size="13" />
      </BaseIconButton>
      <BaseIconButton class="stepButton" :disabled="disabled || atMin" :aria-label="t('numberInput.decrease')" @click="change(-1)">
        <AppIcon :icon="ChevronDownIcon" :size="13" />
      </BaseIconButton>
    </div>
  </div>
</template>

<style scoped>
.numberInput { display: flex; min-width: 0; height: 40px; box-sizing: border-box; border: 1px solid var(--c-border); border-radius: var(--r-2); background: var(--c-surface); color: var(--c-text); overflow: hidden; }
.numberInput:focus-within { border-color: rgba(127, 127, 127, 0.6); }
input { appearance: textfield; -moz-appearance: textfield; min-width: 0; width: 100%; flex: 1; border: 0; outline: none; padding: 0 12px; font: inherit; background: transparent; color: inherit; }
input::-webkit-inner-spin-button, input::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.steppers { display: grid; grid-template-rows: 1fr 1fr; border-left: 1px solid var(--c-border); }
.stepButton { width: 32px; height: 19px; border-radius: 0; }
.stepButton + .stepButton { border-top: 1px solid var(--c-border); }
.stepButton:focus-visible { outline: 2px solid var(--c-accent); outline-offset: -2px; }
.disabled { opacity: 0.5; }
</style>
