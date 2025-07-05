import { ref } from 'vue';
import Hls from 'hls.js';

/**
 * HLS 视频流处理 Composable
 * 专门处理 HLS 流媒体的加载、错误处理和资源清理
 */
export function useHLS() {
  const videoStatusMsg = ref('');
  const videoLoading = ref(false);
  let hlsInstance = null;
  let errorTimeout = null; // 用于错误状态自动清除的定时器
  
  // 三状态错误判断机制
  let errorStartTime = null; // 第一次出错的时间
  let consecutiveErrorCount = 0; // 连续错误次数
  const MAX_ERROR_DURATION = 30000; // 30秒后认为无法恢复
  const MAX_ERROR_COUNT = 8; // 连续8次错误后认为无法恢复
  let recoveryCheckInterval = null; // 恢复检查定时器

  /**
   * 重置错误计数和时间跟踪
   */
  function resetErrorTracking() {
    errorStartTime = null;
    consecutiveErrorCount = 0;
    if (recoveryCheckInterval) {
      clearInterval(recoveryCheckInterval);
      recoveryCheckInterval = null;
    }
  }

  /**
   * 判断错误是否已经无法恢复
   * @returns {boolean} true表示无法恢复，false表示还可以继续尝试
   */
  function isUnrecoverableError() {
    if (!errorStartTime) return false;
    
    const errorDuration = Date.now() - errorStartTime;
    return errorDuration > MAX_ERROR_DURATION || consecutiveErrorCount > MAX_ERROR_COUNT;
  }

  /**
   * 处理错误状态（三状态逻辑）
   * @param {string} errorType - 错误类型
   * @param {boolean} isFatal - 是否是致命错误
   */
  function handleErrorState(errorType, isFatal = false) {
    // 记录错误
    if (!errorStartTime) {
      errorStartTime = Date.now();
    }
    consecutiveErrorCount++;
    
    if (isFatal || isUnrecoverableError()) {
      // 状态3：无法恢复的错误
      videoStatusMsg.value = '播放失败，请检查视频链接';
      videoLoading.value = false;
      resetErrorTracking();
    } else {
      // 状态2：加载中（可恢复）
      videoStatusMsg.value = '加载中...';
      videoLoading.value = true;
      
      // 启动恢复检查定时器
      if (!recoveryCheckInterval) {
        recoveryCheckInterval = setInterval(() => {
          if (isUnrecoverableError()) {
            videoStatusMsg.value = '播放失败，请检查视频链接';
            videoLoading.value = false;
            resetErrorTracking();
          }
        }, 5000); // 每5秒检查一次
      }
    }
  }  /**
   * 清除错误状态（如果视频正在正常播放）
   * @param {HTMLVideoElement} videoElement - 视频元素
   */
  function clearErrorIfPlaying(videoElement) {
    if (videoElement && !videoElement.paused && !videoElement.ended && 
        videoElement.readyState >= 2 && !videoElement.seeking) {
      // 状态1：正常播放
      videoStatusMsg.value = '';
      videoLoading.value = false;
      resetErrorTracking(); // 重置错误跟踪
      
      if (errorTimeout) {
        clearTimeout(errorTimeout);
        errorTimeout = null;
      }
    }
  }

  /**
   * 设置延迟清除错误状态
   * @param {HTMLVideoElement} videoElement - 视频元素
   * @param {number} delay - 延迟时间（毫秒）
   */
  function scheduleErrorClear(videoElement, delay = 3000) {
    if (errorTimeout) {
      clearTimeout(errorTimeout);
    }
    errorTimeout = setTimeout(() => {
      clearErrorIfPlaying(videoElement);
    }, delay);
  }

  /**
   * 加载 HLS 视频源
   * @param {HTMLVideoElement} videoElement - 视频元素
   * @param {string} url - 视频 URL
   * @param {Object} options - 选项配置
   */
  function loadHLSSource(videoElement, url, options = {}) {
    if (!videoElement || !url) return;

    // 清理旧的实例
    destroyHLS();
    
    videoStatusMsg.value = "";
    videoLoading.value = true;

    if (url.endsWith('.m3u8')) {
      // HLS 流媒体处理
      if (Hls.isSupported()) {
        hlsInstance = new Hls();
        hlsInstance.loadSource(url);
        hlsInstance.attachMedia(videoElement);        hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
          // MANIFEST_PARSED只表示清单解析完成，不表示视频数据就绪
          // 保持加载状态，等待实际视频数据加载完成
          resetErrorTracking(); // 重置错误跟踪
          
          if (options.autoPlay) {
            videoElement.play().catch(e => {
              console.warn('Auto play failed:', e);
            });
          }
        });

        // HLS 就绪状态检测 - 基于实际视频数据加载情况
        hlsInstance.on(Hls.Events.LEVEL_LOADED, () => {
          // 播放列表加载完成，检查视频是否真正就绪
          if (videoElement.readyState >= 2 && videoElement.duration > 0) {
            videoLoading.value = false;
            videoStatusMsg.value = "";
          }
        });

        hlsInstance.on(Hls.Events.FRAG_LOADED, () => {
          // 第一个片段加载完成，通常表示可以播放
          if (videoElement.readyState >= 2 && videoElement.duration > 0) {
            videoLoading.value = false;
            videoStatusMsg.value = "";
          }
        });

        // 添加视频元素的 loadeddata 事件监听，作为备用就绪检测
        const onLoadedData = () => {
          if (videoElement.readyState >= 2 && videoElement.duration > 0) {
            videoLoading.value = false;
            videoStatusMsg.value = "";
            videoElement.removeEventListener('loadeddata', onLoadedData);
          }
        };
        videoElement.addEventListener('loadeddata', onLoadedData);

        hlsInstance.on(Hls.Events.ERROR, (event, data) => {
          console.log('HLS error:', data.type, 'fatal:', data.fatal);
          
          // 使用三状态错误处理逻辑
          handleErrorState(data.type, data.fatal);
        });

        // 监听恢复相关事件
        hlsInstance.on(Hls.Events.FRAG_LOADED, () => {
          // 片段加载成功，可能表示已恢复
          setTimeout(() => clearErrorIfPlaying(videoElement), 1000);
        });

        hlsInstance.on(Hls.Events.LEVEL_LOADED, () => {
          // 播放列表加载成功，可能表示已恢复
          setTimeout(() => clearErrorIfPlaying(videoElement), 500);
        });

        hlsInstance.on(Hls.Events.FRAG_PARSING_DATA, () => {
          // 片段解析成功，表示数据流恢复
          clearErrorIfPlaying(videoElement);
        });
      } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
        // iOS Safari 原生支持
        videoElement.src = url;
        videoLoading.value = false;
        if (options.autoPlay) {
          videoElement.play().catch(e => {
            console.warn('Auto play failed:', e);
          });
        }
      } else {
        videoStatusMsg.value = '当前浏览器不支持 HLS(m3u8) 播放';
        videoLoading.value = false;
      }
    } else {
      // 普通视频文件处理
      videoElement.src = url;
      videoLoading.value = false;
      if (options.autoPlay) {
        videoElement.play().catch(e => {
          console.warn('Auto play failed:', e);
        });
      }
    }
  }
  /**
   * 销毁 HLS 实例
   */  function destroyHLS() {
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }
    if (errorTimeout) {
      clearTimeout(errorTimeout);
      errorTimeout = null;
    }
    resetErrorTracking(); // 重置错误跟踪状态
  }

  /**
   * 检查是否支持 HLS
   */
  function isHLSSupported() {
    return Hls.isSupported();
  }

  /**
   * 获取当前 HLS 实例
   */
  function getHLSInstance() {
    return hlsInstance;
  }  /**
   * 手动清除错误状态
   */
  function clearErrorStatus() {
    videoStatusMsg.value = '';
    videoLoading.value = false;
    resetErrorTracking(); // 重置错误跟踪状态
    if (errorTimeout) {
      clearTimeout(errorTimeout);
      errorTimeout = null;
    }
  }

  return {
    // 状态
    videoStatusMsg,
    videoLoading,
    
    // 方法
    loadHLSSource,
    destroyHLS,
    clearErrorStatus,
    isHLSSupported,
    getHLSInstance
  };
}
