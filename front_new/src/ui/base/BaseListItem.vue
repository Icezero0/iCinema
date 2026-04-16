<template>
  <div class="item" :class="{ interactive, dense }">
    <slot />
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    interactive?: boolean;
    dense?: boolean;
  }>(),
  {
    interactive: true,
    dense: false,
  }
);
</script>

<style scoped>
/* ✅ 你原来的 item 外观/hover 等，保持 scoped */
.item {
  padding: 14px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 75%, var(--c-bg));
  transition:
    background 140ms ease,
    border-color 140ms ease,
    box-shadow 140ms ease,
    transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1),
    opacity 180ms ease;
}

.item.dense {
  padding: 12px;
}

.item.interactive:hover {
  background: color-mix(in srgb, var(--c-hover) 55%, var(--c-surface));
  border-color: color-mix(in srgb, var(--c-border) 65%, var(--c-text));
  box-shadow: 0 10px 22px rgb(0 0 0 / 0.08);
}

.item,
.item * {
  cursor: default;
  user-select: text;
}

.item :deep(button),
.item :deep(button *),
.item :deep([role="button"]),
.item :deep([role="button"] *),
.item :deep(a),
.item :deep(a *),
.item :deep(input),
.item :deep(select),
.item :deep(textarea),
.item :deep(label) {
  cursor: pointer;
}

.item :deep(button:disabled),
.item :deep(button:disabled *),
.item :deep(input:disabled),
.item :deep(select:disabled),
.item :deep(textarea:disabled) {
  cursor: not-allowed;
}
</style>

<style>
/* ✅ 非 scoped：专门放 TransitionGroup 动画类（必须全局匹配） */

/* move：下面的 item 顶上来 */
.noti-move {
  transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

/* leave：当前 item 上浮淡出 */
.noti-leave-active {
  position: absolute;
  left: 0;
  right: 0;
  pointer-events: none;
  z-index: 1;
  transition: opacity 180ms ease, transform 180ms ease;
}

.noti-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* enter：可选（未来 ws prepend 会好看） */
.noti-enter-active {
  transition: opacity 160ms ease, transform 160ms ease;
}
.noti-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
</style>
