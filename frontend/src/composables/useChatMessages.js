import { ref, nextTick } from 'vue';
import { API_BASE_URL } from '@/utils/api';
import { useUserInfo } from '@/composables/useUserInfo.js';
import defaultAvatar from '@/assets/default_avatar.jpg';

export function useChatMessages(roomId, userId) {
  const messages = ref([]);
  const messagePageSize = 30;
  let messageSkip = 0;
  const loadingHistory = ref(false);

  /**
   * 获取聊天消息
   * @param {Object} options - 配置选项
   * @param {boolean} options.append - 是否追加到现有消息列表
   */
  async function fetchMessages({ append = false } = {}) {
    if (!roomId.value) return;
    
    const accessToken = document.cookie
      .split('; ')
      .find(row => row.startsWith('accesstoken='))
      ?.split('=')[1];
      
    let messageSkipCopy = messageSkip;
    let loadingMessagePageSize = messagePageSize;
    
    try {
      messageSkip = Math.max(0, messageSkip - messagePageSize);
      loadingMessagePageSize = messageSkipCopy - messageSkip;
      
      if (loadingMessagePageSize <= 0) return; // 没有更多消息可加载
      
      const resp = await fetch(
        `${API_BASE_URL}/rooms/${roomId.value}/messages?skip=${messageSkip}&limit=${loadingMessagePageSize}`,
        {
          headers: { 'Authorization': `Bearer ${accessToken}` }
        }
      );
      
      if (resp.ok) {
        const data = await resp.json();
        
        // 异步补全消息用户信息
        const newMsgs = await Promise.all(
          (data.items || []).map(async msg => {
            const userInfo = await useUserInfo(msg.user_id);
            return {
              content: msg.content,
              user_id: msg.user_id,
              username: userInfo?.username || '神秘用户',
              avatar: userInfo?.avatarUrl || defaultAvatar,
              isSelf: msg.user_id === userId.value,
              timestamp: msg.timestamp
            };
          })
        );
        
        if (append) {
          messages.value = [...newMsgs, ...messages.value];
        } else {
          messages.value = newMsgs;
        }
      } else {
        messageSkip = messageSkipCopy;
      }
    } catch (e) {
      messageSkip = messageSkipCopy;
      console.error('获取消息失败:', e);
    }
  }

  /**
   * 发送聊天消息
   * @param {string} content - 消息内容
   * @param {Object} userInfo - 当前用户信息
   */
  async function sendMessage(content, userInfo) {
    if (!content.trim() || !roomId.value) return;
    
    // 先本地显示
    const newMessage = {
      content: content.trim(),
      user_id: userId.value,
      username: userInfo.username,
      avatar: userInfo.avatarUrl,
      isSelf: true,
      timestamp: Date.now()
    };
    
    messages.value.push(newMessage);
    
    // 发送到后端
    const accessToken = document.cookie
      .split('; ')
      .find(row => row.startsWith('accesstoken='))
      ?.split('=')[1];
      
    try {
      await fetch(`${API_BASE_URL}/rooms/${roomId.value}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({ content: content.trim() })
      });
    } catch (e) {
      console.error('发送消息失败:', e);
    }
  }

  /**
   * 添加接收到的消息
   * @param {Object} messageData - WebSocket 消息数据
   */
  async function addReceivedMessage(messageData) {
    const { room_id, sender_id, content, timestamp } = messageData;
    
    if (room_id !== roomId.value) return;
    
    // 获取发送者用户信息
    const userInfo = await useUserInfo(sender_id);
    
    const newMessage = {
      content,
      user_id: sender_id,
      username: userInfo?.username || '未知用户',
      avatar: userInfo?.avatarUrl || defaultAvatar,
      isSelf: sender_id === userId.value,
      timestamp
    };
    
    messages.value.push(newMessage);
  }
  /**
   * 加载历史消息
   */
  async function loadHistoryMessages() {
    if (loadingHistory.value || messageSkip <= 0) return;
    
    loadingHistory.value = true;
    await fetchMessages({ append: true });
    loadingHistory.value = false;
  }

  /**
   * 初始化消息数据
   * @param {number} totalMessages - 房间总消息数
   */
  function initializeMessages(totalMessages) {
    messageSkip = totalMessages || 0;
  }
  return {
    messages,
    loadingHistory,
    fetchMessages,
    sendMessage,
    addReceivedMessage,
    loadHistoryMessages,
    initializeMessages
  };
}
