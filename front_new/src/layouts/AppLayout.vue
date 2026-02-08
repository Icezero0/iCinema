<script setup lang="ts">
import { ref } from 'vue'
import AppHeader from './components/AppHeader.vue'
import AppSidebar from './components/AppSidebar.vue'

const sidebarOpen = ref(false)
</script>

<template>
  <div class="app">
    <AppHeader v-model:sidebarOpen="sidebarOpen" />

    <div class="body">
      <AppSidebar :open="sidebarOpen" />
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  background: var(--c-bg);
  color: var(--c-text);
}

.body {
  display: grid;
  grid-template-columns: auto 1fr;
  min-height: calc(100vh - 56px);
}

.content {
  padding: var(--s-4);
}
</style>
