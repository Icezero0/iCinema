import { ref, computed } from 'vue';
import { connectWebSocket, isWebSocketConnected, getWebSocket, wsDebugMsgList } from '@/utils/ws';
import { checkAccessToken } from '@/utils/auth';

export function useWebSocketStatus() {
  const wsStatus = ref('disconnected');
  // computed 依赖 wsDebugMsgList.value，保证响应式
  const wsDebugMsg = computed(() => wsDebugMsgList.value.join('\n'));

  function updateWsStatusAndDebug() {
    const ws = getWebSocket();
    if (!ws) {
      wsStatus.value = 'disconnected';
    } else if (ws.readyState === WebSocket.CONNECTING) {
      wsStatus.value = 'connecting';
    } else if (ws.readyState === WebSocket.OPEN) {
      wsStatus.value = 'connected';
    } else {
      wsStatus.value = 'disconnected';
    }
  }

  function setupWebSocket() {
    if (!isWebSocketConnected()) {
      connectWebSocket({
        onStatusChange: (status) => {
          wsStatus.value = status;
        },
        onAuthError: async () => {
          const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
          if (accessToken) {
            await checkAccessToken(accessToken);
          }
        }
      });
    } else {
      updateWsStatusAndDebug();
    }
  }

  return {
    wsStatus,
    wsDebugMsg,
    setupWebSocket,
    updateWsStatusAndDebug
  };
}
