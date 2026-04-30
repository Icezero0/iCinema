<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { CheckIcon, ChevronDownIcon } from "@heroicons/vue/24/outline";
import AppIcon from "@/ui/base/AppIcon.vue";
import BaseMenuItem from "@/ui/base/BaseMenuItem.vue";

type SelectOption = {
  value: string;
  label: string;
};

const props = withDefaults(
  defineProps<{
    modelValue: string;
    options: SelectOption[];
    placeholder?: string;
    disabled?: boolean;
    width?: string | number;
    maxWidth?: string | number;
    label?: string;
    labelPosition?: "top" | "start";
  }>(),
  {
    placeholder: "",
    disabled: false,
    width: "100%",
    maxWidth: "100%",
    label: "",
    labelPosition: "top",
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const rootRef = ref<HTMLElement | null>(null);
const open = ref(false);

const selectedOption = computed(() => {
  return props.options.find((option) => option.value === props.modelValue) ?? null;
});

const displayLabel = computed(() => {
  return selectedOption.value?.label || props.placeholder || "";
});

function normalizeSize(value: string | number) {
  return typeof value === "number" ? `${value}px` : value;
}

const rootStyle = computed(() => {
  return {
    width: normalizeSize(props.width),
    maxWidth: normalizeSize(props.maxWidth),
  };
});

function close() {
  open.value = false;
}

function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
}

function selectOption(value: string) {
  if (props.disabled) return;
  emit("update:modelValue", value);
  close();
}

function onDocPointerDown(event: PointerEvent) {
  if (!open.value) return;
  const root = rootRef.value;
  const target = event.target as Node | null;

  if (root && target && !root.contains(target)) {
    close();
  }
}

function onKeyDown(event: KeyboardEvent) {
  if (!open.value && (event.key === "Enter" || event.key === " ")) {
    return;
  }

  if (event.key === "Escape") {
    close();
  }
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocPointerDown);
  document.addEventListener("keydown", onKeyDown);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onDocPointerDown);
  document.removeEventListener("keydown", onKeyDown);
});
</script>

<template>
  <div class="fieldRoot" :class="`label-${labelPosition}`">
    <span v-if="label" class="fieldLabel">{{ label }}</span>

    <div
      ref="rootRef"
      class="selectRoot"
      :class="{ open, disabled }"
      :style="rootStyle"
    >
      <button
        class="trigger"
        type="button"
        :disabled="disabled"
        :aria-expanded="open"
        @click="toggle"
      >
        <span class="triggerLabel">{{ displayLabel }}</span>
        <AppIcon class="triggerIcon" :icon="ChevronDownIcon" :size="16" />
      </button>

      <Transition name="menu-fade">
        <div v-show="open" class="menu" role="listbox">
          <BaseMenuItem
            v-for="option in options"
            :key="option.value"
            :rightIcon="modelValue === option.value ? CheckIcon : undefined"
            @click="selectOption(option.value)"
          >
            {{ option.label }}
          </BaseMenuItem>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.fieldRoot {
  display: grid;
  gap: 8px;
}

.fieldRoot.label-start {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.fieldLabel {
  font-size: 12px;
  color: var(--c-text-muted);
  white-space: nowrap;
}

.selectRoot {
  position: relative;
}

.trigger {
  width: 100%;
  min-height: 42px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 12px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--c-surface) 94%, white),
      color-mix(in srgb, var(--c-surface) 90%, var(--c-bg))
    );
  color: var(--c-text);
  cursor: pointer;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    transform 160ms ease,
    background 160ms ease;
}

.trigger:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--c-primary) 26%, var(--c-border));
  box-shadow: 0 10px 22px rgb(0 0 0 / 0.04);
}

.trigger:focus-visible,
.selectRoot.open .trigger {
  outline: none;
  border-color: color-mix(in srgb, var(--c-primary) 42%, var(--c-border));
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-primary) 14%, transparent);
  transform: translateY(-1px);
}

.trigger:disabled,
.selectRoot.disabled .trigger {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.triggerLabel {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.triggerIcon {
  color: var(--c-text-muted);
  flex: 0 0 auto;
  transition: transform 160ms ease;
}

.selectRoot.open .triggerIcon {
  transform: rotate(180deg);
}

.menu {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  right: 0;
  min-width: 100%;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  border-radius: 14px;
  padding: 6px;
  box-shadow: 0 18px 50px rgb(0 0 0 / 0.12);
  transform-origin: top center;
  z-index: 30;
}

.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 120ms ease, transform 120ms ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.menu-fade-enter-to,
.menu-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

@media (max-width: 520px) {
  .fieldRoot {
    gap: 4px;
  }

  .fieldRoot.label-start {
    display: grid;
    align-items: stretch;
    gap: 4px;
  }

  .fieldLabel {
    font-size: 10px;
    line-height: 1.1;
  }

  .trigger {
    min-height: 36px;
    gap: 6px;
    padding: 0 8px;
    border-radius: 12px;
  }

  .triggerLabel {
    font-size: 12px;
  }

  .menu {
    top: calc(100% + 6px);
    border-radius: 12px;
    padding: 4px;
  }
}
</style>
