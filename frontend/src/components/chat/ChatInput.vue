<template>
  <div class="chat-input-area">    <input 
      v-model="inputMessage"
      @keyup.enter="handleSend"
      :disabled="disabled"
      placeholder="输入消息..." 
      class="chat-input"
      ref="inputRef"
      autocomplete="off"
      autocapitalize="off"
      autocorrect="off"
      spellcheck="false"
    />
    <button 
      @click="handleSend" 
      :disabled="disabled || !inputMessage.trim()"
      class="chat-send-btn"
    >
      发送
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue';

// Props
defineProps({
  disabled: {
    type: Boolean,
    default: false
  }
});

// Emits
const emit = defineEmits(['send']);

// 响应式数据
const inputMessage = ref('');
const inputRef = ref(null);

// 方法
function handleSend() {
  const content = inputMessage.value.trim();
  if (!content) return;
  
  emit('send', content);
  inputMessage.value = '';
  
  // 重新聚焦输入框
  if (inputRef.value) {
    inputRef.value.focus();
  }
}

// 暴露方法给父组件
defineExpose({
  focus: () => {
    if (inputRef.value) {
      inputRef.value.focus();
    }
  },
  clear: () => {
    inputMessage.value = '';
  }
});
</script>

<style scoped>
@import '@/styles/components/chat/chat-input.css';
</style>
