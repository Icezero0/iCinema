<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
}>();
</script>

<template>
  <div class="header">
    <h3 class="title">{{ title }}</h3>
    <span v-if="subtitle" class="subtitle">{{ subtitle }}</span>
  </div>
</template>

<style scoped>
.header {
  display: grid;
  gap: 4px;
}

.title {
  margin: 0;
  font-size: 15px;
  color: var(--c-text);
}

.subtitle {
  font-size: 12px;
  color: var(--c-text-muted);
}
</style>
