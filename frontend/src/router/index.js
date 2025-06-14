import { createRouter, createWebHistory } from 'vue-router';
import Login from '../views/Login.vue';
import Home from '../views/Home.vue';
import Profile from '../views/Profile.vue';
import Register from '../views/Register.vue';
import Room from '../views/Room.vue';
import { checkAccessToken, clearTokens } from '../utils/auth';
import { API_BASE_URL } from '../utils/api';

const routes = [
  { path: '/', redirect: '/login' }, // 根路径重定向到登录页
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
  const refreshToken = document.cookie.split('; ').find(row => row.startsWith('refreshtoken='))?.split('=')[1];

  if (to.path === '/login') {
    // 没有任何令牌，直接进入登录页
    if (!accessToken && !refreshToken) {
      isTokenValid = false;
      lastValidationTime = null;
      next();
      return;
    }
    
    // 有 accessToken 或 refreshToken，尝试验证
    try {
      // checkAccessToken 已经包含了刷新令牌的逻辑
      const valid = await checkAccessToken(accessToken);
      if (valid) {
        // 验证成功或刷新成功，跳转到主页
        isTokenValid = true;
        lastValidationTime = Date.now();
        next('/home');
        return;
      }
    } catch (error) {
      console.error('Token validation error:', error);
    }
    
    // 所有验证都失败，留在登录页
    isTokenValid = false;
    lastValidationTime = Date.now();
    next();
    return;
  }
  
  if (to.path === '/') {
    // 根路径的处理
    if (!accessToken && !refreshToken) {
      // 没有任何令牌，重定向到登录页
      next('/login');
      return;
    }
    
    // 有令牌，尝试验证
    try {
      const valid = await checkAccessToken(accessToken);
      if (valid) {
        // 令牌有效，重定向到主页
        next('/home');
        return;
      }
    } catch (error) {
      console.error('Root path token validation error:', error);
    }
    
    // 验证失败，重定向到登录页
    next('/login');
    return;
  }

  if (to.path === '/register') {
    next(); // 注册页面不需要验证
    return;
  }

  // 其他受保护页面的处理
  if (!accessToken && !refreshToken) {
    // 没有任何令牌，直接重定向到登录页
    next('/login');
    return;
  }
  
  // 有令牌，检查有效性
  const currentTime = Date.now();
  if (isTokenValid === null || !lastValidationTime || currentTime - lastValidationTime > VALIDATION_INTERVAL) {
    try {
      const valid = await checkAccessToken(accessToken);
      isTokenValid = valid;
      lastValidationTime = currentTime;
      
      if (valid) {
        next(); // 令牌有效，允许访问
      } else {
        next('/login'); // 令牌无效，重定向到登录页
      }
    } catch (error) {
      console.error('Protected route token validation error:', error);
      next('/login');
    }
  } else if (isTokenValid) {
    next(); // 使用缓存的验证结果
  } else {
    next('/login');
  }
});

export default router;