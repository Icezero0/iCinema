<script setup lang="ts">
import AppIcon from "@/ui/base/AppIcon.vue";

type IconComp = any;

const props = withDefaults(
  defineProps<{
    icon?: IconComp;
    rightIcon?: IconComp;
    danger?: boolean;
    disabled?: boolean;
  }>(),
  {
    danger: false,
    disabled: false,
  }
);

const emit = defineEmits<{ (e: "click", ev: MouseEvent): void }>();

function onClick(ev: MouseEvent) {
  if (props.disabled) return;
  emit("click", ev);
}
</script>

<template>
  <button
    class="item"
    :class="{ danger, disabled }"
    type="button"
    :disabled="disabled"
    @click="onClick"
  >
    <span class="left">
      <span v-if="icon" class="icon" aria-hidden="true">
        <AppIcon :icon="icon" :size="16" />
      </span>
      <span class="label">
        <slot />
      </span>
    </span>

    <span v-if="rightIcon" class="rightIcon" aria-hidden="true">
      <AppIcon :icon="rightIcon" :size="16" />
    </span>
  </button>
</template>

<style scoped>
.item {
  width: 100%;
  height: 36px;

  display: flex;
  align-items: center;
  justify-content: space-between;

  padding: 0 10px;

  background: transparent;
  border: none;
  border-radius: var(--r-2);

  color: var(--c-text);
  font-size: 0.875rem;
  text-align: left;

  cursor: pointer;
  user-select: none;

  transition: background 160ms ease;
}

.item:hover {
  background: var(--c-hover);
}

:global([data-theme="dark"]) .item:hover {
  background: var(--c-hover);
}

.item:focus-visible {
  outline: 2px solid var(--c-border);
  outline-offset: 2px;
}

.left {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.icon {
  display: inline-flex;
  align-items: center;
  color: var(--c-text);
}

/* 防止长文案撑爆 */
.label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rightIcon {
  display: inline-flex;
  align-items: center;
  color: var(--c-text);
}

/* danger */
.item.danger {
  color: var(--c-danger, #d14343);
}
.item.danger:hover {
  background: rgba(209, 67, 67, 0.08);
}
:global([data-theme="dark"]) .item.danger:hover {
  background: rgba(209, 67, 67, 0.16);
}
.item.danger .icon,
.item.danger .rightIcon {
  color: var(--c-danger, #d14343);
}

/* disabled */
.item.disabled,
.item:disabled {
  opacity: 0.55;
  cursor: default;
}
.item.disabled:hover,
.item:disabled:hover {
  background: transparent;
}
</style>
