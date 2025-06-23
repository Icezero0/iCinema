<template>  <div class="video-status-debug" :class="{ 'dark-mode': isDarkMode }">
    <!-- 状态标签和显示 -->
    <div class="status-container">
      <span class="status-label">视频状态:</span>
      <span class="status-main" :class="statusClass">
        {{ displayStatus }}
      </span>
    </div>
    
    <!-- 错误信息显示（如果有） -->
    <div v-if="statusMessage && statusMessage.trim()" class="error-message">
      {{ statusMessage }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

// Props
const props = defineProps({
  statusMessage: {
    type: String,
    default: ''
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  isDarkMode: {
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

// 计算主要状态
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
  'status-error': props.statusMessage && props.statusMessage.trim(),
  'dark-mode': props.isDarkMode
}));
</script>

<style scoped>
.video-status-debug {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #e0e6ed;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 8px 0;
  font-size: 14px;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.video-status-debug.dark-mode {
  background: rgba(35, 40, 58, 0.95);
  border-color: #23283a;
  color: #e0e6ed;
}

.status-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.status-label {
  font-size: 14px;
  font-weight: 500;
  color: #666;
  white-space: nowrap;
}

.dark-mode .status-label {
  color: #b0b0b0;
}

.status-main {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 16px;
  text-align: center;
  min-width: 60px;
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

.dark-mode .status-ready {
  color: #4caf50;
  background: rgba(76, 175, 80, 0.2);
}

.dark-mode .status-loading {
  color: #90caf9;
  background: rgba(144, 202, 249, 0.2);
}

.dark-mode .status-error {
  color: #ffb4b4;
  background: rgba(255, 180, 180, 0.2);
}

.error-message {
  font-size: 13px;
  color: #d32f2f;
  text-align: center;
  background: rgba(211, 47, 47, 0.1);
  padding: 6px 8px;
  border-radius: 4px;
  border-left: 3px solid #d32f2f;
  margin-top: 8px;
}

.dark-mode .error-message {
  color: #ffb4b4;
  background: rgba(255, 180, 180, 0.1);
  border-left-color: #ffb4b4;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .status-container {
    flex-direction: column;
    gap: 4px;
    align-items: center;
  }
  
  .video-status-debug {
    margin: 8px 16px;
    padding: 10px 12px;
  }
}
</style>
