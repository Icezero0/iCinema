<script setup lang="ts">
defineProps<{ open: boolean }>()
</script>

<template>
  <aside class="sidebar" :data-open="open">
    <nav class="nav">
      <a href="/">Home</a>
      <!-- 以后加：<router-link to="/rooms">Rooms</router-link> -->
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  border-right: 1px solid var(--c-border);
  background: var(--c-surface);
  padding: var(--s-3);
  transition: width 150ms ease;
}

.sidebar[data-open="false"] {
  width: 0;
  padding: 0;
  overflow: hidden;
  border-right: none;
}

.nav {
  display: grid;
  gap: var(--s-2);
}

a {
  color: var(--c-text);
  text-decoration: none;
}
</style>
