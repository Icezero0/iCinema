<template>
  <div v-if="isOwner" class="user-video-status card" :class="{ 'dark-mode': isDarkMode, 'mobile-mode': isMobile }">
    <h4>用户视频状态</h4>
    <div class="status-content">
      <div v-if="userStatuses.length === 0" class="empty-state">
        <span class="empty-text">暂无在线用户</span>
      </div>
      <div v-else class="user-list">
        <div 
          v-for="userStatus in userStatuses" 
          :key="userStatus.userId"
          class="user-status-item"
          :class="userStatus.status"
        >
          <div class="user-info">
            <div class="user-avatar">
              <img 
                :src="userStatus.avatar || '/src/assets/default_avatar.jpg'" 
                :alt="userStatus.username"
                @error="handleAvatarError"
              />
            </div>
            <div class="user-name">{{ userStatus.username || `用户${userStatus.userId}` }}</div>
          </div>
          <div class="status-info">
            <div class="status-indicator" :class="userStatus.status">
              <div v-if="userStatus.status === 'loading'" class="status-icon loading">
                <div class="mini-spinner"></div>
              </div>
              <div v-else-if="userStatus.status === 'ready'" class="status-icon ready">✓</div>
              <div v-else-if="userStatus.status === 'error'" class="status-icon error">⚠</div>
              <div v-else class="status-icon unknown">?</div>
            </div>
            <div class="status-text">{{ getStatusText(userStatus.status) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

// Props
const props = defineProps({
  isOwner: {
    type: Boolean,
    required: true
  },
  roomId: {
    type: [String, Number],
    required: true
  },
  isDarkMode: {
    type: Boolean,
    default: false
  },
  isMobile: {
    type: Boolean,
    default: false
  },
  wsConnection: {
    type: Object,
    default: null
  },
  roomMembers: {
    type: Array,
    default: () => []
  },
  userId: {
    type: [String, Number],
    required: true
  }
});

// Data
const userStatuses = ref([]);

// Computed
const getStatusText = (status) => {
  switch (status) {
    case 'loading':
      return '加载中';
    case 'ready':
      return '就绪';
    case 'error':
      return '错误';
    default:
      return '未知';
  }
};

// Methods
const handleAvatarError = (event) => {
  event.target.src = '/src/assets/default_avatar.jpg';
};

const handleVideoStatusMessage = (message) => {
  if (message.type === 'user_video_status') {
    const { user_id, status, room_id, userInfo } = message.payload;
    
    console.log('收到用户视频状态消息:', message.payload);
    
    // 只处理当前房间的状态消息
    if (room_id == props.roomId) {
      // 跳过房主自己的状态消息
      if (user_id == props.userId) {
        console.log('跳过房主自己的状态消息:', user_id);
        return;
      }
      
      // 查找现有用户状态
      const existingUserIndex = userStatuses.value.findIndex(user => user.userId === user_id);
      
      if (existingUserIndex !== -1) {
        // 更新现有用户状态
        userStatuses.value[existingUserIndex].status = status;
        userStatuses.value[existingUserIndex].lastUpdate = new Date();
        console.log('更新现有用户状态:', user_id, status);
      } else {
        // 使用Room.vue传递的用户信息，或从roomMembers中查找作为备用
        const username = userInfo?.username || props.roomMembers.find(member => member.id === user_id)?.username || `用户${user_id}`;
        const avatar = userInfo?.avatar || props.roomMembers.find(member => member.id === user_id)?.avatar || null;
        
        const newUser = {
          userId: user_id,
          username: username,
          avatar: avatar,
          status: status,
          lastUpdate: new Date()
        };
        
        userStatuses.value.push(newUser);
        console.log('添加新用户状态:', newUser);
      }
    }
  }
};

const setupWebSocketListener = () => {
  // WebSocket监听器将在Room.vue中统一处理
  console.log('UserVideoStatus组件已准备就绪，等待来自Room.vue的消息');
};

// 监听wsConnection的变化
// 移除WebSocket监听，改为通过Room.vue统一处理

const initializeUserStatuses = (onlineUsers) => {
  if (!onlineUsers || !Array.isArray(onlineUsers)) {
    return;
  }
  
  // 清空现有状态
  userStatuses.value = [];
  
  // 根据后端返回的在线用户数据初始化状态，过滤掉房主自己
  for (const userInfo of onlineUsers) {
    const { user_id, video_status, userInfo: detailedUserInfo } = userInfo;
    
    // 跳过房主自己
    if (user_id == props.userId) {
      continue;
    }
    
    // 使用Room.vue获取的详细用户信息，或从roomMembers中查找作为备用
    const username = detailedUserInfo?.username || props.roomMembers.find(member => member.id === user_id)?.username || `用户${user_id}`;
    const avatar = detailedUserInfo?.avatar || props.roomMembers.find(member => member.id === user_id)?.avatar || null;
    
    userStatuses.value.push({
      userId: user_id,
      username: username,
      avatar: avatar,
      status: video_status || 'unknown',
      lastUpdate: new Date()
    });
  }
  
  console.log('初始化用户视频状态:', userStatuses.value);
};

// 暴露方法给父组件
defineExpose({
  initializeUserStatuses,
  handleVideoStatusMessage
});

// Lifecycle
onMounted(() => {
  console.log('UserVideoStatus组件已挂载');
  setupWebSocketListener();
});

onBeforeUnmount(() => {
  // 清理逻辑
  userStatuses.value = [];
});
</script>

<style scoped>
.user-video-status h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.user-video-status.dark-mode h4 {
  color: #e1e1e1;
}

.status-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: #666;
  font-size: 14px;
}

.dark-mode .empty-state {
  color: #888;
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.user-status-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 6px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
}

.dark-mode .user-status-item {
  background: #2a2a2a;
  border-color: #404040;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.dark-mode .user-name {
  color: #e1e1e1;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-icon {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 10px;
  font-weight: bold;
}

.status-icon.loading {
  background: #ffeaa7;
  color: #fdcb6e;
}

.status-icon.ready {
  background: #d4edda;
  color: #155724;
}

.status-icon.error {
  background: #f8d7da;
  color: #721c24;
}

.status-icon.unknown {
  background: #e2e3e5;
  color: #6c757d;
}

.dark-mode .status-icon.loading {
  background: #6c5ce7;
  color: #a29bfe;
}

.dark-mode .status-icon.ready {
  background: #00b894;
  color: #55efc4;
}

.dark-mode .status-icon.error {
  background: #e84393;
  color: #fd79a8;
}

.dark-mode .status-icon.unknown {
  background: #636e72;
  color: #b2bec3;
}

.mini-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid #fdcb6e;
  border-top: 2px solid transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.dark-mode .mini-spinner {
  border-color: #a29bfe;
  border-top-color: transparent;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.status-text {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.dark-mode .status-text {
  color: #888;
}

.dark-mode .summary-item.error .summary-value {
  color: #fd79a8;
}

/* 移动端优化 */
.mobile-mode .user-status-item {
  padding: 6px 8px;
}

.mobile-mode .user-name {
  font-size: 12px;
}

.mobile-mode .status-text {
  font-size: 11px;
}
</style>
