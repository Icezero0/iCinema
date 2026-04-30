<script setup lang="ts">
import RoomMembersPanel from "@/features/room/components/RoomMembersPanel.vue";
import type { MemberStatus, RoomRole } from "@/features/room/types";

defineProps<{
  members: Array<{
    id: number;
    name: string;
    email?: string | null;
    avatarUrl?: string | null;
    role: RoomRole;
    status: MemberStatus;
  }>;
  searchPlaceholder: string;
  inviteLabel: string;
  leaveRoomLabel: string;
  disbandRoomLabel: string;
  isOwner?: boolean;
  canRemoveMembers?: boolean;
  actionDisabled?: boolean;
  leaving?: boolean;
  disbanding?: boolean;
  pendingJoinRequests?: Array<{
    userId: number;
    source: "apply" | "invite" | "member_invite";
  }>;
  settingManagerUserIds?: number[];
  removingMemberUserIds?: number[];
  loading?: boolean;
  loadingLabel: string;
  emptyLabel: string;
}>();

const emit = defineEmits<{
  inviteUser: [userId: number];
  leaveRoom: [];
  disbandRoom: [];
  setManager: [userId: number];
  unsetManager: [userId: number];
  removeMember: [userId: number];
}>();
</script>

<template>
  <div class="panelBody membersPanelBody">
    <RoomMembersPanel
      :members="members"
      :search-placeholder="searchPlaceholder"
      :invite-label="inviteLabel"
      :leave-room-label="leaveRoomLabel"
      :disband-room-label="disbandRoomLabel"
      :is-owner="isOwner"
      :can-remove-members="canRemoveMembers"
      :action-disabled="actionDisabled"
      :leaving="leaving"
      :disbanding="disbanding"
      :pending-join-requests="pendingJoinRequests"
      :setting-manager-user-ids="settingManagerUserIds"
      :removing-member-user-ids="removingMemberUserIds"
      :loading="loading"
      :loading-label="loadingLabel"
      :empty-label="emptyLabel"
      @invite-user="emit('inviteUser', $event.id)"
      @leave-room="emit('leaveRoom')"
      @disband-room="emit('disbandRoom')"
      @set-manager="emit('setManager', $event)"
      @unset-manager="emit('unsetManager', $event)"
      @remove-member="emit('removeMember', $event)"
    />
  </div>
</template>

<style scoped>
.panelBody {
  display: grid;
  gap: 14px;
  padding: 14px;
  min-height: 0;
  align-content: start;
  overflow: auto;
}

.panelBody > * {
  align-self: start;
}

.membersPanelBody {
  grid-template-rows: minmax(0, 1fr);
  overflow: hidden;
}

.membersPanelBody > * {
  align-self: stretch;
  min-height: 0;
}
</style>
