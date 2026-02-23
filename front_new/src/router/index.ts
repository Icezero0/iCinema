import { createRouter, createWebHistory } from 'vue-router'
import routes from './routes'
import { useAuthStore } from '@/stores/auth.store'

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore();

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

export default router
