<template>  <BaseDialog
    :show="show"
    title="用户信息"
    :show-cancel="false"
    ok-text="关闭"
    @cancel="$emit('close')"
    @ok="$emit('close')"
  >    <div class="user-info-dialog-content" v-if="user">
      <img 
        :src="user.avatarUrl" 
        :alt="user.username" 
        class="user-avatar-detail"
        @error="handleImageError"
      />
      <div class="user-info-username">{{ user.username }}</div>
      <div class="user-info-email">{{ user.email }}</div>
      <button 
        class="remove-btn"
        @click="handleRemoveUser"
        :disabled="!canRemove"
      >
        {{ getRemoveButtonText() }}
      </button>
    </div>
  </BaseDialog>
</template>

<script setup>
import { ref } from 'vue';
import BaseDialog from '@/components/base/BaseDialog.vue';
import defaultAvatar from '@/assets/default_avatar.jpg';

// Props
const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  user: {
    type: Object,
    default: null
  },
  canRemove: {
    type: Boolean,
    default: false
  },
  isOwner: {
    type: Boolean,
    default: false
  },
  currentUserId: {
    type: [String, Number],
    required: true
  }
});

// Emits
const emit = defineEmits(['close', 'remove']);

// 方法
function handleImageError(event) {
  event.target.src = defaultAvatar;
}

function handleRemoveUser() {
  if (!props.canRemove || !props.user) return;
  
  const isRemovingSelf = props.user.id === props.currentUserId;
  const confirmMessage = isRemovingSelf 
    ? '确定要退出房间吗？'
    : `确定要将用户 ${props.user.username} 移出房间吗？`;
  
  const confirmed = window.confirm(confirmMessage);
  if (confirmed) {
    emit('remove', props.user);
  }
}

function getRemoveButtonText() {
  if (!props.user) return '移出房间';
  return props.user.id === props.currentUserId ? '退出房间' : '移出房间';
}
</script>

<style scoped>
@import '@/styles/components/room/member-dialogs.css';
</style>
