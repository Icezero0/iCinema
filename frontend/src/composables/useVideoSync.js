import { ref } from 'vue';
import { getWebSocket } from '@/utils/ws';

/**
 * 视频同步 Composable
 * 专门处理房间内视频播放同步的 WebSocket 消息
 */
export function useVideoSync() {
  const toastVisible = ref(false);
  const toastMsg = ref('');
  
  // 自动播放提示相关状态
  const autoPlayBlocked = ref(false);
  const pendingPlayInfo = ref(null); // 存储待播放的信息

  /**
   * 发送 WebSocket 视频操作消息
   * @param {string} type - 消息类型
   * @param {Object} payload - 消息负载
   */
  function sendVideoMessage(type, payload) {
    const ws = getWebSocket();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type, payload }));
    }
  }  /**
   * 同步播放操作
   * @param {number} roomId - 房间ID
   * @param {number} userId - 用户ID
   * @param {number} progress - 播放进度（发送给后端保存）
   */
  function syncPlay(roomId, userId, progress = 0) {
    sendVideoMessage('set_vedio_start', {
      room_id: roomId,
      sender_id: userId,
      timestamp: Date.now(),
      progress
    });
  }  /**
   * 同步暂停操作
   * @param {number} roomId - 房间ID
   * @param {number} userId - 用户ID
   * @param {number} progress - 播放进度（发送给后端保存）
   */
  function syncPause(roomId, userId, progress = 0) {
    sendVideoMessage('set_vedio_pause', {
      room_id: roomId,
      sender_id: userId,
      timestamp: Date.now(),
      progress
    });
  }

  /**
   * 同步跳转操作
   * @param {number} roomId - 房间ID
   * @param {number} userId - 用户ID
   * @param {number} timeOffset - 时间偏移
   */
  function syncSeek(roomId, userId, timeOffset) {
    sendVideoMessage('set_vedio_jump', {
      room_id: roomId,
      sender_id: userId,
      video_time_offset: timeOffset,
      timestamp: Date.now()
    });
  }

  /**
   * 同步视频URL设置
   * @param {number} roomId - 房间ID
   * @param {number} userId - 用户ID
   * @param {string} url - 视频URL
   */
  function syncVideoUrl(roomId, userId, url) {
    sendVideoMessage('set_vedio_url', {
      room_id: roomId,
      sender_id: userId,
      url,
      timestamp: Date.now()
    });
  }  /**
   * 显示同步操作提示
   * @param {string} message - 提示消息
   */
  function showSyncToast(message) {
    console.log('显示同步提示:', message); // 添加调试信息
    toastMsg.value = message;
    toastVisible.value = false; // 先隐藏
    // 使用 nextTick 确保重新显示
    setTimeout(() => {
      toastVisible.value = true;
    }, 50);
  }

  /**
   * 处理自动播放被阻止的情况
   * @param {Object} videoControls - 视频控制对象
   * @param {number} progress - 播放进度
   */
  function handleAutoPlayBlocked(videoControls, progress = 0) {
    autoPlayBlocked.value = true;
    pendingPlayInfo.value = { videoControls, progress };
    console.log('自动播放被阻止，显示用户交互提示');
  }

  /**
   * 用户点击恢复播放按钮
   */
  function resumePlayback() {
    if (pendingPlayInfo.value) {
      const { videoControls, progress } = pendingPlayInfo.value;
      
      // 先跳转到指定进度
      if (progress > 0 && videoControls.seekTo) {
        videoControls.seekTo(progress);
      }
      
      // 开始播放
      if (videoControls.play) {
        videoControls.play().then(() => {
          // 播放成功，隐藏提示
          autoPlayBlocked.value = false;
          pendingPlayInfo.value = null;
          showSyncToast('已恢复房间播放状态');
        }).catch((error) => {
          console.error('手动播放失败:', error);
          showSyncToast('播放失败，请稍后重试');
        });
      }
    }
  }/**
   * 处理接收到的视频同步消息
   * @param {Object} message - WebSocket 消息
   * @param {Object} videoControls - 视频控制对象
   * @param {Function} getUserInfo - 获取用户信息的函数
   * @param {boolean} allowProgressSync - 是否允许进度同步（房间恢复时为true，实时控制时为false）
   */
  async function handleVideoSyncMessage(message, videoControls, getUserInfo, allowProgressSync = false) {
    const { type, payload } = message;

    if (!payload) return;

    // 获取发送者信息（用于提示）
    const senderId = payload.sender_id;
    let username = '神秘用户';
    
    // 确保 senderId 存在且有效
    if (senderId && typeof senderId === 'number') {
      try {
        const userInfo = await getUserInfo(senderId);
        username = userInfo?.username || '神秘用户';
      } catch (error) {
        console.warn('Failed to get user info for senderId:', senderId, error);
      }
    } else {
      console.warn('Invalid senderId in message:', senderId);
    }    switch (type) {
      case 'set_vedio_url':
        console.log('处理视频URL设置:', payload.url);
        if (payload.url && videoControls.loadVideo) {
          videoControls.loadVideo(payload.url, { autoPlay: false });
          showSyncToast(`${username} 设置了视频地址`);
        }
        break;      case 'set_vedio_start':
        console.log('处理视频播放开始:', payload, 'allowProgressSync:', allowProgressSync);
        if (videoControls.play) {
          // 只在房间恢复时设置进度，实时控制时忽略进度信息
          if (allowProgressSync && payload.progress !== undefined && videoControls.seekTo) {
            console.log('设置播放进度:', payload.progress);
            videoControls.seekTo(payload.progress);
          } else if (!allowProgressSync) {
            console.log('实时播放控制，忽略进度信息，直接播放当前位置');
          }          console.log('开始播放视频');
          
          // 使用与房间恢复完全一致的setTimeout + async/await模式
          setTimeout(async () => {
            if (videoControls.play) {
              try {
                const playResult = videoControls.play();
                if (playResult && typeof playResult.then === 'function') {
                  await playResult;
                }
                showSyncToast(`${username} 开启了视频播放`);
              } catch (error) {
                console.log('自动播放被浏览器阻止:', error);
                // 自动播放失败，显示用户交互提示
                const progress = allowProgressSync && payload.progress !== undefined ? payload.progress : 0;
                handleAutoPlayBlocked(videoControls, progress);
              }
            }
          }, 0); // 立即执行，但使用异步上下文
        }
        break;

      case 'set_vedio_pause':
        console.log('处理视频暂停:', payload);
        if (videoControls.pause) {
          videoControls.pause();
          showSyncToast(`${username} 暂停了视频播放`);
        }
        break;      case 'set_vedio_jump':
        if (payload.video_time_offset !== undefined && videoControls.seekTo) {
          const { video_time_offset, timestamp } = payload;
          if (typeof video_time_offset === 'number' && typeof timestamp === 'number') {
            // 考虑网络延迟，计算实际播放时间
            const now = Date.now();
            const offset = video_time_offset + (now - timestamp) / 1000;
            videoControls.seekTo(offset);
            // 跳转后自动暂停
            if (videoControls.pause) {
              videoControls.pause();
            }
            showSyncToast(`${username} 调整了视频进度`);
          }
        }
        break;

      case 'room_entered':
        if (payload.room_info?.video_url && videoControls.loadVideo) {
          videoControls.loadVideo(payload.room_info.video_url, { autoPlay: false });
        }
        break;
    }
  }

  /**
   * 处理房间进入时的状态恢复
   * @param {Object} roomInfo - 房间信息
   * @param {Object} videoControls - 视频控制对象
   */  async function handleRoomStateRestore(roomInfo, videoControls) {
    if (!roomInfo) return;

    console.log('恢复房间状态:', roomInfo);

    // 恢复视频URL
    if (roomInfo.video_url && videoControls.loadVideo) {
      console.log('恢复视频URL:', roomInfo.video_url);
      videoControls.loadVideo(roomInfo.video_url, { autoPlay: false });
    }

    // 恢复播放状态
    const lastOpType = roomInfo.last_operation_type;
    const lastOpProgress = roomInfo.last_operation_progress || 0;
    const lastOpTime = roomInfo.last_operation_time;
    
    if (lastOpType === 'play') {
      console.log('恢复播放状态，原始进度:', lastOpProgress, '操作时间:', lastOpTime);
      
      // 计算实际应该播放的位置
      let actualProgress = lastOpProgress;
      if (lastOpTime) {
        const currentTime = Date.now();
        const elapsedTime = (currentTime - new Date(lastOpTime).getTime()) / 1000; // 转换为秒
        actualProgress = lastOpProgress + elapsedTime;
        console.log('经过时间:', elapsedTime, '秒，计算后的实际进度:', actualProgress);
      }
      
      // 设置进度并播放
      if (videoControls.seekTo) {
        // 确保进度不会超出视频范围，这里预设一个合理的最大值
        // 实际的duration检查会在视频加载后进行
        const safeProgress = Math.max(0, actualProgress);
        console.log('设置安全进度:', safeProgress);
        videoControls.seekTo(safeProgress);
      }        // 延迟一点开始播放，确保视频加载完成
      setTimeout(async () => {
        if (videoControls.play) {
          try {
            const playResult = videoControls.play();
            if (playResult && typeof playResult.then === 'function') {
              await playResult;
            }
            showSyncToast('已恢复房间播放状态');
          } catch (error) {
            console.log('自动播放被浏览器阻止:', error);
            // 自动播放失败，显示用户交互提示
            handleAutoPlayBlocked(videoControls, actualProgress);
          }
        }
      }, 500);
    } else if (lastOpType === 'pause' || lastOpType === 'seek') {
      console.log('恢复暂停状态，进度:', lastOpProgress);
      
      // 设置进度但不播放，保持暂停状态
      if (videoControls.seekTo) {
        videoControls.seekTo(lastOpProgress);
      }
      
      // 确保视频处于暂停状态
      setTimeout(() => {
        if (videoControls.pause) {
          videoControls.pause();
        }
      }, 500);
    }
  }  return {
    // 状态
    toastVisible,
    toastMsg,
    autoPlayBlocked,
    
    // 同步方法
    syncPlay,
    syncPause,
    syncSeek,
    syncVideoUrl,
    
    // 消息处理
    handleVideoSyncMessage,
    handleRoomStateRestore,
    showSyncToast,
    sendVideoMessage,
    
    // 自动播放处理
    resumePlayback
  };
}
