<template>
  <div 
    class="chat-messages" 
    ref="messagesContainer"
    @scroll="handleScroll"
  >
    <div v-for="(msg, idx) in messages" :key="idx" class="chat-message" :class="{ 'self-message': msg.isSelf }">
      <MessageItem 
        :message="msg"
        :is-self="msg.isSelf"
      />
    </div>
    
    <!-- 加载历史消息指示器 -->
    <div v-if="loadingHistory" class="loading-indicator">
      <span>加载历史消息中...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue';
import MessageItem from './MessageItem.vue';

// Props
const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  loadingHistory: {
    type: Boolean,
    default: false
  }
});

// Emits
const emit = defineEmits(['scroll', 'load-more-with-position']);

// 响应式数据
const messagesContainer = ref(null);
const isUserAtBottom = ref(true); // 跟踪用户是否在底部
const scrollThreshold = 100; // 距离底部多少像素内认为是"在底部"

// 方法
function handleScroll(event) {
  const el = messagesContainer.value;
  if (!el) return;
  
  // 更新用户是否在底部的状态
  const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= scrollThreshold;
  isUserAtBottom.value = isAtBottom;
  
  if (el.scrollTop === 0 && !props.loadingHistory) {
    
    // 记录加载前的高度
    const heightBefore = el.scrollHeight;
    
    // 触发加载历史消息
    emit('load-more-with-position', () => {
      // 这个回调会在历史消息加载完成后执行
      nextTick(() => {
        if (messagesContainer.value) {
          const heightAfter = messagesContainer.value.scrollHeight;
          const heightIncrease = heightAfter - heightBefore;
          
          // 设置滚动位置为新增的高度
          messagesContainer.value.scrollTop = heightIncrease;
          
        }
      });
    });
  }
  
  emit('scroll', event);
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
}

function preserveScrollPosition(callback) {
  if (!messagesContainer.value) {
    callback();
    return;
  }
  
  // 获取更新前的滚动容器高度
  const scrollHeightBefore = messagesContainer.value.scrollHeight;
  
  // 执行回调（通常是加载历史消息）
  callback();
  
  // 等待DOM更新完成后调整滚动位置
  nextTick(() => {
    if (messagesContainer.value) {
      const scrollHeightAfter = messagesContainer.value.scrollHeight;
      const heightIncrease = scrollHeightAfter - scrollHeightBefore;
      
      // 设置滚动位置为新增的高度
      messagesContainer.value.scrollTop = heightIncrease;
    }
  });
}

// 暴露方法给父组件
defineExpose({
  scrollToBottom,
  preserveScrollPosition,
  isUserAtBottom: () => isUserAtBottom.value
});

// 组件挂载后滚动到底部
onMounted(() => {
  scrollToBottom();
});

// 监听消息变化，智能滚动处理
watch(() => props.messages, (newMessages, oldMessages) => {
  if (!oldMessages || newMessages.length === oldMessages.length) return;
  
  if (newMessages.length > oldMessages.length) {
    const addedCount = newMessages.length - oldMessages.length;
    
    // 判断是否是从头部加载的历史消息（通常历史消息会批量加载多条）
    if (addedCount > 1) {
      // 历史消息加载，不自动滚动（位置保持由 handleScroll 中的回调处理）
      return;
    }
    
    // 单条新消息，只有用户在底部时才自动滚动
    if (isUserAtBottom.value) {
      nextTick(() => {
        scrollToBottom();
      });
    }
  }
}, { deep: true });

// 初始加载时滚动到底部
watch(() => props.messages.length, (newLength, oldLength) => {
  // 只在初始加载时（从0到有消息）滚动到底部
  if (oldLength === 0 && newLength > 0) {
    nextTick(() => {
      scrollToBottom();
      isUserAtBottom.value = true;
    });
  }
}, { immediate: true });
</script>

<style scoped>
@import '@/styles/components/chat/chat-messages.css';
</style>
