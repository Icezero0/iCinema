<template>
  <div class="page-container" :class="{ 'mobile-layout': isMobile }">
    <!-- 移动端顶部导航栏 -->
    <div v-if="isMobile" class="mobile-header">
      <div class="mobile-user-info">
        <UserAvatar :src="avatarUrl" :alt="username" size="32" class="mobile-avatar" />
        <span class="mobile-username">{{ username }}</span>
      </div>      <div class="mobile-actions">
        <div class="ws-status mobile-ws-status" :class="wsStatus">
          <span v-if="wsStatus === 'connected'">🟢 已连接</span>
          <span v-else-if="wsStatus === 'connecting'">🟡 正在连接</span>
          <span v-else>🔴 未连接</span>
        </div>
        <button class="mobile-notification-btn" @click="goToNotifications">
          通知<span v-if="notificationCount > 0" class="notification-badge">{{ notificationCount }}</span>
        </button>
        <button class="mobile-menu-btn" @click="showDropdown = !showDropdown">⋮</button>
      </div>
    </div>

    <!-- 桌面端原有布局 -->
    <template v-if="!isMobile">
      <button class="notification-btn" @click="goToNotifications">
        通知<span v-if="notificationCount > 0" class="notification-badge">{{ notificationCount }}</span>
      </button>
      <div class="profile-header" @mouseenter="showDropdown = true" @mouseleave="showDropdown = false">
        <UserAvatar :src="avatarUrl" :alt="username" size="38" class="avatar" />
        <span class="username">{{ username }}</span>
        <transition name="dropdown-fade">
          <div v-if="showDropdown" class="dropdown-menu">
            <div class="dropdown-item" @click="goToProfile">编辑个人资料</div>
            <div class="dropdown-item" @click="logout">退出登录</div>
          </div>
        </transition>
      </div>
      <div class="ws-status" :class="wsStatus">
        <span v-if="wsStatus === 'connected'">🟢 已连接</span>
        <span v-else-if="wsStatus === 'connecting'">🟡 正在连接...</span>
        <span v-else>🔴 未连接</span>
      </div>
    </template>

    <!-- 移动端下拉菜单 -->
    <div v-if="isMobile && showDropdown" class="mobile-dropdown-overlay" @click="showDropdown = false">
      <div class="mobile-dropdown-menu" @click.stop>
        <div class="mobile-dropdown-item" @click="goToProfile">
          <span>编辑个人资料</span>
        </div>
        <div class="mobile-dropdown-item" @click="logout">
          <span>退出登录</span>
        </div>
      </div>
    </div>    <div class="card-container" :class="{ 'mobile-card-container': isMobile }">
      <!-- 我的房间 -->
      <div class="room-card" :class="{ 'mobile-room-card': isMobile }">
        <button 
          class="create-room-btn-float" 
          :class="{ 'mobile-create-btn': isMobile }"
          @click="showCreateRoomDialog = true" 
          title="创建房间"
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="12" fill="#1976d2"/>
            <path d="M12 7V17" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
            <path d="M7 12H17" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
        <div class="my-room-header">
          <h2 class="room-title">我的房间</h2>
        </div>
        <div v-if="loadingMyRooms" class="room-hint">加载中...</div>
        <div v-else-if="myRooms.length === 0" class="room-hint">暂无我的房间</div>
        <ul v-else class="room-list">
          <li v-for="room in myRooms" :key="room.id" class="room-list-item" :class="{ 'mobile-room-item': isMobile }">
            <!-- PC端显示方式 -->
            <template v-if="!isMobile">
              <span>{{ room.name }}
                <span v-if="room.is_active === true" style="color:green;font-size:12px;margin-left:4px;">[活跃]</span>
                <span v-else-if="room.is_active === false" style="color:gray;font-size:12px;margin-left:4px;">[关闭]</span>
              </span>
              <button @click="enterRoom(room.id)">进入</button>
            </template>            <!-- 移动端显示方式 -->
            <template v-else>
              <div class="room-info">
                <span class="room-name">{{ room.name }}</span>
                <span v-if="room.is_active === true" class="room-status active">[活跃]</span>
                <span v-else-if="room.is_active === false" class="room-status inactive">[关闭]</span>
              </div>
              <button @click="enterRoom(room.id)" class="room-action-btn primary">进入</button>
            </template>
          </li>
        </ul>
        <div class="pagination" v-if="myTotal > pageSize">
          <Pagination :currentPage="myPage" :totalPages="myTotalPages" @update:currentPage="changeMyPage" />
        </div>
      </div>
      
      <!-- 大厅房间 -->
      <div class="room-card" :class="{ 'mobile-room-card': isMobile }">
        <h2 class="room-title">大厅房间</h2>
        <div v-if="loadingPublicRooms" class="room-hint">加载中...</div>
        <div v-else-if="publicRooms.length === 0" class="room-hint">暂无大厅房间</div>
        <ul v-else class="room-list">
          <li v-for="room in publicRooms" :key="room.id" class="room-list-item" :class="{ 'mobile-room-item': isMobile }">
            <!-- PC端显示方式 -->
            <template v-if="!isMobile">
              <span>{{ room.name }}
                <span v-if="room.is_active === true" style="color:green;font-size:12px;margin-left:4px;">[活跃]</span>
                <span v-else-if="room.is_active === false" style="color:gray;font-size:12px;margin-left:4px;">[关闭]</span>
              </span>
              <button
                v-if="myRoomIds.includes(room.id)"
                @click="enterRoom(room.id)"
              >进入</button>
              <button
                v-else
                @click="applyToJoin(room.id)"
                class="apply-btn"
              >申请加入</button>
            </template>            <!-- 移动端显示方式 -->
            <template v-else>
              <div class="room-info">
                <span class="room-name">{{ room.name }}</span>
                <span v-if="room.is_active === true" class="room-status active">[活跃]</span>
                <span v-else-if="room.is_active === false" class="room-status inactive">[关闭]</span>
              </div>
              <button
                v-if="myRoomIds.includes(room.id)"
                @click="enterRoom(room.id)"
                class="room-action-btn primary"
              >进入</button>
              <button
                v-else
                @click="applyToJoin(room.id)"
                class="room-action-btn secondary"
              >申请加入</button>
            </template>
          </li>
        </ul>
        <div class="pagination" v-if="publicTotal > pageSize">
          <Pagination :currentPage="publicPage" :totalPages="publicTotalPages" @update:currentPage="changePublicPage" />
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
    <!-- 创建房间对话框复用 -->
    <BaseDialog
      :show="showCreateRoomDialog"
      title="创建房间"
      @ok="handleCreateRoomOk"
      @cancel="() => showCreateRoomDialog = false"
    >
      <RoomForm v-model="createRoomForm" />
    </BaseDialog>
    <div v-if="showJoinRequestTip" class="member-invite-tip-mask">
      <div class="member-invite-tip">
        <div>{{ joinRequestTipMsg }}</div>
        <button @click="showJoinRequestTip = false">知道了</button>
      </div>
    </div>
    <!-- <div class="ws-debug">
      <h4>WebSocket调试输出</h4>
      <pre style="max-height:200px;overflow:auto;background:#f7f7f7;border-radius:6px;padding:0.5rem;">{{ wsDebugMsg }}</pre>
    </div> -->
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import CustomConfirm from '@/components/base/CustomConfirm.vue';
import { useMyUserInfo } from '@/composables/useUserInfo.js';
import { getImageUrl, API_BASE_URL } from '@/utils/api';
import { connectWebSocket, isWebSocketConnected, getWebSocket } from '@/utils/ws';
import { checkAccessToken } from '@/utils/auth';
import { useWebSocketStatus } from '@/composables/useWebSocketStatus';
import { useResponsive } from '@/composables/useResponsive';
import UserAvatar from '@/components/user/UserAvatar.vue';
import Pagination from '@/components/base/Pagination.vue';
import BaseDialog from '@/components/base/BaseDialog.vue';
import RoomForm from '@/components/room/RoomForm.vue';

const showDropdown = ref(false);
const showLogoutConfirm = ref(false);
const router = useRouter();
const USER_CACHE_KEY = 'icinema_user';
const cachedUser = sessionStorage.getItem(USER_CACHE_KEY);
const { username, avatarUrl, email, fetchUserInfo } = useMyUserInfo();
const { wsStatus, wsDebugMsg, setupWebSocket, updateWsStatusAndDebug } = useWebSocketStatus();
const { userId } = useMyUserInfo();

// 响应式检测
const { isMobile, deviceType } = useResponsive();

// 分页相关
const pageSize = 10;
// 大厅房间
const publicRooms = ref([]);
const publicTotal = ref(0);
const publicPage = ref(1);
const loadingPublicRooms = ref(false);
const publicTotalPages = computed(() => Math.ceil(publicTotal.value / pageSize));
// 我的房间
const myRooms = ref([]);
const myTotal = ref(0);
const myPage = ref(1);
const loadingMyRooms = ref(false);
const myTotalPages = computed(() => Math.ceil(myTotal.value / pageSize));
// 通知数量
const notificationCount = ref(0);
const showJoinRequestTip = ref(false);
const joinRequestTipMsg = ref('');
const myRoomIds = ref([]);
const showCreateRoomDialog = ref(false);
const newRoomName = ref("");
const createRoomForm = ref({ name: '', isPublic: true });
watch(showCreateRoomDialog, (v) => {
  if (v) {
    createRoomForm.value.name = `${username.value} 的房间`;
    createRoomForm.value.isPublic = true;
  }
});
async function handleCreateRoomOk() {
  // 获取表单数据
  const { name, isPublic } = createRoomForm.value;
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  if (!accessToken) {
    alert('未登录或登录已过期，请重新登录');
    return;
  }
  try {
    const resp = await fetch(`${API_BASE_URL}/rooms`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({
        name,
        is_public: isPublic,
        // config:
      })
    });
    if (resp.ok) {
      showCreateRoomDialog.value = false;
      await fetchMyRooms(); // 刷新房间列表
    } else {
      const data = await resp.json();
      alert(data.detail || '创建房间失败');
    }
  } catch (e) {
    alert('网络错误，创建房间失败');
  }
}

let heartbeatTimer = null;
let reconnectTimer = null;

function closeWebSocket() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

if (cachedUser) {
  try {
    const userObj = JSON.parse(cachedUser);
    if (userObj.avatar_path) {
      avatarUrl.value = getImageUrl(userObj.avatar_path);
    } else if (userObj.avatar) {
      avatarUrl.value = userObj.avatar;
    }
    if (userObj.username) {
      username.value = userObj.username;
    }
    if (userObj.email) {
      email.value = userObj.email;
    }
  } catch (e) {}
}

onMounted(async () => {
  if (!cachedUser) {
    await fetchUserInfo();
  }
  await fetchMyRoomIds();
  await fetchPublicRooms();
  await fetchMyRooms();
  await fetchNotificationCount();
  setupWebSocket();

  const ws = getWebSocket && getWebSocket();
  if (ws) {
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'receive_notification' && router.currentRoute.value.path === '/home') {
        notificationCount.value += 1;
      }
    };
  }
});

onUnmounted(() => {
  closeWebSocket();
});

async function fetchPublicRooms() {
  loadingPublicRooms.value = true;
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const skip = (publicPage.value - 1) * pageSize;
    const res = await fetch(`${API_BASE_URL}/rooms?skip=${skip}&limit=${pageSize}&is_public=true`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      publicRooms.value = data.items || data || [];
      publicTotal.value = data.total || (data.items ? data.items.length : 0);
    } else {
      publicRooms.value = [];
      publicTotal.value = 0;
    }
  } catch (e) {
    publicRooms.value = [];
    publicTotal.value = 0;
  } finally {
    loadingPublicRooms.value = false;
  }
}

async function fetchMyRooms() {
  loadingMyRooms.value = true;
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const skip = (myPage.value - 1) * pageSize;
    if (!userId.value) {
      myRooms.value = [];
      myTotal.value = 0;
      return;
    }
    const res = await fetch(`${API_BASE_URL}/users/${userId.value}/rooms?skip=${skip}&limit=${pageSize}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      myRooms.value = data.items || [];
      myTotal.value = data.total || 0;
    } else {
      myRooms.value = [];
      myTotal.value = 0;
    }
  } catch (e) {
    myRooms.value = [];
    myTotal.value = 0;
  } finally {
    loadingMyRooms.value = false;
  }
}

async function fetchMyRoomIds() {
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const res = await fetch(`${API_BASE_URL}/users/me/room_ids`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });
    if (res.ok) {
      myRoomIds.value = await res.json();
    } else {
      myRoomIds.value = [];
    }
  } catch (e) {
    myRoomIds.value = [];
  }
}

async function fetchNotificationCount() {
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const res = await fetch(`${API_BASE_URL}/notifications?skip=0&limit=1`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      notificationCount.value = data.total || 0;
    } else {
      notificationCount.value = 0;
    }
  } catch (e) {
    notificationCount.value = 0;
  }
}

function changePublicPage(page) {
  if (page < 1 || page > publicTotalPages.value) return;
  publicPage.value = page;
  fetchPublicRooms();
}
function changeMyPage(page) {
  if (page < 1 || page > myTotalPages.value) return;
  myPage.value = page;
  fetchMyRooms();
}
function enterRoom(roomId) {
  router.push({ path: '/room', query: { id: roomId } });
}
function goToProfile() {
  router.push('/profile');
}
function logout() {
  showLogoutConfirm.value = true;
}
function handleLogoutConfirm() {
  document.cookie = 'accesstoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
  document.cookie = 'refreshtoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
  sessionStorage.removeItem('icinema_user'); // 清除用户信息缓存
  showLogoutConfirm.value = false;
  router.push('/login');
}
function handleLogoutCancel() {
  showLogoutConfirm.value = false;
}
function goToNotifications() {
  router.push('/notifications');
}
function applyToJoin(roomId) {
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  if (!userId.value) {
    joinRequestTipMsg.value = '无法获取用户ID，请重新登录';
    showJoinRequestTip.value = true;
    return;
  }
  fetch(`${API_BASE_URL}/rooms/${roomId}/members`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ action: 'join_request', user_id: userId.value }),
  })
    .then(res => res.json().then(data => ({ ok: res.ok, data })))
    .then(({ ok, data }) => {
      if (ok) {
        joinRequestTipMsg.value = '已提交申请，等待房主审核';
      } else {
        joinRequestTipMsg.value = data.detail || '申请失败';
      }
      showJoinRequestTip.value = true;
    })
    .catch(() => {
      joinRequestTipMsg.value = '网络错误，申请失败';
      showJoinRequestTip.value = true;
    });
}
</script>

<style scoped>
.page-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(to bottom, #e6f5f3, #c8e6e0);
  padding: var(--spacing-md);
}

.profile-header {
  display: flex;
  align-items: center;
  position: fixed;
  top: 2rem;
  left: 2rem;
  border: 2px solid var(--color-border);
  border-radius: 12px;
  padding: 0.5rem 1rem;
  background: linear-gradient(120deg, #fbeee6 0%, #e6eaf5 100%);
  width: auto;
  min-width: 180px;
  z-index: 10;
  box-sizing: border-box;
  cursor: pointer;
}

.notification-btn {
  position: fixed;
  top: 2rem;
  right: 2rem;
  background: #007bff;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0.7rem 1.5rem;
  font-size: 1.1rem;
  cursor: pointer;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  transition: background 0.2s;
}
.notification-btn:hover {
  background: #0056b3;
}
.notification-badge {
  display: inline-block;
  background: #f44336;
  color: #fff;
  border-radius: 50%;
  font-size: 0.9rem;
  min-width: 1.6em;
  height: 1.6em;
  line-height: 1.6em;
  text-align: center;
  margin-left: 0.5em;
  vertical-align: middle;
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
  margin: 10px 6vw 2rem 6vw; /* 上边距100px，左右6vw，底部2rem */
  width: 100%;
  height: auto;
  min-height: 0;
  position: relative;
  top: 0;
}

.room-card {
  position: relative;
  background: linear-gradient(120deg, #f8fafc 0%, #e6eaf5 100%); /* 卡片淡色渐变 */
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(0, 80, 180, 0.08), 0 1.5px 8px rgba(0,0,0,0.04);
  padding: 2.5rem 2rem 1.2rem 2rem;
  flex: 1 1 0;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
}

.room-card:first-child {
  margin-left: 6vw;
}

.room-card:last-child {
  margin-right: 6vw;
}

.room-card h2 {
  font-size: 1.5rem;
  color: #007bff;
  margin-bottom: 1.5rem;
}

.room-list {
  list-style: none;
  padding: 0;
  margin: 0;
  width: 100%;
}

.room-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f0f0f0;
}

.room-list-item:last-child {
  border-bottom: none;
}

.room-list-item button {
  background: #007bff;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.3rem 1rem;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.room-list-item button:hover {
  background: #0056b3;
}

.room-list-item button.secondary {
  background: #28a745;
}

.room-list-item button.secondary:hover {
  background: #218838;
}

/* Legacy apply-btn class for backward compatibility */
.apply-btn {
  background: #28a745 !important;
  color: #fff !important;
}

.room-hint {
  color: #888;
  margin-bottom: 1rem;
}

.pagination {
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  justify-content: center;
}

.pagination button {
  background: #f0f0f0;
  border: none;
  border-radius: 6px;
  padding: 0.3rem 1rem;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.pagination button:disabled {
  background: #e0e0e0;
  color: #aaa;
  cursor: not-allowed;
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

.member-invite-tip-mask {
  position: fixed;
  left: 0;
  top: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0,0,0,0.18);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}
.member-invite-tip {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.13);
  padding: 2.2rem 2.5rem 1.5rem 2.5rem;
  min-width: 260px;
  text-align: center;
  font-size: 1.15rem;
  color: #333;
}
.member-invite-tip button {
  margin-top: 1.2rem;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.4rem 1.5rem;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}
.member-invite-tip button:hover {
  background: #115293;
}

.ws-status {
  position: fixed;
  top: 2rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.9);
  color: #333;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.ws-status {
  margin-top: 0.5rem;
  font-size: 1rem;
  text-align: left;
  margin-left: 1.5rem;
}
.ws-status.connected {
  color: #4caf50;
}
.ws-status.connecting {
  color: #ff9800;
}
.ws-status.disconnected {
  color: #f44336;
}

/* Mobile Responsive Styles */
@media (max-width: 768px) {
  /* 确保页面顶部没有额外间距 */
  body {
    margin: 0 !important;
    padding: 0 !important;
  }
  
  #app {
    margin: 0 !important;
    padding: 0 !important;
  }
  .page-container.mobile-layout {
    flex-direction: column;
    align-items: stretch;
    justify-content: flex-start !important;
    padding: 0 !important;
    margin: 0 !important;
    min-height: 100vh;
    height: auto;
    background: linear-gradient(to bottom, #e6f5f3, #c8e6e0);
    position: relative;
  }/* Mobile Header */
  .mobile-header {
    position: sticky;
    top: 0;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
    padding: 16px 16px 16px 16px;
    padding-top: max(16px, env(safe-area-inset-top));
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 100;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    margin: 0;
  }

  .mobile-user-info {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .mobile-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid #eee;
  }

  .mobile-username {
    font-size: 1rem;
    font-weight: 500;
    color: #333;
  }

  .mobile-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .mobile-ws-status {
    position: static;
    transform: none;
    background: transparent;
    border: none;
    padding: 4px 8px;
    font-size: 0.8rem;
    box-shadow: none;
    margin: 0;
    white-space: nowrap;
  }

  .mobile-notification-btn {
    background: #007bff;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 0.9rem;
    cursor: pointer;
    min-height: var(--mobile-touch-target);
  }

  .mobile-menu-btn {
    background: #f8f9fa;
    color: #333;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 1.2rem;
    cursor: pointer;
    min-height: var(--mobile-touch-target);
    min-width: var(--mobile-touch-target);
  }

  /* Mobile Dropdown */
  .mobile-dropdown-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 200;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 80px;
  }

  .mobile-dropdown-menu {
    background: #fff;
    border-radius: var(--mobile-border-radius);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    padding: 8px 0;
    min-width: 200px;
    max-width: 90vw;
  }

  .mobile-dropdown-item {
    padding: 16px 20px;
    font-size: 1rem;
    color: #333;
    cursor: pointer;
    border-bottom: 1px solid #f0f0f0;
    min-height: var(--mobile-touch-target);
    display: flex;
    align-items: center;
  }

  .mobile-dropdown-item:last-child {
    border-bottom: none;
  }

  .mobile-dropdown-item:active {
    background: #f8f9fa;
  }  /* Mobile Card Container */
  .mobile-card-container {
    flex-direction: column;
    gap: var(--mobile-padding);
    margin: 0;
    padding: var(--mobile-padding);
    width: 100%;
    align-items: center;
    justify-content: flex-start;
    box-sizing: border-box;
  }  .mobile-room-card {
    margin: 0 !important; /* 强制覆盖PC端的边距设置 */
    padding: var(--mobile-padding);
    min-width: 0;
    flex: none;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
  }

  /* 确保移动端卡片没有任何额外的边距 */
  .page-container.mobile-layout .room-card:first-child,
  .page-container.mobile-layout .room-card:last-child {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .mobile-room-card .room-title {
    font-size: 1.25rem;
    margin-bottom: 1rem;
  }
  /* Mobile Room Items */
  .mobile-room-item {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px var(--mobile-padding);
    border: 1px solid #f0f0f0;
    border-radius: var(--mobile-border-radius);
    margin-bottom: 8px;
    background: rgba(255, 255, 255, 0.8);
  }

  .mobile-room-item:last-child {
    border-bottom: 1px solid #f0f0f0;
    margin-bottom: 0;
  }

  .room-info {
    display: flex;
    align-items: center;
    gap: 8px;
    flex: 1;
    overflow: hidden;
  }

  .room-name {
    font-weight: 500;
    font-size: 1rem;
    color: #333;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 1;
  }

  .room-status {
    font-size: 0.8rem;
    font-weight: normal;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .room-status.active {
    color: #28a745;
  }

  .room-status.inactive {
    color: #6c757d;
  }

  .room-action-btn {
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 0.9rem;
    cursor: pointer;
    min-height: 36px;
    font-weight: 500;
    transition: all 0.2s ease;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .room-action-btn.primary {
    background: #007bff;
    color: #fff;
  }

  .room-action-btn.primary:active {
    background: #0056b3;
  }

  .room-action-btn.secondary {
    background: #28a745;
    color: #fff;
  }

  .room-action-btn.secondary:active {
    background: #218838;
  }

  /* Mobile Create Button */
  .mobile-create-btn {
    position: static;
    margin-bottom: 1rem;
    align-self: center;
  }

  /* Hide desktop elements on mobile */
  .profile-header,
  .notification-btn,
  .ws-status:not(.mobile-ws-status) {
    display: none;
  }
}

/* Desktop-only elements should be hidden on mobile */
@media (max-width: 768px) {
  .desktop-only {
    display: none !important;
  }
}

/* .ws-debug {
  margin-top: 2rem;
  padding: 1rem;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;
}
.ws-debug h4 {
  font-size: 1.2rem;
  color: #333;
  margin-bottom: 0.8rem;
} */

.room-title {
  flex: 1;
  text-align: center;
  font-size: 1.5rem;
  font-weight: 600;
  margin: 0;
  line-height: 2.2rem;
}
.create-room-btn-float {
  position: absolute;
  top: 12px;
  right: 18px;
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  outline: none;
  transition: background 0.2s;
  z-index: 2;
}
.create-room-btn-float svg {
  display: block;
}
.create-room-btn-float:hover svg circle {
  fill: #1256a2;
}
.create-room-btn-float:active svg circle {
  fill: #0d3c7b;
}
</style>
