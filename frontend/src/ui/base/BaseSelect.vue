<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
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
const menuRef = ref<HTMLElement | null>(null);
const open = ref(false);
const menuPlacement = ref<"down" | "up">("down");
const menuMaxHeight = ref<number | null>(null);

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

const menuStyle = computed(() => {
  return menuMaxHeight.value
    ? { maxHeight: `${menuMaxHeight.value}px` }
    : {};
});

function getScrollParent(element: HTMLElement | null) {
  let current = element?.parentElement ?? null;

  while (current) {
    const style = window.getComputedStyle(current);
    const overflowY = style.overflowY;
    if (overflowY === "auto" || overflowY === "scroll" || overflowY === "overlay") {
      return current;
    }
    current = current.parentElement;
  }

  return null;
}

async function updateMenuPlacement() {
  await nextTick();

  const root = rootRef.value;
  const menu = menuRef.value;
  if (!root || !menu) return;

  const rootRect = root.getBoundingClientRect();
  const scrollParent = getScrollParent(root);
  const scrollParentRect = scrollParent?.getBoundingClientRect();
  const viewportTop = Math.max(0, scrollParentRect?.top ?? 0);
  const viewportBottom = Math.min(window.innerHeight, scrollParentRect?.bottom ?? window.innerHeight);
  const gap = window.matchMedia("(max-width: 520px)").matches ? 6 : 10;
  const availableBelow = Math.max(0, viewportBottom - rootRect.bottom - gap);
  const availableAbove = Math.max(0, rootRect.top - viewportTop - gap);
  const naturalHeight = menu.scrollHeight;
  const shouldOpenUp = availableBelow < naturalHeight && availableAbove > availableBelow;
  const availableHeight = shouldOpenUp ? availableAbove : availableBelow;

  menuPlacement.value = shouldOpenUp ? "up" : "down";
  menuMaxHeight.value = naturalHeight > availableHeight
    ? Math.max(80, availableHeight)
    : null;
}

function close() {
  open.value = false;
  menuMaxHeight.value = null;
}

function toggle() {
  if (props.disabled) return;
  open.value = !open.value;
  if (open.value) {
    void updateMenuPlacement();
  }
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

function onWindowChange() {
  if (open.value) {
    void updateMenuPlacement();
  }
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocPointerDown);
  document.addEventListener("keydown", onKeyDown);
  window.addEventListener("resize", onWindowChange);
  window.addEventListener("scroll", onWindowChange, true);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onDocPointerDown);
  document.removeEventListener("keydown", onKeyDown);
  window.removeEventListener("resize", onWindowChange);
  window.removeEventListener("scroll", onWindowChange, true);
});
</script>

<template>
  <div class="fieldRoot" :class="`label-${labelPosition}`">
    <span v-if="label" class="fieldLabel">{{ label }}</span>

    <div
      ref="rootRef"
      class="selectRoot"
      :class="{ open, disabled, 'placement-up': menuPlacement === 'up' }"
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
        <div
          v-show="open"
          ref="menuRef"
          class="menu"
          role="listbox"
          :style="menuStyle"
        >
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
  background: color-mix(in srgb, var(--c-surface) 92%, var(--c-bg));
  color: var(--c-text);
  cursor: pointer;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    background 160ms ease;
}

.trigger:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--c-primary) 26%, var(--c-border));
  background: color-mix(in srgb, var(--c-hover) 68%, var(--c-surface));
  box-shadow: 0 8px 18px rgb(0 0 0 / 0.035);
}

.trigger:focus-visible,
.selectRoot.open .trigger {
  outline: none;
  border-color: color-mix(in srgb, var(--c-primary) 42%, var(--c-border));
  background: color-mix(in srgb, var(--c-surface) 96%, var(--c-primary));
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-primary) 14%, transparent);
}

.trigger:disabled,
.selectRoot.disabled .trigger {
  opacity: 0.6;
  cursor: not-allowed;
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
  overflow-y: auto;
  box-shadow: 0 18px 50px rgb(0 0 0 / 0.12);
  transform-origin: top center;
  z-index: 30;
}

.selectRoot.placement-up .menu {
  top: auto;
  bottom: calc(100% + 10px);
  transform-origin: bottom center;
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

.selectRoot.placement-up .menu-fade-enter-from,
.selectRoot.placement-up .menu-fade-leave-to {
  transform: translateY(6px);
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

  .selectRoot.placement-up .menu {
    top: auto;
    bottom: calc(100% + 6px);
  }
}
</style>
