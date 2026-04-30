<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth.store";
import { useNotificationsStore } from "@/stores/notifications.store";
import wsClient from "@/infra/realtime/wsClient";
import AppHeader from "./components/AppHeader.vue";
import AppSidebar from "./components/AppSidebar.vue";
import BaseMediaViewer from "@/ui/base/BaseMediaViewer.vue";
import BaseToastViewport from "@/ui/base/BaseToastViewport.vue";

const route = useRoute();
const auth = useAuthStore();
const notifications = useNotificationsStore();
const viewportWidth = ref(typeof window !== "undefined" ? window.innerWidth : 1280);
const isMobileSidebar = computed(() => viewportWidth.value < 900);
const sidebarOpen = ref(false);

let stopNotificationSubscription: (() => void) | null = null;

function handleViewportResize() {
  viewportWidth.value = window.innerWidth;
}

function closeSidebar() {
  sidebarOpen.value = false;
}

async function syncRealtimeConnection() {
  auth.syncTokensFromStorage();

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

  window.addEventListener("resize", handleViewportResize, { passive: true });
  void syncRealtimeConnection();
});

watch(
  () => [auth.isLoggedIn, auth.accessToken] as const,
  () => {
    void syncRealtimeConnection();
  },
);

watch(
  () => route.fullPath,
  () => {
    if (isMobileSidebar.value) {
      closeSidebar();
    }
  },
);

watch(isMobileSidebar, (isMobile, wasMobile) => {
  if (isMobile === wasMobile) return;
  sidebarOpen.value = false;
});

onBeforeUnmount(() => {
  stopNotificationSubscription?.();
  window.removeEventListener("resize", handleViewportResize);
  wsClient.disconnect();
});
</script>

<template>
  <div class="app">
    <AppHeader v-model:sidebarOpen="sidebarOpen" />
    <BaseMediaViewer />
    <BaseToastViewport />

    <Transition name="backdrop">
      <button
        v-if="isMobileSidebar && sidebarOpen"
        class="sidebarBackdrop"
        type="button"
        aria-label="Close navigation"
        @click="closeSidebar"
      />
    </Transition>

    <div class="body" :class="{ mobile: isMobileSidebar }">
      <AppSidebar :open="sidebarOpen" :mobile="isMobileSidebar" />
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
  isolation: isolate;
}

.body {
  display: grid;
  grid-template-columns: auto 1fr;
  min-height: calc(100dvh - 56px);
  position: relative;
}

.body.mobile {
  grid-template-columns: 1fr;
}

.content {
  padding: 0;
  min-width: 0;
  position: relative;
  z-index: 1;
}

.sidebarBackdrop {
  position: fixed;
  inset: 56px 0 0;
  border: 0;
  background: rgb(6 9 16 / 0.32);
  backdrop-filter: blur(4px);
  z-index: 35;
  cursor: pointer;
}

.backdrop-enter-active,
.backdrop-leave-active {
  transition: opacity 160ms ease;
}

.backdrop-enter-from,
.backdrop-leave-to {
  opacity: 0;
}
</style>
