<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    animated?: boolean;
    tag?: string; // non-animated wrapper tag
    name?: string; // transition name when animated
    gap?: "sm" | "md" | "lg";
  }>(),
  {
    animated: false,
    tag: "div",
    name: "list",
    gap: "md",
  }
);

const gapClass = computed(() => {
  if (props.gap === "sm") return "gapSm";
  if (props.gap === "lg") return "gapLg";
  return "gapMd";
});
</script>

<template>
  <TransitionGroup
    v-if="animated"
    :name="name"
    tag="div"
    class="baseList"
    :class="gapClass"
  >
    <slot />
  </TransitionGroup>

  <component
    v-else
    :is="tag"
    class="baseList"
    :class="gapClass"
  >
    <slot />
  </component>
</template>

<style scoped>
.baseList {
  display: grid;
  position: relative; /* for leave absolute positioning */
}

.gapSm { gap: var(--s-2); }
.gapMd { gap: var(--s-3); }
.gapLg { gap: var(--s-4); }

/* Default animations for name="list"
   如果你传 name="noti"，会生成 noti-xxx 的 class（同样生效）
*/
:global(.list-move) {
  transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

:global(.list-leave-active) {
  position: absolute;
  left: 0;
  right: 0;
  pointer-events: none;
  z-index: 1;
  transition: opacity 180ms ease, transform 180ms ease;
}

:global(.list-leave-to) {
  opacity: 0;
  transform: translateY(-10px);
}

:global(.list-enter-active) {
  transition: opacity 160ms ease, transform 160ms ease;
}
:global(.list-enter-from) {
  opacity: 0;
  transform: translateY(6px);
}

/* 让任意 name 都能吃到相同规则：用属性选择器兜底（更通用） */
:global([class$="-move"]) {
  transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
}
:global([class$="-leave-active"]) {
  position: absolute;
  left: 0;
  right: 0;
  pointer-events: none;
  z-index: 1;
  transition: opacity 180ms ease, transform 180ms ease;
}
:global([class$="-leave-to"]) {
  opacity: 0;
  transform: translateY(-10px);
}
:global([class$="-enter-active"]) {
  transition: opacity 160ms ease, transform 160ms ease;
}
:global([class$="-enter-from"]) {
  opacity: 0;
  transform: translateY(6px);
}
</style>
