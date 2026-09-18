<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseDialog from './BaseDialog.vue';
import BaseButton from './BaseButton.vue';
import BaseNumberInput from './BaseNumberInput.vue';

const props = defineProps<{ modelValue: string; disabled?: boolean; label: string }>();
const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>();
const { t, locale } = useI18n();
const open = ref(false), year = ref(String(new Date().getFullYear())), month = ref(new Date().getMonth());
const trigger = ref<HTMLButtonElement>(), panel = ref<HTMLElement>();
const validYear = computed(() => /^\d{4}$/.test(year.value) && Number(year.value) >= 1900 && Number(year.value) <= 2100);
const displayedYear = computed(() => validYear.value ? Number(year.value) : new Date().getFullYear());
const monthLabel = computed(() => new Intl.DateTimeFormat(locale.value, { month: 'long' }).format(new Date(2020, month.value, 1)));
const weekdays = computed(() => Array.from({ length: 7 }, (_, n) => new Intl.DateTimeFormat(locale.value, { weekday: 'short' }).format(new Date(2024, 0, 7 + n))));
const offset = computed(() => new Date(displayedYear.value, month.value, 1).getDay());
const days = computed(() => new Date(displayedYear.value, month.value + 1, 0).getDate());
function value(day: number) { return `${year.value}-${String(month.value + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`; }
async function show() {
  const parsed = /^(\d{4})-(\d{2})-\d{2}$/.exec(props.modelValue);
  year.value = parsed ? parsed[1]! : String(new Date().getFullYear());
  month.value = parsed ? Number(parsed[2]) - 1 : new Date().getMonth();
  open.value = true;
  await nextTick();
  panel.value?.querySelector<HTMLButtonElement>('.selected, .day')?.focus();
}
function close() { open.value = false; void nextTick(() => trigger.value?.focus()); }
function select(value: string) { emit('update:modelValue', value); close(); }
function shift(delta: number) {
  const date = new Date(displayedYear.value, month.value + delta, 1);
  if (date.getFullYear() < 1900 || date.getFullYear() > 2100) return;
  year.value = String(date.getFullYear()); month.value = date.getMonth();
}
function keyboard(event: KeyboardEvent) {
  if (event.key === 'Tab') {
    const nodes = Array.from(panel.value?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled)') ?? []);
    const first = nodes[0], last = nodes[nodes.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }
  const day = Number((event.target as HTMLElement).dataset.day);
  const delta = ({ ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 } as Record<string, number>)[event.key];
  if (!day || delta === undefined) return;
  event.preventDefault();
  const date = new Date(displayedYear.value, month.value, day + delta);
  if (date.getFullYear() < 1900 || date.getFullYear() > 2100) return;
  year.value = String(date.getFullYear()); month.value = date.getMonth();
  void nextTick(() => panel.value?.querySelector<HTMLButtonElement>(`[data-day="${date.getDate()}"]`)?.focus());
}
</script>

<template>
  <button ref="trigger" type="button" class="dateInput" :disabled="disabled" :aria-label="label" aria-haspopup="dialog" :aria-expanded="open" @click="show">
    <span :class="{ placeholder: !modelValue }">{{ modelValue || t('catalogImport.pickDate') }}</span>
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M7 3v4m10-4v4M3 11h18" /></svg>
  </button>
  <BaseDialog :model-value="open" :max-width="360" :z-index="100" :aria-label="label" @update:model-value="close">
    <section ref="panel" class="calendar" @keydown="keyboard">
      <div class="heading"><strong>{{ label }}</strong><BaseButton @click="close">{{ t('catalogAdmin.close') }}</BaseButton></div>
      <div class="navigation">
        <BaseButton :disabled="!validYear || (year === '1900' && month === 0)" :aria-label="t('catalogImport.previousMonth')" @click="shift(-1)">‹</BaseButton>
        <span>{{ monthLabel }}</span>
        <BaseNumberInput v-model="year" :min="1900" :max="2100" :aria-label="t('catalogAdmin.fields.year')" />
        <BaseButton :disabled="!validYear || (year === '2100' && month === 11)" :aria-label="t('catalogImport.nextMonth')" @click="shift(1)">›</BaseButton>
      </div>
      <div class="days">
        <span v-for="(weekday, index) in weekdays" :key="index" class="weekday">{{ weekday }}</span>
        <span v-for="n in offset" :key="`blank-${n}`" />
        <button v-for="day in days" :key="day" type="button" class="day" :class="{ selected: value(day) === modelValue }" :data-day="day" :aria-label="value(day)" :aria-pressed="value(day) === modelValue" :disabled="!validYear" @click="select(value(day))">{{ day }}</button>
      </div>
      <div class="footer"><BaseButton @click="select('')">{{ t('catalogImport.clearDate') }}</BaseButton></div>
    </section>
  </BaseDialog>
</template>

<style scoped>
.dateInput { min-height: 40px; width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 12px; border: 1px solid var(--c-border); border-radius: var(--r-2); background: var(--c-surface); color: var(--c-text); font: inherit; cursor: pointer; }
.placeholder, .weekday { color: var(--c-text-muted); } .dateInput:disabled { opacity: .6; cursor: not-allowed; }
.calendar { background: var(--c-surface); color: var(--c-text); border: 1px solid var(--c-border); border-radius: var(--r-2); padding: 20px; max-height: calc(100dvh - 48px); overflow: auto; }
.heading, .navigation, .footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.navigation { margin: 20px 0 12px; } .navigation :deep(.numberInput) { width: 112px; } .navigation > span { white-space: nowrap; }
.days { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; text-align: center; }
.weekday { font-size: 12px; padding: 8px 0; } .day { border: 0; border-radius: var(--r-2); aspect-ratio: 1; background: transparent; color: var(--c-text); cursor: pointer; }
.day:hover { background: var(--c-bg); } .day.selected { background: var(--c-primary); color: var(--c-on-primary, #111); }
.dateInput:focus-visible, .day:focus-visible { outline: 2px solid var(--c-primary); outline-offset: 2px; } .footer { margin-top: 16px; justify-content: flex-end; }
</style>
