<template>
  <form class="video-form" :class="{ 'dark-mode': isDarkMode }">
    <div class="form-group">
      <label for="video-url">视频外链：</label>
      <input
        id="video-url"
        :value="videoUrl"
        @input="$emit('update:video-url', $event.target.value)"
        :disabled="!isOwner"
        type="text"
        placeholder="请输入视频外链地址"
        class="video-url-input"
      />
      <button
        type="button"
        class="video-url-confirm-btn"
        @click="$emit('confirm-url')"
        :disabled="!isValidVideoUrl || (!isOwner && videoUrl !== confirmedUrl)"
        style="margin-left:8px;"
      >确认</button>
    </div>
    
    <!-- 视频状态显示 -->
    <div class="status-row">
      <span class="status-label">视频状态:</span>
      <span class="status-value" :class="statusClass">
        {{ displayStatus }}
      </span>
      <!-- 错误信息显示（如果有） -->
      <span v-if="statusMessage && statusMessage.trim()" class="error-info">
        - {{ statusMessage }}
      </span>
    </div>
  </form>
</template>

<script setup>
import { computed } from 'vue';

// Props
const props = defineProps({
  videoUrl: {
    type: String,
    default: ''
  },
  confirmedUrl: {
    type: String,
    default: ''
  },
  isOwner: {
    type: Boolean,
    required: true
  },
  isDarkMode: {
    type: Boolean,
    default: false
  },
  // 视频状态相关props
  statusMessage: {
    type: String,
    default: ''
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  isPlaying: {
    type: Boolean,
    default: false
  },
  videoLoading: {
    type: Boolean,
    default: false
  }
});

// Emits
defineEmits([
  'update:video-url',
  'confirm-url'
]);

// 计算属性
const isValidVideoUrl = computed(() => {
  if (!props.videoUrl) return false;
  const url = props.videoUrl.trim();
  return /^https?:\/\/.+\.(mp4|webm|ogg|m3u8)(\?.*)?$/i.test(url);
});

// 计算视频状态显示
const displayStatus = computed(() => {
  if (props.statusMessage && props.statusMessage.trim()) {
    return '错误';
  }
  if (props.isLoading || props.videoLoading) {
    return '加载中';
  }
  return '就绪';
});

// 计算状态样式类
const statusClass = computed(() => ({
  'status-ready': !props.isLoading && !props.videoLoading && !props.statusMessage,
  'status-loading': props.isLoading || props.videoLoading,
  'status-error': props.statusMessage && props.statusMessage.trim()
}));
</script>

<style scoped>
.video-form {
  width: 100%;
  max-width: 640px;
  margin: 0 auto 24px auto;
  background: rgba(255,255,255,0.95);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  padding: 18px 24px 12px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.video-form.dark-mode {
  background: rgba(35,40,58,0.98);
}
.form-group {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 0px;
}
.video-url-input {
  flex: 1 1 0;
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 15px;
}
.video-url-input[disabled] {
  background: #f5f5f5;
  color: #aaa;
}
.video-form.dark-mode .video-url-input[disabled] {
  background: #23283a;
  color: #666;
}
.video-url-confirm-btn {
  padding: 6px 16px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}
.video-url-confirm-btn:disabled {
  background: #ccc;
  color: #fff;
  cursor: not-allowed;
}
.video-form.dark-mode .video-url-confirm-btn {
  background: #90caf9;
  color: #23283a;
}
.video-form.dark-mode .video-url-confirm-btn:disabled {
  background: #444a5a;
  color: #888;
}
label {
  color: #1976d2;
  font-size: 15px;
  font-weight: 500;
}
.video-form.dark-mode label {
  color: #90caf9;
}

/* 视频状态样式 */
.status-row {
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 14px;
  margin-top: 2px;
}

.status-label {
  color: #1976d2;
  font-weight: 500;
  white-space: nowrap;
  margin-right: 8px;
}

.video-form.dark-mode .status-label {
  color: #90caf9;
}

.status-value {
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 13px;
  min-width: 50px;
  text-align: center;
}

.status-ready {
  color: #28a745;
  background: rgba(40, 167, 69, 0.1);
}

.status-loading {
  color: #1976d2;
  background: rgba(25, 118, 210, 0.1);
}

.status-error {
  color: #d32f2f;
  background: rgba(211, 47, 47, 0.1);
}

.video-form.dark-mode .status-ready {
  color: #4caf50;
  background: rgba(76, 175, 80, 0.2);
}

.video-form.dark-mode .status-loading {
  color: #90caf9;
  background: rgba(144, 202, 249, 0.2);
}

.video-form.dark-mode .status-error {
  color: #ffb4b4;
  background: rgba(255, 180, 180, 0.2);
}

.error-info {
  color: #d32f2f;
  font-size: 12px;
  font-style: italic;
}

.video-form.dark-mode .error-info {
  color: #ffb4b4;
}
</style>
