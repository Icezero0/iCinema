<template>
  <div class="page-container">
    <div class="auth-card">
      <div class="profile-header" @mouseenter="showDropdown = true" @mouseleave="showDropdown = false">
        <img :src="avatarUrl" alt="avatar" class="avatar" />
        <span class="username">{{ username }}</span>
        <transition name="dropdown-fade">
          <div v-if="showDropdown" class="dropdown-menu">
            <div class="dropdown-item" @click="goToProfile">编辑个人资料</div>
            <div class="dropdown-item" @click="logout">退出登录</div>
          </div>
        </transition>
      </div>
      <h1>欢迎来到 iCinema</h1>
      <button class="main-button" @click="$router.push('/profile')">个人信息</button>
      <button class="main-button" @click="$router.push('/room')">进入房间</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import defaultAvatar from '@/assets/default_avatar.jpg';

const username = ref('');
const avatarUrl = ref(defaultAvatar);
const showDropdown = ref(false);
const router = useRouter();
const AVATAR_CACHE_KEY = 'icinema_avatar_url';

const cachedAvatar = localStorage.getItem(AVATAR_CACHE_KEY);
if (cachedAvatar) {
  avatarUrl.value = cachedAvatar;
}

onMounted(async () => {
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    if (!accessToken) return;

    const response = await fetch('http://localhost:8000/users/me', {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });
    if (response.ok) {
      const data = await response.json();
      username.value = data.username || 'unknown_user';
      if (data.icon_path) {
        avatarUrl.value = `http://localhost:8000${data.icon_path}`;
      } else {
        avatarUrl.value = data.avatar || defaultAvatar;
      }
      // 更新缓存
      localStorage.setItem(AVATAR_CACHE_KEY, avatarUrl.value);
    }
  } catch (e) {
    alert('获取用户信息失败，请稍后再试。');
    console.error('Error fetching user info:', e);
  }
});

function goToProfile() {
  router.push('/profile');
}

function logout() {
  document.cookie = 'accesstoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
  document.cookie = 'refreshtoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
  alert('您已退出登录');
  router.push('/login');
}
</script>

<style scoped>
.page-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(to bottom, #e6f5f3, #c8e6e0);
  padding: 1rem;
}

.auth-card {
  background: white;
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
  text-align: center;
  position: relative;
}

.profile-header {
  display: flex;
  align-items: center;
  position: fixed;
  top: 2rem;
  left: 2rem;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  padding: 0.5rem 1rem;
  background: linear-gradient(120deg, #fbeee6 0%, #e6eaf5 100%);
  width: auto;
  min-width: 180px;
  z-index: 10;
  box-sizing: border-box;
  cursor: pointer;
}

.dropdown-menu {
  position: absolute;
  top: 60px;
  left: 0;
  width: 160px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  padding: 0.5rem 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.dropdown-item {
  padding: 0.75rem 1rem;
  font-size: 1rem;
  color: #333;
  cursor: pointer;
  transition: background 0.2s;
}

.dropdown-item:hover {
  background: #f0f0f0;
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid #eee;
  background: #fff;
}

.username {
  margin-left: 1rem;
  font-size: 1.1rem;
  color: #333;
  font-weight: 500;
}

h1 {
  margin-top: 3.5rem;
  margin-bottom: 2rem;
  font-size: 2rem;
  color: #007bff;
}

.main-button {
  padding: 0.75rem;
  font-size: 1rem;
  border: none;
  border-radius: 6px;
  width: 100%;
  margin-bottom: 1rem;
  background-color: #007bff;
  color: white;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.main-button:last-child {
  background-color: #28a745;
  margin-bottom: 0;
}

.main-button:hover {
  background-color: #0056b3;
}

.main-button:last-child:hover {
  background-color: #218838;
}

.dropdown-fade-enter-active, .dropdown-fade-leave-active {
  transition: all 0.2s cubic-bezier(.55,0,.1,1);
}
.dropdown-fade-enter-from, .dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px) scaleY(0.95);
}
.dropdown-fade-enter-to, .dropdown-fade-leave-from {
  opacity: 1;
  transform: translateY(0) scaleY(1);
}
</style>
