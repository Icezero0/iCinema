<script setup lang="ts">
const props = defineProps<{
  icon: any;
  size?: number;
}>();
</script>

<template>
  <component
    :is="props.icon"
    class="appIcon"
    :style="{
      width: `${props.size ?? 20}px`,
      height: `${props.size ?? 20}px`,
    }"
    aria-hidden="true"
  />
</template>

<style scoped>
.appIcon {
  display: block;
  /* ✅ 核心：颜色从父级继承 */
  color: inherit;
}

/* ✅ 防止某些 icon 组件内部写死 stroke/fill（保险） */
.appIcon :deep(path),
.appIcon :deep(svg) {
  stroke: currentColor;
}
</style>
