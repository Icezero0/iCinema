import { createRouter, createWebHistory } from 'vue-router';
import Login from '../views/Login.vue';
import Home from '../views/Home.vue';
import Profile from '../views/Profile.vue';
import Register from '../views/Register.vue';
import Room from '../views/Room.vue';

const routes = [
  { path: '/login', component: Login },
  { path: '/home', component: Home },
  { path: '/profile', component: Profile },
  { path: '/register', component: Register },
  { path: '/room', component: Room },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

let isTokenValid = null; // 缓存验证结果
let lastValidationTime = null; // 上次验证时间
const VALIDATION_INTERVAL = 5 * 60 * 1000; // 验证间隔时间，5分钟

router.beforeEach(async (to, from, next) => {
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];

  if (to.path === '/login' || to.path === '/register') {
    next(); // 登录页面和注册页面不需要验证
    return;
  }

  if (!accessToken) {
    isTokenValid = null; // 清除缓存
    lastValidationTime = null; // 清除验证时间
    if (to.path === '/') {
      next('/login');
    } else {
      next('/login');
    }
  } else {
    const currentTime = Date.now();
    if (isTokenValid === null || !lastValidationTime || currentTime - lastValidationTime > VALIDATION_INTERVAL) {
      try {
        const response = await fetch('http://localhost:8000/token/check', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${accessToken}`,
          },
        });

        isTokenValid = response.ok; // 缓存验证结果
        lastValidationTime = currentTime; // 更新验证时间

        if (isTokenValid) {
          if (to.path === '/') {
            next('/home');
          } else {
            next();
          }
        } else {
          next('/login');
        }
      } catch (error) {
        console.error('auth failed:', error);
        isTokenValid = false; // 缓存失败结果
        next('/login');
      }
    } else {
      if (isTokenValid) {
        if (to.path === '/') {
          next('/home');
        } else {
          next();
        }
      } else {
        next('/login');
      }
    }
  }
});

export default router;