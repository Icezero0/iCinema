<template>
  <div class="page-container">
    <div class="home-card">
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
      <div class="card-container">
        <div class="room-card">
          <h2>大厅房间</h2>
          <!-- 可添加大厅房间内容或入口按钮 -->
        </div>
        <div class="room-card">
          <h2>我的房间</h2>
          <!-- 可添加我的房间内容或入口按钮 -->
        </div>
      </div>
    </div>
    <CustomConfirm
      :show="showLogoutConfirm"
      title="确认退出登录"
      content="确定要退出登录吗？"
      @ok="handleLogoutConfirm"
      @cancel="handleLogoutCancel"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import defaultAvatar from '@/assets/default_avatar.jpg';
import CustomConfirm from '@/components/CustomConfirm.vue';
import { useUserInfo } from '@/composables/useUserInfo.js';

const showDropdown = ref(false);
const showLogoutConfirm = ref(false);
const router = useRouter();
const USER_CACHE_KEY = 'icinema_user';
const { username, avatarUrl, email, fetchUserInfo } = useUserInfo();

// 初始化时优先从localStorage读取缓存用户信息
const cachedUser = localStorage.getItem(USER_CACHE_KEY);
if (cachedUser) {
  try {
    const userObj = JSON.parse(cachedUser);
    if (userObj.avatar_path) {
      avatarUrl.value = `http://localhost:8000${userObj.avatar_path}`;
    } else if (userObj.avatar) {
      avatarUrl.value = userObj.avatar;
    }
    if (userObj.username) {
      username.value = userObj.username;
    }
    if (userObj.email) {
      email.value = userObj.email;
    }
  } catch (e) {
    // ignore parse error
  }
}

onMounted(async () => {
  // 如果localStorage有缓存，则不请求后端
  if (cachedUser) {
    return;
  }
  await fetchUserInfo();
});

function goToProfile() {
  router.push('/profile');
}

function logout() {
  showLogoutConfirm.value = true;
}

function handleLogoutConfirm() {
  document.cookie = 'accesstoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
  document.cookie = 'refreshtoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
  showLogoutConfirm.value = false;
  router.push('/login');
}

function handleLogoutCancel() {
  showLogoutConfirm.value = false;
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

.home-card {
  background: white;
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  width: 80%;
  height: 80%;
  max-width: none;
  text-align: center;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 500px;
  box-sizing: border-box;
  flex: 1 1 auto;
  margin-top: 10vh;
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

.card-container {
  display: flex;
  flex-direction: row;
  gap: 2rem;
  justify-content: center;
  align-items: flex-start;
  width: 100%;
  margin: 3rem;
  position: relative;
  top: 0;
}

.room-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
  padding: 2.5rem 2rem;
  flex: 1 1 0;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
}

.room-card h2 {
  font-size: 1.5rem;
  color: #007bff;
  margin-bottom: 1.5rem;
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
