<template>  <BaseDialog
    :show="show"
    title="添加成员"
    :show-cancel="false"
    ok-text="关闭"
    @cancel="$emit('close')"
    @ok="$emit('close')"
  >
    <div class="dialog-content">
      <!-- 搜索区域 -->
      <div class="search-area">        <input 
          v-model="userSearchQuery" 
          @keyup.enter="fetchUserList" 
          placeholder="输入邮箱或用户名检索" 
          class="search-input"
          type="search"
          autocomplete="off"
        />
        <button @click="fetchUserList" class="search-btn">查询</button>
      </div>

      <!-- 用户列表 -->
      <div v-if="userListLoading" class="loading-text">加载中...</div>
      <div v-else>
        <div v-if="userList.length === 0" class="empty-text">暂无用户</div>
        <ul v-else class="user-list">
          <li v-for="user in userList" :key="user.id" class="user-item">
            <UserAvatar 
              :src="user.avatarUrl || defaultAvatar" 
              :alt="user.username" 
              :size="32" 
              class="user-item-avatar"
            />
            <span class="user-item-name">{{ user.username }}</span>
            
            <!-- 用户状态按钮 -->
            <template v-if="isUserInRoom(user.id)">
              <span class="user-status-badge in-room">已在房间</span>
            </template>
            <template v-else-if="isUserInvited(user.id)">
              <span class="user-status-badge invited">已邀请</span>
            </template>
            <template v-else>
              <button class="invite-btn" @click="inviteUser(user.id)">
                邀请
              </button>
            </template>
          </li>
        </ul>
        
        <!-- 分页 -->
        <Pagination 
          v-if="userTotal > userPageSize" 
          :currentPage="userPage" 
          :totalPages="userTotalPages" 
          @update:currentPage="onUserPageChange" 
        />
      </div>
    </div>
  </BaseDialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { API_BASE_URL, getImageUrl } from '@/utils/api';
import defaultAvatar from '@/assets/default_avatar.jpg';
import BaseDialog from '@/components/base/BaseDialog.vue';
import UserAvatar from '@/components/user/UserAvatar.vue';
import Pagination from '@/components/base/Pagination.vue';

// Props
const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  roomMembers: {
    type: Array,
    default: () => []
  },
  isOwner: {
    type: Boolean,
    default: false
  },
  roomId: {
    type: [String, Number],
    required: true
  }
});

// Emits
const emit = defineEmits(['close', 'member-added']);

// 响应式数据
const userSearchQuery = ref('');
const userList = ref([]);
const userListLoading = ref(false);
const userPage = ref(1);
const userPageSize = 10;
const userTotal = ref(0);
const invitedUserIds = ref([]);

// 计算属性
const userTotalPages = computed(() => Math.ceil(userTotal.value / userPageSize));

// 方法
function isUserInRoom(userId) {
  return props.roomMembers.some(m => m.id === userId);
}

function isUserInvited(userId) {
  return invitedUserIds.value.includes(userId);
}

async function fetchUserList() {
  userListLoading.value = true;
  const params = new URLSearchParams();
  params.append('skip', (userPage.value - 1) * userPageSize);
  params.append('limit', userPageSize);
  
  if (userSearchQuery.value) {
    if (userSearchQuery.value.includes('@')) {
      params.append('email', userSearchQuery.value);
    } else {
      params.append('username', userSearchQuery.value);
    }
  }
  
  try {
    const accessToken = document.cookie
      .split('; ')
      .find(row => row.startsWith('accesstoken='))
      ?.split('=')[1];
      
    const resp = await fetch(`${API_BASE_URL}/users?${params.toString()}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    
    if (resp.ok) {
      const data = await resp.json();
      userList.value = (data.items || []).map(u => ({
        ...u,
        avatarUrl: u.avatar_path ? getImageUrl(u.avatar_path) : ''
      }));
      userTotal.value = data.total || 0;
    } else {
      userList.value = [];
      userTotal.value = 0;
    }
  } catch (e) {
    userList.value = [];
    userTotal.value = 0;
  } finally {
    userListLoading.value = false;
  }
}

function onUserPageChange(newPage) {
  userPage.value = newPage;
  fetchUserList();
}

async function inviteUser(userId) {
  if (isUserInvited(userId)) return;
  
  const accessToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('accesstoken='))
    ?.split('=')[1];
    
  const action = props.isOwner ? 'owner_invitation' : 'member_invitation';
  
  try {
    await fetch(`${API_BASE_URL}/rooms/${props.roomId}/members`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
      body: JSON.stringify({ user_id: userId, action })
    });
    
    invitedUserIds.value.push(userId);
    emit('member-added', { userId, action });
  } catch (e) {
    console.error('邀请用户失败:', e);
  }
}

// 监听弹窗显示状态，重置数据
watch(() => props.show, (newShow) => {
  if (newShow) {
    userPage.value = 1;
    userSearchQuery.value = '';
    invitedUserIds.value = [];
    userList.value = [];
    userTotal.value = 0;
  }
});
</script>

<style scoped>
@import '@/styles/components/room/member-dialogs.css';
</style>
