<template>
  <div class="room-page" :class="{ 'dark-mode': isDarkMode, 'mobile-layout': isMobile }">
    <!-- 房间顶部状态栏 -->
    <RoomHeader 
      :room-name="roomName"
      :ws-status="wsStatus"
      :is-dark-mode="isDarkMode"
      :is-mobile="isMobile"
      @back-home="goHome"
      @toggle-dark-mode="isDarkMode = $event"
    />
    
    <!-- 桌面端布局 -->
    <div v-if="!isMobile" class="room-main desktop-layout">
      <!-- 视频播放区域 -->
      <VideoArea 
        ref="videoAreaComponentRef"
        :is-owner="isOwner"
        :room-id="roomId"
        :user-id="userId"
        :is-dark-mode="isDarkMode"
        :room-name="roomName"
        :is-room-public="isRoomPublic"
        @video-play="handleVideoPlay"
        @video-pause="handleVideoPause"
        @video-seek="handleVideoSeek"
        @video-url-change="handleVideoUrlChange"
        @room-settings-save="handleRoomSettingsSave"
        @room-dissolve="handleRoomDissolve"
      />
      
      <!-- 垂直分隔条 -->
      <DragDivider 
        direction="vertical"
        :is-dark-mode="isDarkMode"
        :target-ref="chatBarRef"
        :min-size="200"
      />
      
      <!-- 消息栏 -->
      <div class="chat-bar" ref="chatBarRef">
        <!-- 房间成员区域 -->
        <RoomMembers 
          :members="roomMembers" 
          :is-owner="isOwner"
          :current-user-id="userId"
          :room-id="roomId"
          @member-removed="handleMemberRemoved"
          @member-added="handleMemberAdded"
          ref="roomMembersRef"
        />
        
        <!-- 水平分隔条 -->
        <DragDivider 
          direction="horizontal"
          :is-dark-mode="isDarkMode"
          :target-ref="membersBarRef"
          :min-size="48"
        />
          <!-- 聊天区域组件 -->
        <ChatArea
          :messages="messages"
          :room-id="roomId"
          :user-id="userId"
          :loading-history="loadingHistory"
          @send-message="handleSendMessage"
          @load-history-with-callback="handleLoadHistoryWithCallback"
          ref="chatAreaRef"
        />
      </div>
    </div>

    <!-- 移动端布局 -->
    <div v-if="isMobile" class="room-main mobile-layout">
      <!-- 视频播放区域 (16:9) -->
      <div class="mobile-video-container">
        <VideoArea 
          ref="videoAreaComponentRef"
          :is-owner="isOwner"
          :room-id="roomId"
          :user-id="userId"
          :is-dark-mode="isDarkMode"
          :room-name="roomName"
          :is-room-public="isRoomPublic"          :is-mobile="true"
          @video-play="handleVideoPlay"
          @video-pause="handleVideoPause"
          @video-seek="handleVideoSeek"
          @video-url-change="handleVideoUrlChange"
          @status-update="handleStatusUpdate"
          @room-settings-save="handleRoomSettingsSave"
          @room-dissolve="handleRoomDissolve"
        />
      </div>      <!-- 视频控制区域 -->
      <div class="mobile-controls">        <div class="mobile-control-buttons">          <button 
            class="mobile-control-btn"
            :class="{ active: showMobileControls }"
            @click="toggleMobilePanel('controls')"
          >
            <span class="btn-text">视频控制</span>
          </button>
          <button 
            class="mobile-control-btn"
            :class="{ active: showMobileMembers }"
            @click="toggleMobilePanel('members')"
          >
            <span class="btn-icon">👥</span>
            <span class="btn-text">成员 ({{ roomMembers.length }})</span>
          </button>
          <button 
            v-if="isOwner"
            class="mobile-control-btn"
            :class="{ active: showMobileSettings }"
            @click="toggleMobilePanel('settings')"
          >
            <span class="btn-icon">⚙️</span>
            <span class="btn-text">房间设置</span>
          </button>
        </div>        <!-- 折叠的视频控制 -->
        <div v-if="showMobileControls" class="mobile-collapsible mobile-video-controls">
          <div class="mobile-panel-card">
            <!-- 视频控制条 -->
            <div class="mobile-video-control-section">
              <h4 class="mobile-section-title">视频控制</h4>              <VideoControls
                :is-playing="isPlaying"
                :current-time="currentTime"
                :duration="duration"
                :buffered-ranges="bufferedRanges"
                :played-percent="playedPercent"
                :volume="volume"
                :is-owner="isOwner"
                :is-dark-mode="isDarkMode"
                :is-mobile="true"                @toggle-play="handleTogglePlay"
                @seek="handleControlSeek"
                @volume-change="handleVolumeChange"
              />
            </div>

            <!-- 视频URL控制 -->
            <div class="mobile-url-section">
              <h4 class="mobile-section-title">视频链接</h4>
              <div class="mobile-url-input-group">
                <input 
                  v-model="videoUrlInput" 
                  type="url" 
                  placeholder="输入视频链接..."
                  class="mobile-url-input"
                  :disabled="!isOwner"
                />
                <button 
                  @click="confirmVideoUrl"
                  class="mobile-confirm-btn"
                  :disabled="!isOwner || !videoUrlInput.trim()"
                >
                  确认
                </button>
              </div>
              <div v-if="videoStatusMsg" class="mobile-status-msg">{{ videoStatusMsg }}</div>
            </div>
          </div>
        </div>

        <!-- 折叠的成员列表 -->
        <div v-if="showMobileMembers" class="mobile-collapsible mobile-members">
          <RoomMembers 
            :members="roomMembers" 
            :is-owner="isOwner"
            :current-user-id="userId"
            :room-id="roomId"
            :is-mobile="true"
            @member-removed="handleMemberRemoved"
            @member-added="handleMemberAdded"
            ref="roomMembersRef"
          />
        </div>        <!-- 折叠的房间设置 -->
        <div v-if="showMobileSettings && isOwner" class="mobile-collapsible mobile-settings">
          <div class="mobile-panel-card">            <RoomSettings 
              :is-owner="isOwner"
              :room-id="roomId"
              :room-name="roomName"
              :is-room-public="isRoomPublic"
              :is-dark-mode="isDarkMode"
              :is-mobile="true"
              @room-settings-save="handleRoomSettingsSave"
              @room-dissolve="handleRoomDissolve"
              @show-error="handleRoomSettingsError"
            />
          </div>
        </div>
      </div>

      <!-- 聊天区域 -->
      <div class="mobile-chat-container">        <ChatArea
          :messages="messages"
          :room-id="roomId"
          :user-id="userId"
          :loading-history="loadingHistory"
          :is-mobile="true"
          @send-message="handleSendMessage"
          @load-history-with-callback="handleLoadHistoryWithCallback"
          ref="chatAreaRef"
        />
      </div>
    </div>
    
    <!-- 自动播放被阻止提示 -->
    <div v-if="autoPlayBlocked" class="auto-play-prompt">
      <div class="auto-play-content">
        <div class="auto-play-icon">
          <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
            <polygon points="8,5 19,12 8,19" />
          </svg>
        </div>
        <h3>需要手动播放</h3>
        <p>浏览器阻止了自动播放，请点击下方按钮继续观看</p>
        <button @click="resumePlayback" class="resume-play-btn">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <polygon points="8,5 19,12 8,19" />
          </svg>
          继续播放
        </button>
      </div>
    </div>
    
    <BaseToast v-model="toastVisible" :message="toastMsg" :duration="1600" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed, onBeforeUnmount, nextTick } from 'vue';
import { useRouter, useRoute } from 'vue-router';

// Composables
import { useWebSocketStatus } from '@/composables/useWebSocketStatus';
import { useMyUserInfo, useUserInfo } from '@/composables/useUserInfo.js';
import { useVideoSync } from '@/composables/useVideoSync.js';
import { useChatMessages } from '@/composables/useChatMessages.js';
import { useResponsive } from '@/composables/useResponsive.js';

// Utils
import { getWebSocket } from '@/utils/ws';
import { getImageUrl, API_BASE_URL } from '@/utils/api';

// Assets
import defaultAvatar from '@/assets/default_avatar.jpg';

// Components
import BaseToast from '@/components/base/BaseToast.vue';
import DragDivider from '@/components/base/DragDivider.vue';
import VideoArea from '@/components/video/VideoArea.vue';
import VideoControls from '@/components/video/VideoControls.vue';
import RoomMembers from '@/components/room/RoomMembers.vue';
import RoomHeader from '@/components/room/RoomHeader.vue';
import RoomSettings from '@/components/room/RoomSettings.vue';
import ChatArea from '@/components/chat/ChatArea.vue';

const { avatarUrl, username, userId } = useMyUserInfo();

// NOTE: 视频播放控制现在完全在 VideoArea 组件中，Room.vue 不再直接控制

// NOTE: HLS 处理现在完全在 VideoArea 组件中，Room.vue 不再直接处理

// 使用视频同步 composable
const {
  toastVisible,
  toastMsg,
  autoPlayBlocked,
  syncPlay,
  syncPause,
  syncSeek,
  syncVideoUrl,
  handleVideoSyncMessage,
  handleRoomStateRestore,
  showSyncToast,
  resumePlayback
} = useVideoSync();

const router = useRouter();
const route = useRoute();
const isDarkMode = ref(true);

// 房间相关状态
const roomId = computed(() => route.query.id || route.params.id);
const isOwner = ref(false); // true为房主，false为成员
const videoAreaComponentRef = ref(null);
const roomMembersRef = ref(null);
const roomName = ref("");
const isRoomPublic = ref(false);
const roomMembers = ref([]);

// 响应式检测
const { isMobile } = useResponsive();

// 移动端状态管理
const mobileActiveTab = ref('video'); // 当前活跃标签
const showMobileControls = ref(false); // 是否显示视频控制
const showMobileMembers = ref(false); // 是否显示成员列表
const showMobileSettings = ref(false); // 是否显示房间设置

// 视频控制相关变量
const videoUrlInput = ref('');
const videoStatusMsg = computed(() => videoAreaComponentRef.value?.videoStatusMsg || '');

// 监听videoUrlInput变化，同步到VideoArea组件
watch(videoUrlInput, (newValue) => {
  if (videoAreaComponentRef.value && videoAreaComponentRef.value.videoUrlInput !== newValue) {
    videoAreaComponentRef.value.videoUrlInput = newValue;
  }
});

// 从VideoArea组件同步videoUrlInput的值
watch(() => videoAreaComponentRef.value?.videoUrlInput, (newValue) => {
  if (newValue !== undefined && videoUrlInput.value !== newValue) {
    videoUrlInput.value = newValue;
  }
});

// 视频播放器状态
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const bufferedRanges = ref([]);
const volume = ref(1);

// 处理VideoArea组件的状态更新
function handleStatusUpdate(status) {
  isPlaying.value = status.isPlaying;
  currentTime.value = status.currentTime;
  duration.value = status.duration;
  bufferedRanges.value = status.bufferedRanges;
  volume.value = status.volume;
  console.log('Room.vue 状态更新:', status);
}

const playedPercent = computed(() => {
  if (!duration.value || duration.value <= 0) return 0;
  const percent = (currentTime.value / duration.value) * 100;
  console.log('Room.vue playedPercent computed:', percent);
  return percent;
});

// 视频控制方法
function handleTogglePlay() {
  if (!videoAreaComponentRef.value) return;
  
  // 调用VideoArea的togglePlay方法，它会自动处理房间同步
  videoAreaComponentRef.value.togglePlay();
}

function handleControlSeek(newTime) {
  if (!videoAreaComponentRef.value) return;
  
  // 调用VideoArea的onSeek方法，它会自动处理房间同步
  videoAreaComponentRef.value.onSeek(newTime);
}

function handleVolumeChange(newVolume) {
  if (!videoAreaComponentRef.value) return;
  
  // 音量变化只是本地操作，不需要房间同步
  videoAreaComponentRef.value.setVolume(newVolume);
}

// 确认视频URL
function confirmVideoUrl() {
  if (!isOwner.value) {
    console.warn('用户不是房主');
    return;
  }
  
  if (!videoUrlInput.value.trim()) {
    console.warn('视频URL为空');
    return;
  }
  
  // 调用VideoArea组件的方法
  if (videoAreaComponentRef.value && typeof videoAreaComponentRef.value.confirmVideoUrl === 'function') {
    try {
      // 先同步videoUrlInput到VideoArea组件
      videoAreaComponentRef.value.videoUrlInput = videoUrlInput.value;
      // 然后调用确认方法
      videoAreaComponentRef.value.confirmVideoUrl();
    } catch (error) {
      console.error('调用VideoArea的confirmVideoUrl方法失败:', error);
    }
  } else {
    console.error('VideoArea组件未准备好或confirmVideoUrl方法不存在');
  }
}

// 移动端面板切换逻辑（互斥）
function toggleMobilePanel(panelType) {
  if (panelType === 'controls') {
    const wasOpen = showMobileControls.value;
    // 关闭所有面板
    showMobileControls.value = false;
    showMobileMembers.value = false;
    showMobileSettings.value = false;
    // 如果之前是关闭的，则打开当前面板
    if (!wasOpen) {
      showMobileControls.value = true;
    }
  } else if (panelType === 'members') {
    const wasOpen = showMobileMembers.value;
    showMobileControls.value = false;
    showMobileMembers.value = false;
    showMobileSettings.value = false;
    if (!wasOpen) {
      showMobileMembers.value = true;
    }
  } else if (panelType === 'settings') {
    const wasOpen = showMobileSettings.value;
    showMobileControls.value = false;
    showMobileMembers.value = false;
    showMobileSettings.value = false;
    if (!wasOpen) {
      showMobileSettings.value = true;
    }
  }
}

// 移动端视窗高度处理
const handleMobileViewportResize = () => {
  if (isMobile.value) {
    // 设置CSS自定义属性来处理动态视窗高度
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
  }
};

// 监听窗口大小变化
if (typeof window !== 'undefined') {
  window.addEventListener('resize', handleMobileViewportResize);
  window.addEventListener('orientationchange', handleMobileViewportResize);
}

// 使用聊天消息 composable
const {
  messages,
  loadingHistory,
  sendMessage: sendChatMessage,
  loadHistoryMessages,
  initializeMessages,
  fetchMessages
} = useChatMessages(roomId, userId);

// 聊天区域引用
const chatAreaRef = ref(null);

// 在fetchRoomDetailsAndSetIdentity中填充成员，房主排首位

const { wsStatus, setupWebSocket } = useWebSocketStatus();

// 成员管理事件处理函数
async function handleMemberRemoved(user) {
  const roomId = route.query.id || route.params.id;
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  
  try {
    await fetch(`${API_BASE_URL}/rooms/${roomId}/members/${user.id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });
    
    // 更新本地成员列表
    const idx = roomMembers.value.findIndex(m => m.id === user.id);
    if (idx !== -1) {
      roomMembers.value.splice(idx, 1);
    }
    
    showSyncToast(`用户 ${user.username} 已被移出房间`);
  } catch (e) {
    console.error('移除用户失败:', e);
    showSyncToast('操作失败，请重试');
  }
}

function handleMemberAdded(data) {
  // 可以在这里处理成员添加后的逻辑，比如刷新成员列表
  showSyncToast('成员邀请已发送');
}

async function fetchRoomDetailsAndSetIdentity() {
  const roomId = route.query.id || route.params.id;
  if (!roomId) return;
  
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  
  try {
    const resp = await fetch(`${API_BASE_URL}/rooms/${roomId}/details`, {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    
    if (resp.ok) {
      const data = await resp.json();
      
      // 获取当前登录用户id
      let myId = userId.value;
      if (data.owner && myId && data.owner.id === myId) {
        isOwner.value = true;
      } else {
        isOwner.value = false;
      }
      
      let members = [];
      
      if (data.name) { 
        roomName.value = data.name;
        isRoomPublic.value = data.is_public || false;
      }
      
      if (data.owner) {
        members.push({
          id: data.owner.id,
          username: data.owner.username,
          avatarUrl: data.owner.avatar_path ? getImageUrl(data.owner.avatar_path) : defaultAvatar,
          isOwner: true
        });
      }
      
      if (data.members && Array.isArray(data.members)) {
        members = members.concat(
          data.members
            .filter(u => !data.owner || u.id !== data.owner.id)
            .map(u => ({
              id: u.id,
              username: u.username,
              avatarUrl: u.avatar_path ? getImageUrl(u.avatar_path) : (u.avatar || ''),
              isOwner: false
            }))
        );
      }
      
      roomMembers.value = members;
        // 初始化聊天消息
      if (data.message_count) {
        initializeMessages(data.message_count);
        await fetchMessages();
        
        // 消息加载完成后滚动到底部
        nextTick(() => {
          if (chatAreaRef.value) {
            chatAreaRef.value.scrollToBottom();
          }
        });
      } else {
        // 即使没有历史消息，也要滚动到底部确保位置正确
        nextTick(() => {
          if (chatAreaRef.value) {
            chatAreaRef.value.scrollToBottom();
          }
        });
      }
    }
  } catch (e) { 
    /* 可加错误提示 */ 
  }
}

function goHome() {
  // 通过websocket发送离开房间消息
  const ws = getWebSocket();
  const roomId = route.query.id || route.params.id;
  
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'leave_room',
      payload: { room_id: roomId }
    }));
  }
  
  router.push('/');
}

// 聊天相关事件处理函数
async function handleSendMessage(content) {
  await sendChatMessage(content, { username: username.value, avatarUrl: avatarUrl.value });
  
  // 滚动到底部
  nextTick(() => {
    if (chatAreaRef.value) {
      chatAreaRef.value.scrollToBottom();
    }
  });
}

function handleLoadHistoryWithCallback(callback) {
  // 使用旧代码的处理方式
  loadHistoryMessages().then(() => {
    // 历史消息加载完成后执行位置保持回调
    callback();
  });
}

// VideoArea 组件事件处理函数
function handleVideoPlay(roomId, userId, currentTime) {
  syncPlay(roomId, userId, currentTime);
}

function handleVideoPause(roomId, userId, currentTime) {
  syncPause(roomId, userId, currentTime);
}

function handleVideoSeek(roomId, userId, currentTime) {
  syncSeek(roomId, userId, currentTime);
}

function handleVideoUrlChange(roomId, userId, url) {
  syncVideoUrl(roomId, userId, url);
}

function handleRoomSettingsSave(newRoomName, newIsRoomPublic) {
  roomName.value = newRoomName;
  isRoomPublic.value = newIsRoomPublic;
  
  // 显示保存成功的提示
  showSyncToast('房间设置已保存');
}

function handleRoomSettingsError(errorMessage) {
  // 显示错误提示
  showSyncToast(errorMessage);
}

function handleRoomDissolve() {
  // 显示解散房间的提示
  showSyncToast('时间Cia不多llo');
  
  setTimeout(() => {
    // 断开WebSocket连接
    const ws = getWebSocket();
    if (ws) {
      ws.send(JSON.stringify({
        type: 'leave_room',
        payload: { room_id: roomId.value, sender_id: userId.value }
      }));
      ws.close();
    }
    router.push('/');
  }, 2000);
}

onMounted(() => {
  fetchRoomDetailsAndSetIdentity();
  if (wsStatus.value === 'disconnected') setupWebSocket();
  else getWebSocketAndEnterRoom();
  
  // 移动端视窗高度初始化
  handleMobileViewportResize();
  
  // 确保聊天区域滚动到底部（延迟执行以等待所有内容加载完成）
  setTimeout(() => {
    nextTick(() => {
      if (chatAreaRef.value) {
        chatAreaRef.value.scrollToBottom();
      }
    });
  }, 500); // 500ms延迟确保内容完全加载
});

async function getWebSocketAndEnterRoom() {
  // 发送websocket进入房间消息
  const ws = getWebSocket();
  const roomId = route.query.id || route.params.id;
  if (!roomId) return;
  
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: 'enter_room',
      payload: {
        room_id: roomId
      }
    }));
  }

  // WebSocket消息处理
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.addEventListener('message', async (event) => {
      try {
        const msg = JSON.parse(event.data);
        console.log('收到WebSocket消息:', msg); // 添加调试信息
        
        if (msg.type === 'room_message' && msg.payload) {
          const { room_id, sender_id, content, timestamp } = msg.payload;
          // 获取用户信息
          const userInfo = await useUserInfo(sender_id);          messages.value.push({
            content,
            user_id: sender_id,
            username: userInfo?.username || '未知用户',
            avatar: userInfo?.avatarUrl || defaultAvatar,
            isSelf: sender_id === userId.value,
            timestamp
          });
          
          // 只有当用户在聊天底部时才自动滚动到新消息
          nextTick(() => {
            if (chatAreaRef.value && chatAreaRef.value.isUserAtBottom()) {
              chatAreaRef.value.scrollToBottom();
            }
          });
        } else if (msg.type === 'set_vedio_url' && msg.payload) {
          // 通过 VideoArea 组件处理URL设置
          const videoControls = {
            loadVideo: (url, options) => {
              videoAreaComponentRef.value?.loadVideo(url, options);
            }
          };
          await handleVideoSyncMessage(msg, videoControls, useUserInfo);        } else if (msg.type === 'set_vedio_start') {
          // 通过 VideoArea 组件处理播放
          const videoControls = {
            play: () => {
              return videoAreaComponentRef.value?.play();
            }
          };
          // allowProgressSync = false，实时播放控制不设置进度
          await handleVideoSyncMessage(msg, videoControls, useUserInfo, false);
        } else if (msg.type === 'set_vedio_pause') {
          // 通过 VideoArea 组件处理暂停
          const videoControls = {
            pause: () => {
              videoAreaComponentRef.value?.pause();
            }
          };
          await handleVideoSyncMessage(msg, videoControls, useUserInfo);
        } else if (msg.type === 'receive_notification') {
          showSyncToast('您有新的通知，请在通知页面查看。');        } else if (msg.type === 'set_vedio_jump' && msg.payload) {
          // 通过 VideoArea 组件处理跳转
          const videoControls = {
            seekTo: (time) => {
              videoAreaComponentRef.value?.seekTo(time);
            },
            pause: () => {
              videoAreaComponentRef.value?.pause();
            }
          };
          await handleVideoSyncMessage(msg, videoControls, useUserInfo);
        } else if (msg.type === 'room_entered' && msg.payload) {
          console.log('已进入房间:', msg.payload.room_id, msg.payload.room_info);
          
          // 通过 VideoArea 组件处理房间状态恢复
          const videoControls = {
            loadVideo: (url, options) => {
              videoAreaComponentRef.value?.loadVideo(url, options);
            },            play: () => {
              return videoAreaComponentRef.value?.play();
            },
            pause: () => {
              videoAreaComponentRef.value?.pause();
            },
            seekTo: (time) => {
              videoAreaComponentRef.value?.seekTo(time);
            }
          };
          
          // 使用专用的房间状态恢复函数
          await handleRoomStateRestore(msg.payload.room_info, videoControls);
        }
        // 未来可扩展其他type
      } catch (e) {
        console.error('WebSocket消息处理错误:', e);
      }
    });
  }
}

// 拖拽调整成员区域高度
const membersBarRef = computed(() => roomMembersRef.value?.membersBarRef);

onBeforeUnmount(() => {
  // 清理事件监听器
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', handleMobileViewportResize);
    window.removeEventListener('orientationchange', handleMobileViewportResize);
  }
  
  // 拖拽分隔条的清理现在由 DragDivider 组件内部处理
});

watch(wsStatus, (newStatus) => {
  if (newStatus === 'connected') {
    getWebSocketAndEnterRoom();
  }
});

const chatBarRef = ref(null);
</script>

<style scoped>
@import '@/styles/room.css';

.room-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(to bottom, #e6f5f3, #c8e6e0);
  transition: background var(--transition-normal);
}

.room-page.dark-mode {
  background: linear-gradient(120deg, #23283a 0%, #181c24 100%);
}

.room-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.desktop-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.mobile-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.chat-bar {
  width: 330px;
  min-width: 330px;
  max-width: 100%;
  background: #fff;
  display: flex;
  flex-direction: column;
  border-left: 1px solid #eee;
  height: 100%;
}

.room-page.dark-mode .chat-bar {
  background: linear-gradient(120deg, #23283a 0%, #181c24 100%);
  border-left: 1px solid #23283a;
}

.loading {
  color: #1976d2;
}

.volume-icon svg {
  color: inherit;
}

.room-page.dark-mode .volume-icon svg {
  color: #fff;
}

/* 自动播放提示样式 */
.auto-play-prompt {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.auto-play-content {
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  text-align: center;
  max-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  animation: slideUp 0.3s ease-out;
}

.room-page.dark-mode .auto-play-content {
  background: #2a3045;
  color: #fff;
}

.auto-play-icon {
  color: #1976d2;
  margin-bottom: 16px;
}

.room-page.dark-mode .auto-play-icon {
  color: #90caf9;
}

.auto-play-content h3 {
  margin: 0 0 12px 0;
  font-size: 20px;
  font-weight: 600;
}

.auto-play-content p {
  margin: 0 0 24px 0;
  color: #666;
  line-height: 1.5;
}

.room-page.dark-mode .auto-play-content p {
  color: #ccc;
}

.resume-play-btn {
  background: #1976d2;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 auto;
  transition: all 0.2s ease;
}

.resume-play-btn:hover {
  background: #1565c0;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(25, 118, 210, 0.3);
}

.resume-play-btn:active {
  transform: translateY(0);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Mobile Responsive Styles */
@media (max-width: 768px) {
  .room-page.mobile-layout {
    /* 使用自定义属性处理视窗高度 */
    height: calc(var(--vh, 1vh) * 100);
    /* 降级方案 */
    height: 100vh;
    height: 100dvh;
    display: flex;
    flex-direction: column;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    overflow: hidden;
  }

  /* 支持动态视窗高度的浏览器 */
  @supports (height: 100dvh) {
    .room-page.mobile-layout {
      height: 100dvh;
    }
  }
  /* 移动端视频容器 (16:9 比例) */
  .mobile-video-container {
    width: 100%;
    max-width: 100vw; /* 确保不超出视窗宽度 */
    aspect-ratio: 16/9;
    max-height: 35vh; /* 稍微减少高度，为其他内容留更多空间 */
    background: #000;
    position: relative;
    flex-shrink: 0;
    overflow: hidden; /* 防止内容溢出 */
    box-sizing: border-box;
  }
  /* 移动端控制区域 */
  .mobile-controls {
    background: rgba(255, 255, 255, 0.95);
    border-bottom: 1px solid #eee;
    flex-shrink: 0;
    max-height: 60vh; /* 大幅增加控制区域高度，可以占满下半部分 */
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }

  .room-page.dark-mode .mobile-controls {
    background: rgba(35, 40, 58, 0.95);
    border-bottom: 1px solid #23283a;
  }
  .mobile-control-buttons {
    display: flex;
    padding: 12px 16px;
    gap: 12px;
    overflow-x: auto;
    flex-shrink: 0; /* 按钮区域不收缩 */
  }

  .mobile-control-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
    transform: translateZ(0); /* 启用硬件加速 */
    white-space: nowrap;
    min-height: var(--mobile-touch-target);
  }

  .mobile-control-btn:hover,
  .mobile-control-btn.active {
    background: #007bff;
    color: white;
    border-color: #007bff;
  }

  .room-page.dark-mode .mobile-control-btn {
    background: #23283a;
    border-color: #3a4050;
    color: #fff;
  }

  .room-page.dark-mode .mobile-control-btn:hover,
  .room-page.dark-mode .mobile-control-btn.active {
    background: #007bff;
    border-color: #007bff;
  }

  .btn-icon {
    font-size: 16px;
  }

  .btn-text {
    font-size: 14px;
    font-weight: 500;
  }  /* 折叠区域 */
  .mobile-collapsible {
    border-top: 1px solid #eee;
    flex: 1; /* 让折叠区域占据剩余空间 */
    min-height: 300px; /* 最小高度 */
    max-height: calc(60vh - 80px); /* 控制区域高度减去按钮区域高度 */
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    /* 动画效果 */
    animation: fadeIn 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
    transform-origin: top;
  }

  @keyframes fadeIn {
    0% {
      opacity: 0;
    }
    100% {
      opacity: 1;
    }
  }  /* 成员列表折叠区域 */
  .mobile-collapsible.mobile-members {
    padding: 8px 0; /* 减少内边距 */
    animation: fadeIn 0.35s cubic-bezier(0.4, 0.0, 0.2, 1);
  }
  /* 当有折叠面板展开时，调整聊天容器高度 */
  .room-page.mobile-layout:has(.mobile-collapsible) .mobile-chat-container {
    flex: 0 1 40vh; /* 当有展开面板时，聊天区域最多占40vh */
  }

  .room-page.dark-mode .mobile-collapsible {
    border-top: 1px solid #3a4050;
  }
  /* 移动端面板卡片样式 */
  .mobile-panel-card {
    background: #fff;
    border-radius: 8px;
    margin: 8px 12px 12px 12px; /* 减少顶部边距 */
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    border: 1px solid #f0f2f5;
    flex: 1; /* 让卡片填充可用空间 */
    display: flex;
    flex-direction: column;    min-height: 0; /* 允许内容溢出时滚动 */
    animation: fadeIn 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
  }

  .room-page.dark-mode .mobile-panel-card {
    background: #23283a;
    border-color: #3a4050;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
  }

  /* 移动端区域标题 */
  .mobile-section-title {
    margin: 0 0 12px 0;
    font-size: 16px;
    font-weight: 600;
    color: #333;
    border-bottom: 1px solid #f0f2f5;
    padding-bottom: 8px;
  }

  .room-page.dark-mode .mobile-section-title {
    color: #fff;
    border-bottom-color: #3a4050;
  }
  /* 移动端视频控制区域 */
  .mobile-video-control-section {
    margin-bottom: 16px;
  }

  .mobile-video-control-section .custom-video-controls {
    background: rgba(240, 242, 245, 0.8);
    border-radius: 8px;
    padding: 12px 16px;
    border: 1px solid #e1e7ed;
  }

  .room-page.dark-mode .mobile-video-control-section .custom-video-controls {
    background: rgba(42, 47, 62, 0.8);
    border-color: #3a4050;
  }

  /* 移动端URL区域样式 */
  .mobile-url-section {
    margin-top: 16px;
  }

  .mobile-url-input-group {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }

  .mobile-url-input {
    flex: 1;
    padding: 10px 12px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 14px;
    background: #fff;
  }

  .room-page.dark-mode .mobile-url-input {
    background: #2a2f3e;
    border-color: #3a4050;
    color: #fff;
  }

  .mobile-url-input:focus {
    outline: none;
    border-color: #1976d2;
    box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.1);
  }

  .mobile-confirm-btn {
    padding: 10px 16px;
    background: #1976d2;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    min-width: 60px;
  }

  .mobile-confirm-btn:hover {
    background: #1565c0;
  }

  .mobile-confirm-btn:disabled {
    background: #ccc;
    cursor: not-allowed;
  }

  .mobile-status-msg {
    margin-top: 8px;
    font-size: 12px;
    color: #666;
  }

  .room-page.dark-mode .mobile-status-msg {
    color: #ccc;
  }

  .mobile-members {
    background: transparent;
  }

  .mobile-settings {
    background: transparent;
    padding: 0;
  }  /* 移动端聊天容器 */
  .mobile-chat-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 200px; /* 确保聊天区域有最小高度 */
    background: #fff;
    overflow: hidden;
    position: relative;
    border-top: 2px solid #e1e7ed;
    border-left: 1px solid #f0f2f5;
    border-right: 1px solid #f0f2f5;
    border-bottom: 1px solid #f0f2f5;
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
  }

  .room-page.dark-mode .mobile-chat-container {
    background: #23283a;
    border-top: 2px solid #3a4050;
    border-left: 1px solid #2a3242;
    border-right: 1px solid #2a3242;
    border-bottom: 1px solid #2a3242;
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.15);
  }

  /* 确保聊天输入框在底部可见 */
  .mobile-chat-container {
    padding-bottom: env(safe-area-inset-bottom); /* 考虑iPhone的安全区域 */
  }

  /* 隐藏桌面端特定元素 */
  .mobile-layout .chat-bar,
  .mobile-layout .desktop-layout {
    display: none;
  }

  /* 调整自动播放提示在移动端的显示 */
  .auto-play-prompt {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1000;
  }

  .auto-play-content {
    margin: 20px;
    max-width: none;
  }
}

@keyframes slideDown {
  from {
    max-height: 0;
    opacity: 0;
  }
  to {
    max-height: 200px;
    opacity: 1;
  }
}

</style>
