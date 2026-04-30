import { createRouter, createWebHistory } from 'vue-router'
import routes from './routes'
import { useAuthStore } from '@/stores/auth.store'

const INITIAL_ROOM_ENTRY_KEY = "icinema:initial-room-entry";

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from) => {
  const auth = useAuthStore();
  const isInitialNavigation = from.matched.length === 0;
  const isInitialRoomEntry = isInitialNavigation && to.name === "room";
  const pendingInitialRoomEntry = sessionStorage.getItem(INITIAL_ROOM_ENTRY_KEY);

  if (isInitialRoomEntry) {
    sessionStorage.setItem(INITIAL_ROOM_ENTRY_KEY, to.fullPath);
  }

  if (to.name === "room") {
    to.meta.requiresSyncGate = isInitialRoomEntry || pendingInitialRoomEntry === to.fullPath;
  }

  if (auth.status === "unknown") {
    await auth.init();
  }


  if (to.matched.some(record => record.meta.requiresAuth) && !auth.isLoggedIn) {
    return {
      path: "/auth/login",
      query: { redirect: to.fullPath },
    };
  }

  if (
    auth.isLoggedIn &&
    (to.path === "/auth/login" || to.path === "/auth/register")
  ) {
    return "/";
  }
});

router.afterEach((to) => {
  if (to.name === "room") {
    sessionStorage.removeItem(INITIAL_ROOM_ENTRY_KEY);
  }
});

export default router
