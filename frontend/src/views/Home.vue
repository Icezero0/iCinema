<template>
  <div class="page-container">
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
    <div class="card-container">
      <!-- 大厅房间 -->
      <div class="room-card">
        <h2>大厅房间</h2>
        <div v-if="loadingPublicRooms" class="room-hint">加载中...</div>
        <div v-else-if="publicRooms.length === 0" class="room-hint">暂无大厅房间</div>
        <ul v-else class="room-list">
          <li v-for="room in publicRooms" :key="room.id" class="room-list-item">
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
          </li>
        </ul>
        <div class="pagination" v-if="publicTotal > pageSize">
          <Pagination :currentPage="publicPage" :totalPages="publicTotalPages" @update:currentPage="changePublicPage" />
        </div>
      </div>
      <!-- 我的房间 -->
      <div class="room-card">
        <h2>我的房间</h2>
        <div v-if="loadingMyRooms" class="room-hint">加载中...</div>
        <div v-else-if="myRooms.length === 0" class="room-hint">暂无我的房间</div>
        <ul v-else class="room-list">
          <li v-for="room in myRooms" :key="room.id" class="room-list-item">
            <span>{{ room.name }}
              <span v-if="room.is_active === true" style="color:green;font-size:12px;margin-left:4px;">[活跃]</span>
              <span v-else-if="room.is_active === false" style="color:gray;font-size:12px;margin-left:4px;">[关闭]</span>
            </span>
            <button @click="enterRoom(room.id)">进入</button>
          </li>
        </ul>
        <div class="pagination" v-if="myTotal > pageSize">
          <Pagination :currentPage="myPage" :totalPages="myTotalPages" @update:currentPage="changeMyPage" />
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
    <div v-if="showJoinRequestTip" class="member-invite-tip-mask">
      <div class="member-invite-tip">
        <div>{{ joinRequestTipMsg }}</div>
        <button @click="showJoinRequestTip = false">知道了</button>
      </div>
    </div>
    <div class="ws-debug">
      <h4>WebSocket调试输出</h4>
      <pre style="max-height:200px;overflow:auto;background:#f7f7f7;border-radius:6px;padding:0.5rem;">{{ wsDebugMsg }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import CustomConfirm from '@/components/CustomConfirm.vue';
import { useMyUserInfo } from '@/composables/useUserInfo.js';
import { getImageUrl, API_BASE_URL } from '@/utils/api';
import { connectWebSocket, isWebSocketConnected, getWebSocket } from '@/utils/ws';
import { checkAccessToken } from '@/utils/auth';
import { useWebSocketStatus } from '@/composables/useWebSocketStatus';
import UserAvatar from '@/components/UserAvatar.vue';
import Pagination from '@/components/Pagination.vue';

const showDropdown = ref(false);
const showLogoutConfirm = ref(false);
const router = useRouter();
const USER_CACHE_KEY = 'icinema_user';
const cachedUser = sessionStorage.getItem(USER_CACHE_KEY);
const { username, avatarUrl, email, fetchUserInfo } = useMyUserInfo();
const { wsStatus, wsDebugMsg, setupWebSocket, updateWsStatusAndDebug } = useWebSocketStatus();
const { userId } = useMyUserInfo();

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
});

onUnmounted(() => {
  closeWebSocket();
});

async function fetchPublicRooms() {
  loadingPublicRooms.value = true;
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const skip = (publicPage.value - 1) * pageSize;
    // 不加任何filter，直接查所有房间
    const res = await fetch(`${API_BASE_URL}/rooms?skip=${skip}&limit=${pageSize}`, {
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
    const res = await fetch(`${API_BASE_URL}/notifications/?skip=0&limit=1`, {
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
  // 发送websocket消息
  const ws = getWebSocket();
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'enter_room',
      payload: {
        room_id: roomId
      }
    }));
  }
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
  padding: 1rem;
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

.apply-btn {
  background: #28a745 !important;
  color: #fff !important;
  border: none !important;
  border-radius: 6px !important;
  padding: 0.3rem 1rem !important;
  cursor: pointer !important;
  font-size: 1rem !important;
  transition: background 0.2s !important;
}
.apply-btn:hover {
  background: #218838 !important;
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

.ws-debug {
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
}
</style>
