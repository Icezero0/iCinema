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
  loading?: boolean;
  loadingLabel: string;
  emptyLabel: string;
}>();
</script>

<template>
  <div class="panelBody membersPanelBody">
    <RoomMembersPanel
      :members="members"
      :search-placeholder="searchPlaceholder"
      :invite-label="inviteLabel"
      :leave-room-label="leaveRoomLabel"
      :loading="loading"
      :loading-label="loadingLabel"
      :empty-label="emptyLabel"
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
