<script setup lang="ts">
import BaseListItem from "@/ui/base/BaseListItem.vue";

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

<template>
  <BaseListItem :interactive="interactive" :dense="dense">
    <div class="lr">
      <div class="left">
        <slot name="left" />
      </div>

      <div class="content">
        <slot />
      </div>

      <div class="right">
        <slot name="right" />
      </div>
    </div>
  </BaseListItem>
</template>

<style scoped>
.lr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--s-3);
}

.left {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  min-width: 0;
}

.content {
  min-width: 0;
  flex: 1;
}

.right {
  display: inline-flex;
  align-items: center;
  gap: var(--s-2);
  flex: 0 0 auto;
}
</style>
