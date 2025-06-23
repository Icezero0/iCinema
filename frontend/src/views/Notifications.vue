<template>
  <div class="page-container">
    <div class="notifications-card">
      <h2>我的通知</h2>
      <div v-if="loading" class="hint">加载中...</div>
      <div v-else-if="notifications.length === 0" class="hint">暂无通知</div>
      <ul v-else class="notification-list">
        <li v-for="item in notifications" :key="item.id" class="notification-item">
          <div class="sender-info-row">
            <div class="sender-info" v-if="item.sender_id">
              <img class="sender-avatar" :src="(senderInfo[item.sender_id] && senderInfo[item.sender_id].avatar) || defaultAvatar" alt="avatar" />
              <span class="sender-username">{{ senderInfo[item.sender_id]?.username || '' }}</span>
            </div>
          </div>
          <button class="delete-btn" @click="deleteNotification(item.id)">×</button>
          <div class="content">
            <template v-if="parseContent(item).type === 'owner_invitation'">
              房主邀请你加入房间 <b>{{ roomNames[parseContent(item).room_id] || ('#' + parseContent(item).room_id) }}</b>
            </template>
            <template v-else-if="parseContent(item).type === 'join_request'">
              用户 <b>{{ userNames[parseContent(item).user_id] || ('#' + parseContent(item).user_id) }}</b> 请求加入你的房间 <b>{{ roomNames[parseContent(item).room_id] || ('#' + parseContent(item).room_id) }}</b>
            </template>
            <template v-else-if="parseContent(item).type === 'member_invitation'">
              房间成员邀请你加入房间 <b>{{ roomNames[parseContent(item).room_id] || ('#' + parseContent(item).room_id) }}</b>
            </template>
            <template v-else>
              {{ item.content }}
            </template>
          </div>
          <div class="meta">
            <span class="status" :class="item.status">{{ statusText(item.status) }}</span>
            <span class="time">{{ formatTime(item.created_at) }}</span>
          </div>
          <div class="actions" v-if="['owner_invitation','join_request','member_invitation'].includes(parseContent(item).type)">
            <button class="action-btn accept" @click="respondToNotification(item.id, 'accept')">同意</button>
            <button class="action-btn reject" @click="respondToNotification(item.id, 'reject')">拒绝</button>
          </div>
        </li>
      </ul>
      <div class="pagination" v-if="total > pageSize">
        <Pagination :currentPage="page" :totalPages="totalPages" @update:currentPage="changePage" />
      </div>
      <button class="back-btn" @click="goHome">返回主页</button>
      <div v-if="showMemberInviteTip" class="member-invite-tip-mask">
        <div class="member-invite-tip">
          <div>已同意邀请，等待房主审核</div>
          <button @click="showMemberInviteTip = false">知道了</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { API_BASE_URL } from '@/utils/api';
import { useRouter } from 'vue-router';
import defaultAvatar from '@/assets/default_avatar.jpg';
import Pagination from '@/components/base/Pagination.vue';

const showMemberInviteTip = ref(false);
const router = useRouter();
const notifications = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 5;
const loading = ref(false);
const totalPages = computed(() => Math.ceil(total.value / pageSize));
const userCache = {};
const roomCache = {};
const senderInfo = ref({});

onMounted(fetchNotifications);

async function fetchNotifications() {
  loading.value = true;
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const skip = (page.value - 1) * pageSize;
    const res = await fetch(`${API_BASE_URL}/notifications?skip=${skip}&limit=${pageSize}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      notifications.value = data.items || [];
      total.value = data.total || 0;
    } else {
      notifications.value = [];
      total.value = 0;
    }
  } catch (e) {
    notifications.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

function changePage(newPage) {
  if (newPage < 1 || newPage > totalPages.value) return;
  page.value = newPage;
  fetchNotifications();
}

function statusText(status) {
  switch (status) {
    case 'unread': return '未读';
    case 'read': return '已读';
    case 'pending': return '待处理';
    case 'accepted': return '已接受';
    case 'rejected': return '已拒绝';
    default: return status;
  }
}

function formatTime(time) {
  if (!time) return '';
  // 兼容无Z结尾的UTC时间
  let d = null;
  if (typeof time === 'string' && !time.endsWith('Z') && !time.includes('+')) {
    d = new Date(time + 'Z');
  } else {
    d = new Date(time);
  }
  if (isNaN(d.getTime())) return time;
  return d.toLocaleString(undefined, { hour12: false });
}

function parseContent(item) {
  try {
    return typeof item.content === 'object' ? item.content : JSON.parse(item.content);
  } catch {
    return {};
  }
}

async function respondToNotification(id, action) {
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  const item = notifications.value.find(n => n.id === id);
  const content = parseContent(item);
  const body = { action };
  if (content.token) body.token = content.token;
  const res = await fetch(`${API_BASE_URL}/notifications/${id}/respond`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    if (content.type === 'member_invitation' && action === 'accept') {
      showMemberInviteTip.value = true;
    }
    fetchNotifications();
  } else {
    alert('操作失败');
  }
}

async function deleteNotification(id) {
  // 发送删除请求
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  const res = await fetch(`${API_BASE_URL}/notifications/${id}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${accessToken}` },
  });
  if (res.ok) {
    fetchNotifications();
  } else {
    alert('删除失败');
  }
}

function goHome() {
  router.push('/home');
}

async function getUsername(userId) {
  if (!userId) return '';
  if (userCache[userId]) return userCache[userId];
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const res = await fetch(`${API_BASE_URL}/users/${userId}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      userCache[userId] = data.username || userId;
      return userCache[userId];
    }
  } catch {}
  return userId;
}

async function getRoomName(roomId) {
  if (!roomId) return '';
  if (roomCache[roomId]) return roomCache[roomId];
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const res = await fetch(`${API_BASE_URL}/rooms/${roomId}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      roomCache[roomId] = data.name || roomId;
      return roomCache[roomId];
    }
  } catch {}
  return roomId;
}

async function getSenderInfo(userId) {
  if (!userId) return { username: '', avatar: defaultAvatar };
  if (senderInfo.value[userId]) return senderInfo.value[userId];
  try {
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    const res = await fetch(`${API_BASE_URL}/users/${userId}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      const avatar = data.avatar_path ? (data.avatar_path.startsWith('http') ? data.avatar_path : (API_BASE_URL + data.avatar_path)) : (data.avatar || defaultAvatar);
      senderInfo.value[userId] = {
        username: data.username || '',
        avatar
      };
      return senderInfo.value[userId];
    }
  } catch {}
  senderInfo.value[userId] = { username: '', avatar: defaultAvatar };
  return senderInfo.value[userId];
}

const userNames = ref({});
const roomNames = ref({});

async function preloadNames() {
  const promises = [];
  for (const item of notifications.value) {
    const content = parseContent(item);
    if (content.user_id && !userNames.value[content.user_id]) {
      promises.push(getUsername(content.user_id).then(name => userNames.value[content.user_id] = name));
    }
    if (content.room_id && !roomNames.value[content.room_id]) {
      promises.push(getRoomName(content.room_id).then(name => roomNames.value[content.room_id] = name));
    }
  }
  await Promise.all(promises);
}

async function preloadSenderInfo() {
  const promises = [];
  for (const item of notifications.value) {
    if (item.sender_id && !senderInfo.value[item.sender_id]) {
      promises.push(getSenderInfo(item.sender_id));
    }
  }
  await Promise.all(promises);
}

watch(notifications, preloadNames, { immediate: true });
watch(notifications, preloadSenderInfo, { immediate: true });
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
.notifications-card {
  background: linear-gradient(120deg, #f8fafc 0%, #e6eaf5 100%);
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(0, 80, 180, 0.08), 0 1.5px 8px rgba(0,0,0,0.04);
  padding: 2.5rem 2rem;
  min-width: 350px;
  max-width: 600px;
  width: 100%;
}
.hint {
  color: #888;
  margin-bottom: 1rem;
}
.notification-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.notification-item {
  position: relative;
  padding-top: 0.5rem;
  border-bottom: 1px solid #f0f0f0;
  padding: 1rem 0;
}
.notification-item:last-child {
  border-bottom: none;
}
.sender-info-row {
  width: 100%;
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
  position: relative;
  min-height: 36px;
}
.sender-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.sender-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  border: 1.5px solid #eee;
  background: #fff;
}
.sender-username {
  font-size: 1rem;
  color: #333;
  font-weight: 500;
}
.content {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}
.meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.95rem;
  color: #888;
}
.status.unread { color: #007bff; }
.status.read { color: #888; }
.status.pending { color: #ff9800; }
.status.accepted { color: #4caf50; }
.status.rejected { color: #f44336; }
.time { font-style: italic; }
.pagination {
  margin-top: 1.5rem;
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
.delete-btn {
  position: absolute;
  top: 0.7rem;
  right: 1rem;
  background: none;
  border: none;
  color: #bbb;
  font-size: 1.3rem;
  cursor: pointer;
  z-index: 2;
  transition: color 0.2s;
}
.delete-btn:hover {
  color: #888;
}
.actions {
  margin-top: 0.7rem;
  display: flex;
  gap: 1rem;
}
.action-btn {
  padding: 0.3rem 1.2rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}
.action-btn.accept {
  background: #4caf50;
  color: #fff;
}
.action-btn.accept:hover {
  background: #388e3c;
}
.action-btn.reject {
  background: #f44336;
  color: #fff;
}
.action-btn.reject:hover {
  background: #b71c1c;
}
.back-btn {
  display: block;
  margin: 2rem auto 0 auto;
  background: #f0f0f0;
  color: #333;
  border: none;
  border-radius: 8px;
  padding: 0.7rem 1.5rem;
  font-size: 1.1rem;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  transition: background 0.2s;
}
.back-btn:hover {
  background: #e0e0e0;
}
.member-invite-tip-mask {
  position: fixed;
  left: 0; top: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.18);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}
.member-invite-tip {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.13);
  padding: 2rem 2.5rem;
  font-size: 1.15rem;
  color: #333;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.5rem;
}
.member-invite-tip button {
  background: #007bff;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.5rem;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.2s;
}
.member-invite-tip button:hover {
  background: #0056b3;
}
</style>
