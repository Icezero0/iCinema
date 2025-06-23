<template>  <div class="custom-video-controls" :class="{ 'dark-mode': isDarkMode }">
    <button 
      @click="handlePlayToggle" 
      @mousedown="startRipple"
      @touchstart="startRipple"
      class="play-btn" 
      :disabled="!isOwner"
      ref="playBtnRef"
    >
      <span v-if="!isPlaying" class="play-icon">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
          <polygon points="8,5 19,12 8,19" />
        </svg>
      </span>
      <span v-else class="pause-icon">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
          <rect x="6" y="5" width="4" height="14"/>
          <rect x="14" y="5" width="4" height="14"/>
        </svg>
      </span>
      <span class="ripple-effect" ref="rippleRef"></span>
    </button>
    
    <!-- 进度条区域 -->
    <div class="video-progress-bar-wrap">
      <div class="video-buffer-bar">
        <template v-for="(range, idx) in bufferedRanges" :key="idx">
          <div class="buffered-segment" :style="{ left: range.start + '%', width: (range.end - range.start) + '%' }"></div>
        </template>
      </div>
      <div class="video-played-bar" :style="{ width: playedPercent + '%' }"></div>      <input
        type="range"
        min="0"
        :max="duration"
        step="0.1"
        :value="isDragging ? dragValue : (hasPendingSeek ? pendingSeekValue : currentTime)"
        @mousedown="handleSeekStart"
        @touchstart="handleSeekStart"
        @input="handleSeekInput"
        @change="handleSeekEnd"
        class="video-progress-input"
        :disabled="!isOwner"
      />
    </div>
      <!-- 时间显示 -->
    <span class="time-label">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
    
    <!-- 音量控制 (仅PC端显示) -->
    <template v-if="!isMobile">
      <span class="volume-icon">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
          <polygon points="3,9 3,15 7,15 12,20 12,4 7,9" />
          <path d="M16.5,12c0-1.77-1-3.29-2.5-4.03v8.06C15.5,15.29,16.5,13.77,16.5,12z" />
        </svg>
      </span>
      <input
        type="range"
        min="0"
        max="1"
        step="0.01"
        :value="volume"
        @input="$emit('volume-change', $event.target.value)"
        class="volume-slider"
        title="音量"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';

// Props
const props = defineProps({
  isPlaying: {
    type: Boolean,
    default: false
  },
  currentTime: {
    type: Number,
    default: 0
  },
  duration: {
    type: Number,
    default: 0
  },
  volume: {
    type: Number,
    default: 1
  },
  bufferedRanges: {
    type: Array,
    default: () => []
  },
  playedPercent: {
    type: Number,
    default: 0
  },
  isOwner: {
    type: Boolean,
    required: true
  },  isDarkMode: {
    type: Boolean,
    default: false
  },
  isMobile: {
    type: Boolean,
    default: false
  }
});

// Emits
const emit = defineEmits([
  'toggle-play',
  'seek',
  'volume-change'
]);

// 模板引用
const playBtnRef = ref(null);
const rippleRef = ref(null);

// 本地状态
const isDragging = ref(false);
const dragValue = ref(0);
const hasPendingSeek = ref(false); // 是否有待处理的跳转
const pendingSeekValue = ref(0); // 待处理的跳转值

// 播放/暂停按钮点击处理
function handlePlayToggle() {
  if (!props.isOwner) return;
  emit('toggle-play');
}

// 波纹效果处理
function startRipple(event) {
  if (!props.isOwner || !rippleRef.value) return;
  
  const ripple = rippleRef.value;
  const btn = playBtnRef.value;
  
  // 重置波纹样式
  ripple.style.left = '';
  ripple.style.top = '';
  ripple.style.width = '';
  ripple.style.height = '';
  ripple.classList.remove('ripple-animate');
  
  // 获取按钮和点击位置信息
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  
  let x, y;
  if (event.type === 'touchstart') {
    const touch = event.touches[0];
    x = touch.clientX - rect.left;
    y = touch.clientY - rect.top;
  } else {
    x = event.clientX - rect.left;
    y = event.clientY - rect.top;
  }
  
  // 设置波纹位置和大小
  ripple.style.left = (x - size / 2) + 'px';
  ripple.style.top = (y - size / 2) + 'px';
  ripple.style.width = size + 'px';
  ripple.style.height = size + 'px';
  
  // 触发动画
  requestAnimationFrame(() => {
    ripple.classList.add('ripple-animate');
  });
}

// 处理拖拽开始
function handleSeekStart(event) {
  if (!props.isOwner) return;
  isDragging.value = true;
  dragValue.value = parseFloat(event.target.value);
}

// 处理拖拽过程
function handleSeekInput(event) {
  if (!props.isOwner) return;
  dragValue.value = parseFloat(event.target.value);
}

// 处理拖拽结束
function handleSeekEnd(event) {
  if (!props.isOwner) return;
  const newTime = parseFloat(event.target.value);
  
  // 设置待处理状态
  hasPendingSeek.value = true;
  pendingSeekValue.value = newTime;
  dragValue.value = newTime;
  
  // 立即结束拖拽状态，但保持显示跳转值
  isDragging.value = false;
  
  emit('seek', newTime);
}

// 时间格式化函数
function formatTime(seconds) {
  if (isNaN(seconds) || seconds < 0) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// 监听 currentTime 变化，智能重置待处理状态
watch(() => props.currentTime, (newTime) => {
  if (hasPendingSeek.value) {
    // 如果当前时间接近我们跳转的目标时间，说明跳转完成了
    if (Math.abs(newTime - pendingSeekValue.value) < 0.5) {
      hasPendingSeek.value = false;
      pendingSeekValue.value = 0;
    }
  }
});
</script>

<style scoped>
.custom-video-controls {
  width: 100%;
  max-width: 640px;
  margin: 0 auto 8px auto;
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255,255,255,0.95);
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
  padding: 8px 16px;
}
.custom-video-controls.dark-mode {
  background: rgba(35,40,58,0.98);
}
.play-btn {
  background: #1976d2;
  border: none;
  border-radius: 50%;
  width: 35px;
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: #fff;
  cursor: pointer;
  outline: none;
  box-shadow: 0 2px 8px rgba(25,118,210,0.10);
  transition: all 0.25s cubic-bezier(0.4, 0.0, 0.2, 1);
  position: relative;
  overflow: hidden;
  -webkit-tap-highlight-color: transparent;
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
  /* 完全去除默认的焦点样式 */
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  /* 防止任何包裹框 */
  border: 0;
  padding: 0;
  margin: 0;
}

.play-btn:hover {
  background: #1565c0;
  box-shadow: 0 4px 16px rgba(25,118,210,0.20);
  transform: scale(1.05);
}

.play-btn:active {
  background: #0d47a1;
  transform: scale(0.96);
  box-shadow: 0 2px 8px rgba(25,118,210,0.25);
  transition: all 0.15s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.play-btn:focus {
  outline: none !important;
  border: none !important;
  box-shadow: 0 2px 8px rgba(25,118,210,0.10), 0 0 0 2px rgba(25,118,210,0.3);
}

.play-btn:focus:not(:focus-visible) {
  box-shadow: 0 2px 8px rgba(25,118,210,0.10);
}

.play-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  opacity: 0.6;
  transform: none !important;
  box-shadow: none;
}

/* 波纹效果 */
.ripple-effect {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  pointer-events: none;
  transform: scale(0);
  opacity: 0;
  transition: none;
}

.ripple-effect.ripple-animate {
  animation: ripple-animation 0.6s cubic-bezier(0.4, 0.0, 0.2, 1);
}

@keyframes ripple-animation {
  0% {
    transform: scale(0);
    opacity: 0.8;
  }
  50% {
    opacity: 0.4;
  }
  100% {
    transform: scale(1);
    opacity: 0;
  }
}
.custom-video-controls.dark-mode .play-btn {
  background: #1976d2;
  color: #fff;
}

.custom-video-controls.dark-mode .play-btn:hover {
  background: #42a5f5;
}

.custom-video-controls.dark-mode .play-btn:focus {
  box-shadow: 0 0 0 2px rgba(66, 165, 245, 0.4);
}

.custom-video-controls.dark-mode .play-btn:disabled {
  background: #444;
  color: #888;
}

/* 播放/暂停图标动画 */
.play-icon,
.pause-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 2;
  transition: transform 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.play-btn:active .play-icon,
.play-btn:active .pause-icon {
  transform: scale(0.9);
}

.play-icon svg,
.pause-icon svg {
  transition: transform 0.25s cubic-bezier(0.4, 0.0, 0.2, 1);
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.1));
}

/* 图标切换动画 */
.play-icon {
  animation: iconFadeIn 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.pause-icon {
  animation: iconFadeIn 0.3s cubic-bezier(0.4, 0.0, 0.2, 1);
}

@keyframes iconFadeIn {
  0% {
    opacity: 0;
    transform: scale(0.8);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

/* 移动端优化 */
@media (max-width: 768px) {
  .play-btn {
    width: 40px;
    height: 40px;
    -webkit-tap-highlight-color: transparent;
    /* 移动端额外的触摸优化 */
    touch-action: manipulation;
  }
  
  .play-btn:hover {
    transform: none; /* 移动端禁用hover缩放 */
    background: #1976d2; /* 保持原色 */
    box-shadow: 0 2px 8px rgba(25,118,210,0.10);
  }
  
  .play-btn:active {
    transform: scale(0.92);
    background: #0d47a1;
    transition: all 0.1s cubic-bezier(0.4, 0.0, 0.2, 1);
  }
  
  /* 移动端波纹效果调整 */
  .ripple-effect.ripple-animate {
    animation: ripple-animation-mobile 0.4s cubic-bezier(0.4, 0.0, 0.2, 1);
  }
  
  @keyframes ripple-animation-mobile {
    0% {
      transform: scale(0);
      opacity: 0.6;
    }
    50% {
      opacity: 0.3;
    }
    100% {
      transform: scale(1);
      opacity: 0;
    }
  }
  
  /* 移动端进度条优化 */
  .video-progress-bar-wrap {
    height: 20px; /* 增加触摸区域 */
    margin: 0 6px;
  }
  
  .video-progress-input {
    height: 20px;
    touch-action: manipulation;
  }
    .video-progress-input::-webkit-slider-thumb {
    width: 16px;
    height: 16px;
    margin-top: -5px;
    transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
  }
  
  .video-progress-input::-moz-range-thumb {
    width: 16px;
    height: 16px;
  }
  
  /* 移动端禁用hover效果，但保留active效果 */
  .video-progress-input:hover::-webkit-slider-thumb {
    transform: none;
    box-shadow: 0 1px 4px rgba(25,118,210,0.18);
  }
  
  .video-progress-input:hover::-moz-range-thumb {
    transform: none;
    box-shadow: 0 1px 4px rgba(25,118,210,0.18);
  }
  
  .video-progress-input:active::-webkit-slider-thumb {
    transform: scale(1.1);
    box-shadow: 0 2px 8px rgba(25,118,210,0.3);
  }
  
  .video-progress-input:active::-moz-range-thumb {
    transform: scale(1.1);
    box-shadow: 0 2px 8px rgba(25,118,210,0.3);
  }
  
  .time-label {
    font-size: 12px;
  }
}
.video-progress-bar-wrap {
  position: relative;
  flex: 1 1 0;
  height: 16px;
  margin: 0 8px;
  display: flex;
  align-items: center;
}
.video-buffer-bar {
  position: absolute;
  left: 0; top: 50%;
  width: 100%; height: 6px;
  background: #eee;
  border-radius: 3px;
  transform: translateY(-50%);
  z-index: 1;
  overflow: hidden;
}
.custom-video-controls.dark-mode .video-buffer-bar {
  background: #444;
}
.buffered-segment {
  position: absolute;
  top: 0; height: 100%;
  background: #bbb;
  border-radius: 3px;
  z-index: 2;
}
.custom-video-controls.dark-mode .buffered-segment {
  background: #888;
}
.video-played-bar {
  position: absolute;
  left: 0; top: 50%;
  height: 6px;
  background: #1976d2;
  border-radius: 3px;
  transform: translateY(-50%);
  z-index: 3;
  pointer-events: none;
}
.video-progress-input {
  position: relative;
  width: 100%;
  height: 16px;
  background: transparent;
  z-index: 4;
  appearance: none;
  outline: none;
  margin: 0;
  padding: 0;
  -webkit-tap-highlight-color: transparent;
}

.video-progress-input::-webkit-slider-thumb {
  appearance: none;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #1976d2;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(25,118,210,0.18);
  cursor: pointer;
  margin-top: -4px;
  transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.video-progress-input::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #1976d2;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(25,118,210,0.18);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
}

.video-progress-input::-ms-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #1976d2;
  border: 2px solid #fff;
  box-shadow: 0 1px 4px rgba(25,118,210,0.18);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0.0, 0.2, 1);
}

/* 进度条滑块hover效果 */
.video-progress-input:hover::-webkit-slider-thumb {
  transform: scale(1.2);
  box-shadow: 0 2px 8px rgba(25,118,210,0.3);
}

.video-progress-input:active::-webkit-slider-thumb {
  transform: scale(1.3);
  box-shadow: 0 2px 12px rgba(25,118,210,0.4);
}

.video-progress-input:hover::-moz-range-thumb {
  transform: scale(1.2);
  box-shadow: 0 2px 8px rgba(25,118,210,0.3);
}

.video-progress-input:active::-moz-range-thumb {
  transform: scale(1.3);
  box-shadow: 0 2px 12px rgba(25,118,210,0.4);
}
.video-progress-input::-webkit-slider-runnable-track {
  height: 6px;
  background: transparent;
}
.video-progress-input::-ms-fill-lower,
.video-progress-input::-ms-fill-upper {
  background: transparent;
}
.video-progress-input:focus {
  outline: none;
}
.volume-slider {
  width: 80px;
  accent-color: #1976d2;
  height: 4px;
}
.time-label {
  font-size: 13px;
  color: #666;
  min-width: 70px;
  text-align: right;
}
.custom-video-controls.dark-mode .time-label {
  color: #90caf9;
}
.volume-icon svg {
  color: inherit;
}
.custom-video-controls.dark-mode .volume-icon svg {
  color: #fff;
}

/* Mobile Responsive Styles */
@media (max-width: 768px) {
  .custom-video-controls {
    gap: 8px;
    padding: 8px 12px;
    border-radius: 6px;
    background: rgba(30, 30, 30, 0.95);
    box-shadow: none;
    border: 1px solid rgba(255, 255, 255, 0.15);
  }

  .custom-video-controls.dark-mode {
    background: rgba(30, 30, 30, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.15);
  }  .play-btn {
    width: 28px;
    height: 28px;
    min-width: 28px;
    min-height: 28px;
    font-size: 24px;
    flex-shrink: 0;
    border-radius: 50%;
    /* 移动端卡片样式的额外优化 */
    background: #1976d2;
    box-shadow: 0 1px 3px rgba(25,118,210,0.15);
  }

  .play-btn:active {
    background: #0d47a1;
    transform: scale(0.9);
    box-shadow: 0 1px 2px rgba(25,118,210,0.2);
  }

  .play-btn:disabled {
    background: #666;
    box-shadow: none;
  }

  .play-btn svg {
    width: 16px;
    height: 16px;
  }

  .time-label {
    font-size: 11px;
    min-width: 60px;
    color: #ccc;
  }

  .custom-video-controls.dark-mode .time-label {
    color: #ccc;
  }

  .video-progress-bar-wrap {
    margin: 0 4px;
  }

  .video-buffer-bar {
    background: #555;
  }

  .custom-video-controls.dark-mode .video-buffer-bar {
    background: #555;
  }

  .buffered-segment {
    background: #888;
  }

  .custom-video-controls.dark-mode .buffered-segment {
    background: #888;
  }

  .video-progress-input::-webkit-slider-thumb {
    width: 12px;
    height: 12px;
  }

  .video-progress-input::-moz-range-thumb {
    width: 12px;
    height: 12px;
  }

  .video-progress-input::-ms-thumb {
    width: 12px;
    height: 12px;
  }
}
</style>
