import { ref, computed } from 'vue';

/**
 * 视频播放器核心逻辑 Composable
 * 提供基础的播放器状态管理和控制功能
 */
export function useVideoPlayer() {
  // 播放器状态
  const videoRef = ref(null);
  const isPlaying = ref(false);
  const currentTime = ref(0);
  const duration = ref(0);
  const volume = ref(1);
  const videoLoading = ref(false);
  const bufferedRanges = ref([]);

  // 计算属性
  const playedPercent = computed(() => 
    duration.value ? (currentTime.value / duration.value) * 100 : 0
  );
  // 播放/暂停切换
  function togglePlay() {
    const video = videoRef.value;
    if (!video) return;
    
    if (video.paused) {
      return play();
    } else {
      return pause();
    }
  }

  // 播放视频 - 返回Promise以便处理自动播放失败
  function play() {
    const video = videoRef.value;
    if (!video) return Promise.reject(new Error('Video element not found'));
    
    return video.play();
  }

  // 暂停视频
  function pause() {
    const video = videoRef.value;
    if (!video) return;
    
    video.pause();
  }

  // 跳转到指定时间
  function seekTo(time) {
    const video = videoRef.value;
    if (video) {
      video.currentTime = time;
    }
  }

  // 设置音量
  function setVolume(newVolume) {
    const video = videoRef.value;
    if (video) {
      volume.value = newVolume;
      video.volume = newVolume;
    }
  }

  // 格式化时间显示
  function formatTime(t) {
    t = Math.floor(t || 0);
    const m = String(Math.floor(t / 60)).padStart(2, '0');
    const s = String(Math.floor(t % 60)).padStart(2, '0');
    return `${m}:${s}`;
  }

  // 更新缓冲区信息
  function updateBuffered() {
    const video = videoRef.value;
    if (!video || !duration.value) {
      bufferedRanges.value = [];
      return;
    }
    
    const ranges = [];
    for (let i = 0; i < video.buffered.length; i++) {
      const start = (video.buffered.start(i) / duration.value) * 100;
      const end = (video.buffered.end(i) / duration.value) * 100;
      ranges.push({ start, end });
    }
    bufferedRanges.value = ranges;
  }
  // 初始化视频事件监听器
  function initVideoEvents() {
    const video = videoRef.value;
    if (!video) return;

    video.addEventListener('timeupdate', () => {
      currentTime.value = video.currentTime;
    });

    video.addEventListener('durationchange', () => {
      duration.value = video.duration || 0;
    });

    video.addEventListener('play', () => {
      isPlaying.value = true;
    });

    video.addEventListener('pause', () => {
      isPlaying.value = false;
    });    video.addEventListener('waiting', () => {
      videoLoading.value = true;
    });

    video.addEventListener('playing', () => {
      videoLoading.value = false;
    });

    // 添加 seeking 相关事件监听
    video.addEventListener('seeking', () => {
      // 用户开始拖拽进度条，设置加载状态
      videoLoading.value = true;
    });

    video.addEventListener('seeked', () => {
      // 跳转完成，但需要检查是否真正就绪
      if (video.readyState >= 2) {
        videoLoading.value = false;
      }
      // 如果数据不足，保持加载状态，等待其他事件
    });

    // 添加更多可以表示视频就绪的事件
    video.addEventListener('canplay', () => {
      // 视频可以开始播放（但可能需要缓冲）
      if (video.readyState >= 3) {
        videoLoading.value = false;
      }
    });

    video.addEventListener('canplaythrough', () => {
      // 视频可以流畅播放到结束
      videoLoading.value = false;
    });

    video.addEventListener('loadeddata', () => {
      // 视频的首帧已经加载
      if (video.readyState >= 2) {
        videoLoading.value = false;
      }
    });

    video.addEventListener('progress', updateBuffered);
    video.addEventListener('durationchange', updateBuffered);
    video.addEventListener('timeupdate', updateBuffered);

    // 设置初始音量
    video.volume = volume.value;
  }
  return {
    // 状态
    videoRef,
    isPlaying,
    currentTime,
    duration,
    volume,
    videoLoading,
    bufferedRanges,
    playedPercent,
    
    // 方法
    togglePlay,
    play,
    pause,
    seekTo,
    setVolume,
    formatTime,
    updateBuffered,
    initVideoEvents
  };
}
