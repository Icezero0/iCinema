import { ref } from 'vue';

// 全局唯一 WebSocket 实例和管理工具

let ws = null;
let heartbeatTimer = null;
let reconnectTimer = null;
// 用ref包装，保证响应式
export const wsDebugMsgList = ref([]);

export function getWebSocket() {
  return ws;
}

export function isWebSocketConnected() {
  return ws && ws.readyState === WebSocket.OPEN;
}

export function connectWebSocket({
  onStatusChange,
  onAuthError
} = {}) {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    // 已有连接或正在连接，直接返回
    return ws;
  }
  const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
  if (!accessToken) {
    onStatusChange && onStatusChange('disconnected');
    return null;
  }
  onStatusChange && onStatusChange('connecting');
  const wsBaseUrl = `ws${location.protocol === 'https:' ? 's' : ''}://${location.hostname}:8000`;
  ws = new WebSocket(`${wsBaseUrl}/ws`);
  ws.onopen = () => {
    onStatusChange && onStatusChange('connected');
    ws.send(JSON.stringify({ type: 'authorization', token: accessToken }));
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
      }
    }, 30000);
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };
  ws.onclose = () => {
    onStatusChange && onStatusChange('disconnected');
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    if (!accessToken) {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      return;
    }
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectWebSocket({ onStatusChange, onAuthError });
      }, 3000);
    }
  };
  ws.onerror = () => {
    onStatusChange && onStatusChange('disconnected');
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
    const accessToken = document.cookie.split('; ').find(row => row.startsWith('accesstoken='))?.split('=')[1];
    if (!accessToken) {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      return;
    }
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connectWebSocket({ onStatusChange, onAuthError });
      }, 3000);
    }
  };
  ws.onmessage = async (event) => {
    appendWsDebugMsg(event.data);
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'auth_error') {
        onAuthError && onAuthError();
      }
    } catch (e) {}
  };
  return ws;
}

export function closeWebSocket() {
  if (ws) {
    ws.onopen = null;
    ws.onclose = null;
    ws.onerror = null;
    ws.onmessage = null;
    ws.close();
    ws = null;
  }
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

export function appendWsDebugMsg(msg) {
  wsDebugMsgList.value.unshift(msg);
  // 可限制最大长度，如100条
  if (wsDebugMsgList.value.length > 100) wsDebugMsgList.value.length = 100;
}

export function getWsDebugMsgList() {
  return wsDebugMsgList.value;
}

export function clearWsDebugMsgList() {
  wsDebugMsgList.value = [];
}
