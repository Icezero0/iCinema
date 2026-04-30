<script setup lang="ts">
defineProps<{
  title?: string
  maxWidth?: number
}>()
</script>

<template>
  <div class="page">
    <div class="container" :style="{ maxWidth: (maxWidth ?? 960) + 'px' }">
      <h1 v-if="title" class="title">{{ title }}</h1>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  padding: var(--s-4);
}
.container {
  margin: 0 auto;
}
.title {
  margin: 0 0 var(--s-3) 0;
}

@media (max-width: 800px) {
  .page {
    padding: 12px;
  }
}

@media (max-width: 520px) {
  .page {
    padding: 8px;
  }
}
</style>
