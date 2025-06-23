<template>
  <div class="chat-area">    <!-- 聊天消息区域 -->
    <ChatMessages 
      :messages="messages"
      :loading-history="loadingHistory"
      @scroll="handleChatScroll"
      @load-more-with-position="handleLoadMoreWithPosition"
      ref="chatMessagesRef"
    />
    
    <!-- 聊天输入区域 -->
    <ChatInput 
      :disabled="!canSendMessage"
      @send="handleSendMessage"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import ChatMessages from './ChatMessages.vue';
import ChatInput from './ChatInput.vue';

// Props
const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  roomId: {
    type: [String, Number],
    required: true
  },
  userId: {
    type: [String, Number],
    required: true
  },
  loadingHistory: {
    type: Boolean,
    default: false
  }
});

// Emits
const emit = defineEmits([
  'send-message',
  'load-history-with-callback',
  'chat-scroll'
]);

// 响应式数据
const chatMessagesRef = ref(null);

// 计算属性
const canSendMessage = computed(() => {
  return props.roomId && props.userId;
});

// 方法
function handleChatScroll(event) {
  emit('chat-scroll', event);
}

function handleLoadMoreWithPosition(callback) {
  emit('load-history-with-callback', callback);
}

function handleSendMessage(content) {
  if (!content.trim() || !canSendMessage.value) return;
  emit('send-message', content);
}

// 暴露方法给父组件
defineExpose({
  scrollToBottom: () => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollToBottom();
    }
  },
  preserveScrollPosition: (callback) => {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.preserveScrollPosition(callback);
    }
  },
  isUserAtBottom: () => {
    return chatMessagesRef.value ? chatMessagesRef.value.isUserAtBottom() : true;
  }
});
</script>

<style scoped>
@import '@/styles/components/chat/chat-area.css';
</style>
