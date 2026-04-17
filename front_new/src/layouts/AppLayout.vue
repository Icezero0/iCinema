<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useAuthStore } from "@/stores/auth.store";
import { useNotificationsStore } from "@/stores/notifications.store";
import wsClient from "@/infra/realtime/wsClient";
import AppHeader from "./components/AppHeader.vue";
import AppSidebar from "./components/AppSidebar.vue";

const sidebarOpen = ref(false);
const auth = useAuthStore();
const notifications = useNotificationsStore();

let stopNotificationSubscription: (() => void) | null = null;

async function syncRealtimeConnection() {
  if (auth.isLoggedIn && auth.accessToken) {
    try {
      await wsClient.connect(auth.accessToken);
    } catch (error) {
      console.error("Failed to initialize realtime connection", error);
    }
    return;
  }

  wsClient.disconnect();
}

onMounted(() => {
  stopNotificationSubscription = wsClient.onEvent("notification", () => {
    void notifications.fetchUnreadCount();
  });

  void syncRealtimeConnection();
});

watch(
  () => [auth.isLoggedIn, auth.accessToken] as const,
  () => {
    void syncRealtimeConnection();
  },
);

onBeforeUnmount(() => {
  stopNotificationSubscription?.();
  wsClient.disconnect();
});
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
  min-height: 100dvh;
  background: var(--c-bg);
  color: var(--c-text);
}

.body {
  display: grid;
  grid-template-columns: auto 1fr;
  min-height: calc(100dvh - 56px);
}

.content {
  padding: 0;
}
</style>
