<template>
  <div class="room-header" :class="{ 'dark-mode': isDarkMode }">
    <button class="back-home-btn" @click="$emit('back-home')">返回主页</button>
    <div class="room-title">{{ roomName }}</div>    <div class="ws-status-bar" :class="wsStatus">
      <span v-if="wsStatus === 'connected'">🟢 已连接</span>
      <span v-else-if="wsStatus === 'connecting'">🟡 正在连接...</span>
      <span v-else>🔴 未连接</span>
    </div>
    <button 
      class="dark-mode-toggle-btn"
      :class="{ 'dark-active': isDarkMode }"
      @click="$emit('toggle-dark-mode', !isDarkMode)"
    >
      <span class="toggle-icon">{{ isDarkMode ? '🌙' : '☀️' }}</span>
      <span class="toggle-text">{{ isDarkMode ? '深色模式' : '浅色模式' }}</span>
    </button>
  </div>
</template>

<script setup>
defineProps({
  roomName: {
    type: String,
    default: ''
  },
  wsStatus: {
    type: String,
    default: 'disconnected'
  },
  isDarkMode: {
    type: Boolean,
    default: false
  }
});

defineEmits(['back-home', 'toggle-dark-mode']);
</script>

<style scoped>
@import '@/styles/components/room/room-header.css';
</style>
