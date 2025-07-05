<template>
  <div class="video-area" :class="{ 'dark-mode': isDarkMode, 'mobile-mode': isMobile }">
    <!-- 视频播放器容器 -->
    <div class="video-player-container" :class="{ 'mobile-container': isMobile }">
      <video ref="videoRef" class="video-player" />
      
      <!-- 移动端视频状态遮罩层 -->
      <div v-if="isMobile" class="mobile-video-overlay" :class="overlayClass">
        <!-- 加载中状态 -->
        <div v-if="showLoadingOverlay" class="overlay-content">
          <div class="overlay-icon">
            <div class="loading-spinner"></div>
          </div>
          <div class="overlay-text">{{ videoStatusMsg || '加载中...' }}</div>
        </div>
        
        <!-- 播放失败状态 -->
        <div v-if="showErrorOverlay" class="overlay-content">
          <div class="overlay-icon error-icon">⚠</div>
          <div class="overlay-text">{{ videoStatusMsg }}</div>
        </div>
        
        <!-- 暂停状态 -->
        <div v-if="showPausedOverlay" class="overlay-content">
          <div class="overlay-icon">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
              <rect x="6" y="5" width="4" height="14"/>
              <rect x="14" y="5" width="4" height="14"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- 桌面端视频状态遮罩层 -->
      <div v-if="!isMobile" class="desktop-video-overlay" :class="overlayClass">
        <!-- 加载中状态 -->
        <div v-if="showLoadingOverlay" class="overlay-content">
          <div class="overlay-icon">
            <div class="loading-spinner"></div>
          </div>
          <div class="overlay-text">{{ videoStatusMsg || '加载中...' }}</div>
        </div>
        
        <!-- 播放失败状态 -->
        <div v-if="showErrorOverlay" class="overlay-content">
          <div class="overlay-icon error-icon">⚠</div>
          <div class="overlay-text">{{ videoStatusMsg }}</div>
        </div>
        
        <!-- 暂停状态 -->
        <div v-if="showPausedOverlay" class="overlay-content">
          <div class="overlay-icon">
            <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
              <rect x="6" y="5" width="4" height="14"/>
              <rect x="14" y="5" width="4" height="14"/>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- 桌面端显示完整的控制和设置 -->
    <div class="video-extra-area" v-if="!isMobile">
      <!-- 自定义控制栏 -->
      <VideoControls
        :is-playing="isPlaying"
        :current-time="currentTime"
        :duration="duration"
        :volume="volume"
        :buffered-ranges="bufferedRanges"
        :played-percent="playedPercent"
        :is-owner="isOwner"
        :is-dark-mode="isDarkMode"        
        @toggle-play="togglePlay"        
        @seek="onSeek"
        @volume-change="onVolumeChange"
      />      
      
      <!-- 视频外链表单 -->
      <VideoUrlForm
        v-model:video-url="internalVideoUrlInput"
        :confirmed-url="videoUrl"
        :is-owner="isOwner"
        :is-dark-mode="isDarkMode"
        :status-message="videoStatusMsg"
        :is-loading="isVideoLoading"
        :is-playing="isPlaying"
        :video-loading="videoLoading"
        @confirm-url="confirmVideoUrl"
      />
      
      <!-- 用户视频状态卡片 -->
      <UserVideoStatus
        ref="userVideoStatusRef"
        :is-owner="isOwner"
        :room-id="roomId"
        :user-id="userId"
        :is-dark-mode="isDarkMode"
        :is-mobile="isMobile"
        :ws-connection="wsConnection"
        :room-members="roomMembers"
      />
      
      <!-- 房间设置组件 -->      
      <RoomSettings
        :is-owner="isOwner"
        :room-id="roomId"
        :room-name="roomName"
        :is-room-public="isRoomPublicLocal"
        :is-dark-mode="isDarkMode"
        @room-settings-save="handleRoomSettingsSave"
        @room-dissolve="handleRoomDissolve"
        @show-error="handleShowToast"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, toRefs } from 'vue';
import '@/styles/components/video/index.css';
import '@/styles/components/video/responsive.css';
import { useVideoPlayer } from '@/composables/useVideoPlayer.js';
import { useHLS } from '@/composables/useHLS.js';
import { useVideoSync } from '@/composables/useVideoSync.js';
import { API_BASE_URL } from '@/utils/api';
import VideoControls from '@/components/video/VideoControls.vue';
import VideoUrlForm from '@/components/video/VideoUrlForm.vue';
import UserVideoStatus from '@/components/room/UserVideoStatus.vue';
import RoomSettings from '@/components/room/RoomSettings.vue';

// Props
const props = defineProps({
  isOwner: {
    type: Boolean,
    required: true
  },
  roomId: {
    type: String,
    required: true
  },  userId: {
    type: [String, Number],
    required: true
  },
  isDarkMode: {
    type: Boolean,
    default: false
  },
  roomName: {
    type: String,
    default: ''
  },
  isRoomPublic: {
    type: Boolean,
    default: false
  },
  isMobile: {
    type: Boolean,
    default: false
  },
  videoUrlInput: {
    type: String,
    default: ''
  },
  externalVideoStatus: {
    type: String,
    default: ''
  },
  wsConnection: {
    type: Object,
    default: null
  },
  roomMembers: {
    type: Array,
    default: () => []
  }
});

// Emits
const emit = defineEmits([
  'video-play',
  'video-pause', 
  'video-seek',
  'video-url-change',
  'room-settings-save',
  'room-dissolve',
  'show-toast',
  'status-update',
  'video-url-input-change',
  'video-status-change'
]);

// 使用视频播放器 composable
const {
  videoRef,
  isPlaying,
  currentTime,
  duration,
  volume,
  videoLoading,
  bufferedRanges,
  playedPercent,
  togglePlay: videoTogglePlay,
  play,
  pause,
  seekTo,
  setVolume,
  formatTime,
  initVideoEvents
} = useVideoPlayer();

// 使用 HLS 处理 composable
const {
  videoStatusMsg,
  videoLoading: hlsVideoLoading,
  loadHLSSource,
  destroyHLS,
  clearErrorStatus
} = useHLS();

// 使用视频同步 composable
const {
  showSyncToast,
  sendVideoMessage
} = useVideoSync();

// 组件引用
const userVideoStatusRef = ref(null);

// 合并视频加载状态，添加智能检测
const isVideoLoading = computed(() => {
  const combinedLoading = videoLoading.value || hlsVideoLoading.value;
  
  // 如果视频正在 seeking，应该显示加载状态
  if (videoRef.value && videoRef.value.seeking) {
    return true;
  }
  
  // 如果显示加载中，但视频实际已就绪且不在 seeking，则返回 false
  if (combinedLoading && videoRef.value) {
    const video = videoRef.value;
    if (video.readyState >= 2 && video.duration > 0 && !video.seeking) {
      return false;
    }
  }
  
  return combinedLoading;
});

// 遮罩层显示控制
const showLoadingOverlay = computed(() => {
  return isVideoLoading.value || (videoStatusMsg.value === '加载中...');
});

const showErrorOverlay = computed(() => {
  return videoStatusMsg.value && 
         videoStatusMsg.value !== '加载中...' && 
         videoStatusMsg.value !== '';
});

const showPausedOverlay = computed(() => {
  // 暂停遮罩支持PC端和移动端
  const video = videoRef.value;
  if (!video) {
    console.log('暂停遮罩：视频元素不存在');
    return false;
  }
  
  // 简化判断条件：只要视频存在、不在播放、不在加载、没有错误信息就显示暂停遮罩
  const shouldShow = !isPlaying.value && // 不在播放
                     !isVideoLoading.value && // 不在加载中
                     !showLoadingOverlay.value && // 不显示加载遮罩
                     !showErrorOverlay.value && // 不显示错误遮罩
                     video.readyState >= 1; // 视频至少有基本数据
  
  // 添加详细调试信息
  console.log('暂停遮罩状态检查:', {
    isMobile: props.isMobile,
    hasVideo: !!video,
    isPlaying: isPlaying.value,
    isVideoLoading: isVideoLoading.value,
    videoLoading: videoLoading.value,
    hlsVideoLoading: hlsVideoLoading.value,
    showLoadingOverlay: showLoadingOverlay.value,
    showErrorOverlay: showErrorOverlay.value,
    readyState: video ? video.readyState : 'no video',
    videoSrc: video ? video.src : 'no video',
    shouldShow
  });
  
  return shouldShow;
});

const overlayClass = computed(() => {
  return {
    'show-loading': showLoadingOverlay.value,
    'show-error': showErrorOverlay.value,
    'show-paused': showPausedOverlay.value,
    'dark-mode': props.isDarkMode
  };
});

// 内部状态 - 使用外部传入的状态作为默认值
const videoUrl = ref('');
const internalVideoUrlInput = ref(props.videoUrlInput || '');
const isRoomPublicLocal = ref(props.isRoomPublic);

// 监听外部videoUrlInput变化，同步到内部状态
watch(() => props.videoUrlInput, (newValue) => {
  if (newValue !== internalVideoUrlInput.value) {
    internalVideoUrlInput.value = newValue;
  }
});

// 监听内部输入变化，通知外部
watch(internalVideoUrlInput, (newValue) => {
  emit('video-url-input-change', newValue);
});

// 监听外部视频状态变化
watch(() => props.externalVideoStatus, (newValue) => {
  if (newValue && newValue !== videoStatusMsg.value) {
    videoStatusMsg.value = newValue;
  }
});

// 监听内部状态变化，通知外部
watch(videoStatusMsg, (newValue) => {
  emit('video-status-change', newValue);
});

// 监听视频状态变化，发送WebSocket消息
watch([showLoadingOverlay, showErrorOverlay, showPausedOverlay], ([loading, error, paused]) => {
  const video = videoRef.value;
  if (!video) return;
  
  let status = '';
  let message = '';
  
  // 复用现有的状态判断逻辑
  if (loading) {
    status = 'loading';
    message = videoStatusMsg.value || '加载中...';
  } else if (error) {
    status = 'error';
    message = videoStatusMsg.value || '';
  } else if (video.readyState >= 1) {
    status = 'ready';
    message = '';
  }
  
  // 只在状态确实变化时发送消息
  if (status && status !== watch.lastStatus) {
    watch.lastStatus = status;
    
    sendVideoMessage('video_status', {
      room_id: props.roomId,
      sender_id: props.userId,
      status: status,
      message: message,
      timestamp: Date.now()
    });
    
    console.log('发送视频状态消息:', status, message);
  }
}, { 
  immediate: false,
  flush: 'post'
});

// 初始化状态跟踪
watch.lastStatus = null;

// 监听 props 变化
watch(() => props.isRoomPublic, (newValue) => {
  isRoomPublicLocal.value = newValue;
});

// 添加定期状态同步检查
let statusSyncInterval = null;

function startStatusSync() {
  if (statusSyncInterval) {
    clearInterval(statusSyncInterval);
  }
  
  statusSyncInterval = setInterval(() => {
    const video = videoRef.value;
    if (video && (videoLoading.value || hlsVideoLoading.value)) {
      // 如果正在 seeking，保持加载状态
      if (video.seeking) {
        return;
      }
      
      // 如果显示加载中，但视频实际已就绪且不在 seeking
      if (video.readyState >= 2 && video.duration > 0) {
        // 强制同步状态
        videoLoading.value = false;
        if (hlsVideoLoading.value) {
          hlsVideoLoading.value = false;
        }
      }
    }
  }, 500); // 缩短检查间隔以更快响应 seeking 状态变化
}

function stopStatusSync() {
  if (statusSyncInterval) {
    clearInterval(statusSyncInterval);
    statusSyncInterval = null;
  }
}

// 视频控制方法
function togglePlay() {
  videoTogglePlay();
  
  const video = videoRef.value;
  if (!video) return;
    if (props.isOwner && props.roomId) {
    if (video.paused) {
      emit('video-pause', props.roomId, props.userId, video.currentTime);
    } else {
      emit('video-play', props.roomId, props.userId, video.currentTime);
    }
  }
}

function onSeek(newTime) {
  const time = Number(newTime);
  seekTo(time);
  
  // 跳转后自动暂停视频
  const video = videoRef.value;
  if (video && !video.paused) {
    video.pause();
    isPlaying.value = false;
  }
  
  if (props.isOwner && props.roomId) {
    emit('video-seek', props.roomId, props.userId, time);
    // 不需要额外发送暂停消息，因为其他用户收到跳转消息后也会自动暂停
  }
}

function onVolumeChange(newVolume) {
  const vol = Number(newVolume);
  setVolume(vol);
}

function playVideoWithUrl(url, options = {}) {
  const video = videoRef.value;
  if (!video) return;
  
  loadHLSSource(video, url, options);
}

function confirmVideoUrl() {
  playVideoWithUrl(internalVideoUrlInput.value, { autoPlay: false });
  const video = videoRef.value;
  if (video) {
    video.pause();
  }
  isPlaying.value = false;
  
  if (props.isOwner && props.roomId) {
    emit('video-url-change', props.roomId, props.userId, internalVideoUrlInput.value);
  }
}

// RoomSettings 组件事件处理
function handleRoomSettingsSave(newRoomName, newIsRoomPublic) {
  isRoomPublicLocal.value = newIsRoomPublic;
  emit('room-settings-save', newRoomName, newIsRoomPublic);
}

function handleRoomDissolve() {
  emit('room-dissolve');
}

function handleShowToast(message) {
  showSyncToast(message);
}

// 监听 URL 输入变化
watch(internalVideoUrlInput, (val) => {
  if (!val) {
    videoStatusMsg.value = '';
    return;
  }
  // 内部验证逻辑
  const url = val.trim();
  const isValid = /^https?:\/\/.+\.(mp4|webm|ogg|m3u8)(\?.*)?$/i.test(url);
  if (!isValid) {
    videoStatusMsg.value = '请输入有效的视频直链（支持mp4/webm/ogg/m3u8）';
  } else {
    videoStatusMsg.value = '';
  }
});

// 暴露方法给父组件
defineExpose({
  loadVideo: (url, options) => {
    internalVideoUrlInput.value = url;
    playVideoWithUrl(url, options);
    const video = videoRef.value;
    if (video) {
      video.pause();
    }
    isPlaying.value = false;  },
  confirmVideoUrl,
  togglePlay,
  onSeek,
  setVolume,
  play: () => {
    const video = videoRef.value;
    if (video) {
      return video.play(); // 返回Promise以便捕获自动播放异常
    }
    return Promise.reject(new Error('Video element not found'));
  },
  pause: () => {
    const video = videoRef.value;
    if (video && !video.paused) {
      video.pause();
    }
  },
  seekTo: (time) => {
    const video = videoRef.value;
    if (video && typeof time === 'number') {
      // 确保进度在有效范围内
      const safeDuration = video.duration || Infinity;
      const safeTime = Math.max(0, Math.min(time, safeDuration));
      
      if (time > safeDuration) {
        console.warn(`尝试设置的进度 ${time} 超过视频时长 ${safeDuration}，已限制为 ${safeTime}`);
      }
      
      video.currentTime = safeTime;
    }  },
  // 暴露响应式变量
  videoUrlInput: internalVideoUrlInput,
  videoStatusMsg,
  isPlaying,
  currentTime,
  duration,
  volume,
  bufferedRanges,
  // 初始化用户视频状态
  initializeUserVideoStatuses: (onlineUsers) => {
    if (userVideoStatusRef.value && userVideoStatusRef.value.initializeUserStatuses) {
      userVideoStatusRef.value.initializeUserStatuses(onlineUsers);
    }
  },
  // 处理用户视频状态消息
  handleUserVideoStatusMessage: (message) => {
    if (userVideoStatusRef.value && userVideoStatusRef.value.handleVideoStatusMessage) {
      userVideoStatusRef.value.handleVideoStatusMessage(message);
    }
  }
});

// 监听播放器状态变化，通知父组件
watch([isPlaying, currentTime, duration, bufferedRanges, volume], ([playing, time, dur, buffers, vol]) => {
  emit('status-update', {
    isPlaying: playing,
    currentTime: time,
    duration: dur,
    bufferedRanges: buffers,
    volume: vol
  });
});

onMounted(() => {
  initVideoEvents();
  startStatusSync(); // 启动状态同步
  
  const video = videoRef.value;
  if (video) {    video.addEventListener('error', () => {
      // 普通视频错误通常是致命的，直接显示失败状态
      videoStatusMsg.value = '播放失败，请检查视频链接';
    });    // 添加播放状态相关事件监听，用于错误状态恢复检测
    video.addEventListener('playing', () => {
      // 视频开始播放时，如果有错误信息，检查是否应该清除
      if (videoStatusMsg.value && videoStatusMsg.value !== '加载中...') {
        setTimeout(() => {
          if (!video.paused && !video.ended && video.readyState >= 2) {
            clearErrorStatus();
          }
        }, 2000);
      }
    });    video.addEventListener('timeupdate', () => {
      // 播放过程中定期检查，如果播放正常且有错误信息，则清除错误信息
      if (videoStatusMsg.value && videoStatusMsg.value !== '加载中...' && 
          !video.paused && !video.ended && 
          video.readyState >= 2 && video.currentTime > 0) {
        // 使用防抖，避免频繁触发
        clearTimeout(video._clearErrorTimeout);
        video._clearErrorTimeout = setTimeout(() => {
          if (!video.paused && !video.ended && video.readyState >= 2) {
            clearErrorStatus();
          }
        }, 3000);
      }
    });video.addEventListener('canplay', () => {
      // 视频可以播放时，清除加载相关的错误状态
      if (videoStatusMsg.value.includes('播放警告') || videoStatusMsg.value.includes('加载')) {
        setTimeout(() => {
          if (video.readyState >= 2) {
            clearErrorStatus();
          }
        }, 1000);
      }
    });    // 添加状态同步相关的事件监听
    video.addEventListener('loadeddata', () => {
      // 视频数据加载完成，可能需要同步状态
      if (video.readyState >= 2 && !video.seeking) {
        videoLoading.value = false;
      }
    });

    video.addEventListener('canplaythrough', () => {
      // 视频可以流畅播放，确保状态同步
      if (!video.seeking) {
        videoLoading.value = false;
      }
    });

    // 添加 seeking 相关的状态管理
    video.addEventListener('seeking', () => {
      // 开始 seeking 时，确保显示加载状态
      videoLoading.value = true;
    });

    video.addEventListener('seeked', () => {
      // seeking 完成后，检查是否真正就绪
      setTimeout(() => {
        if (video.readyState >= 2 && !video.seeking) {
          videoLoading.value = false;
        }
      }, 100); // 给一点时间让状态稳定
    });

    // 监听 readyState 变化（通过 loadstart 等事件间接检测）
    video.addEventListener('loadstart', () => {
      if (video.seeking) {
        videoLoading.value = true;
      }
    });
  }
});

onBeforeUnmount(() => {
  stopStatusSync(); // 停止状态同步
  destroyHLS();
});
</script>

<style scoped>
/* Component-specific overrides can be added here if needed */
</style>
