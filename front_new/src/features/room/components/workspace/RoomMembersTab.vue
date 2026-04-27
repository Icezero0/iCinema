<script setup lang="ts">
import RoomMembersPanel from "@/features/room/components/RoomMembersPanel.vue";
import type { RoomRole } from "@/features/room/types";

defineProps<{
  members: Array<{
    id: number;
    name: string;
    avatarUrl?: string | null;
    role: RoomRole;
    status: "idle";
  }>;
  searchPlaceholder: string;
  inviteLabel: string;
  leaveRoomLabel: string;
  disbandRoomLabel: string;
  isOwner?: boolean;
  actionDisabled?: boolean;
  leaving?: boolean;
  disbanding?: boolean;
  pendingJoinRequests?: Array<{
    userId: number;
    source: "apply" | "invite" | "member_invite";
  }>;
  loading?: boolean;
  loadingLabel: string;
  emptyLabel: string;
}>();

const emit = defineEmits<{
  inviteUser: [userId: number];
  leaveRoom: [];
  disbandRoom: [];
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
      :action-disabled="actionDisabled"
      :leaving="leaving"
      :disbanding="disbanding"
      :pending-join-requests="pendingJoinRequests"
      :loading="loading"
      :loading-label="loadingLabel"
      :empty-label="emptyLabel"
      @invite-user="emit('inviteUser', $event.id)"
      @leave-room="emit('leaveRoom')"
      @disband-room="emit('disbandRoom')"
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
