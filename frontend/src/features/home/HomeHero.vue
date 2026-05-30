<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
}>();
</script>

<template>
  <section class="hero">
    <div class="copy">
      <h1 class="headline">{{ title }}</h1>
      <p v-if="subtitle" class="subline">{{ subtitle }}</p>
    </div>
  </section>
</template>

<style scoped>
.hero {
  padding: 24px;
  border: 1px solid var(--c-border);
  border-radius: 20px;
  background:
    radial-gradient(120% 120% at 0% 0%, var(--auth-tint-1), transparent 52%),
    radial-gradient(120% 120% at 100% 0%, var(--auth-tint-2), transparent 46%),
    var(--c-surface);
}

.headline {
  margin: 0;
  font-size: 28px;
  line-height: 1.1;
  color: var(--c-text);
}

.subline {
  margin: 10px 0 0;
  max-width: 60ch;
  font-size: 14px;
  line-height: 1.6;
  color: var(--c-text-muted);
}
</style>
