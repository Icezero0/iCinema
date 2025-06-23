<template>
  <div class="room-members-container">
    <!-- 房间成员标题 -->
    <div class="room-members-label">房间成员</div>
    
    <!-- 房间成员列表 -->
    <div class="room-members-bar" ref="membersBarRef">
      <template v-if="members.length > 0">
        <MemberItem 
          v-for="member in members" 
          :key="member.id"
          :member="member"
          @click="openUserInfoDialog(member)"
        />        <div class="add-member-btn" @click="showAddUserDialog = true" title="添加成员">
          <div class="add-member-avatar">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="11" cy="11" r="11" fill="#fff"/>
              <path d="M11 6V16" stroke="#888" stroke-width="2" stroke-linecap="round"/>
              <path d="M6 11H16" stroke="#888" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="add-member-label">添加成员</div>
        </div>
      </template>
      <template v-else>
        <div class="room-member-item owner">
          <UserAvatar :src="defaultAvatar" alt="测试用户" size="38" class="room-member-avatar" />
          <div class="room-member-name">测试用户</div>
        </div>
      </template>
    </div>

    <!-- 用户信息弹窗 -->
    <MemberInfoDialog
      :show="showUserInfoDialog"
      :user="selectedUser"
      :can-remove="canRemoveUser"
      :is-owner="isOwner"
      :current-user-id="currentUserId"
      @close="showUserInfoDialog = false"
      @remove="handleRemoveUser"
    />

    <!-- 添加成员弹窗 -->
    <AddMemberDialog
      :show="showAddUserDialog"
      :room-members="members"
      :is-owner="isOwner"
      :room-id="roomId"
      @close="showAddUserDialog = false"
      @member-added="handleMemberAdded"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useUserInfo } from '@/composables/useUserInfo.js';
import defaultAvatar from '@/assets/default_avatar.jpg';
import UserAvatar from '@/components/user/UserAvatar.vue';
import MemberItem from './MemberItem.vue';
import MemberInfoDialog from './MemberInfoDialog.vue';
import AddMemberDialog from './AddMemberDialog.vue';

// Props
const props = defineProps({
  members: {
    type: Array,
    default: () => []
  },
  isOwner: {
    type: Boolean,
    default: false
  },
  currentUserId: {
    type: [String, Number],
    required: true
  },
  roomId: {
    type: [String, Number],
    required: true
  }
});

// Emits
const emit = defineEmits([
  'member-info-opened',
  'member-removed', 
  'member-added',
  'add-member-clicked'
]);

// 响应式数据
const membersBarRef = ref(null);
const showUserInfoDialog = ref(false);
const showAddUserDialog = ref(false);
const selectedUser = ref(null);

// 计算属性
const canRemoveUser = computed(() => {
  if (!selectedUser.value) return false;
  const user = selectedUser.value;
  return (props.isOwner && user.id !== props.currentUserId) || 
         (!props.isOwner && user.id === props.currentUserId);
});

// 方法
async function openUserInfoDialog(user) {
  showUserInfoDialog.value = true;
  const userInfo = await useUserInfo(user.id);
  selectedUser.value = {
    id: user.id,
    avatarUrl: userInfo.avatarUrl,
    username: userInfo.username,
    email: userInfo.email,
  };
  emit('member-info-opened', selectedUser.value);
}

function handleRemoveUser(user) {
  emit('member-removed', user);
  showUserInfoDialog.value = false;
}

function handleMemberAdded(member) {
  emit('member-added', member);
}

// 暴露给父组件的方法和数据
defineExpose({
  membersBarRef
});
</script>

<style scoped>
@import '@/styles/components/room/room-members.css';
</style>
