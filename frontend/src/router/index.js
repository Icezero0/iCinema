import { createRouter, createWebHistory } from 'vue-router';
import Login from '../views/Login.vue';
import Home from '../views/Home.vue';
import Profile from '../views/Profile.vue';
import Register from '../views/Register.vue';
import Room from '../views/Room.vue';
import { checkAccessToken, clearTokens } from '../utils/auth';

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

  if (to.path === '/login') {
    if (!accessToken) {
      isTokenValid = null;
      lastValidationTime = null;
      next(); // 没有token，正常进入登录页
      return;
    }
    try {
      const valid = await checkAccessToken(accessToken);
      if (valid) {
        isTokenValid = true;
        lastValidationTime = Date.now();
        next('/home'); // token有效，跳转主页
      } else {
        isTokenValid = false;
        lastValidationTime = Date.now();
        next(); // token无效，留在登录页
      }
    } catch (error) {
      isTokenValid = false;
      lastValidationTime = Date.now();
      next(); // 验证异常，留在登录页
    }
    return;
  }

  if (to.path === '/register') {
    next(); // 注册页面不需要验证
    return;
  }

  if (!accessToken) {
    isTokenValid = null;
    lastValidationTime = null;
    if (to.path === '/') {
      next('/login');
    } else {
      next('/login');
    }
  } else {
    const currentTime = Date.now();
    if (isTokenValid === null || !lastValidationTime || currentTime - lastValidationTime > VALIDATION_INTERVAL) {
      try {
        const valid = await checkAccessToken(accessToken);
        isTokenValid = valid;
        lastValidationTime = currentTime;

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
        isTokenValid = false;
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