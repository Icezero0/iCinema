<template>
  <div class="chat-content-row">
    <UserAvatar 
      :src="message.avatar || defaultAvatar" 
      :alt="message.username" 
      size="32" 
      class="chat-avatar" 
    />
    <div class="chat-content-col">
      <div class="chat-username" :class="{ 'self-username': isSelf }">
        {{ message.username }}
      </div>
      <span class="chat-bubble">{{ message.content }}</span>
    </div>
  </div>
</template>

<script setup>
import UserAvatar from '@/components/user/UserAvatar.vue';
import defaultAvatar from '@/assets/default_avatar.jpg';

// Props
defineProps({
  message: {
    type: Object,
    required: true
  },
  isSelf: {
    type: Boolean,
    default: false
  }
});
</script>

<style scoped>
@import '@/styles/components/chat/message-item.css';
</style>
