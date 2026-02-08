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

  // 未登录 → 访问需要鉴权的页面
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return {
      path: "/auth/login",
      query: { redirect: to.fullPath },
    };
  }

  // 已登录 → 不允许进入 auth pages
  if (
    auth.isLoggedIn &&
    (to.path === "/auth/login" || to.path === "/auth/register")
  ) {
    return "/";
  }
});

export default router
