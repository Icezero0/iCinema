<template>
  <div 
    class="room-member-item" 
    :class="{ owner: member.isOwner }"
    @click="$emit('click', member)"
  >
    <UserAvatar 
      :src="member.avatarUrl" 
      :alt="member.username" 
      size="38" 
      class="room-member-avatar"
    />
    <div class="room-member-name">{{ member.username }}</div>
  </div>
</template>

<script setup>
import UserAvatar from '@/components/user/UserAvatar.vue';

// Props
defineProps({
  member: {
    type: Object,
    required: true
  }
});

// Emits
defineEmits(['click']);
</script>

<style scoped>
@import '@/styles/components/room/member-item.css';
</style>
