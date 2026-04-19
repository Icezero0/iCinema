<script setup lang="ts">
import type { Room } from "@/infra/api/rooms.api";
import RoomSettingsPanel from "@/features/room/components/RoomSettingsPanel.vue";

defineProps<{
  room: Room;
  roomNameLabel: string;
  visibilityLabel: string;
  syncPolicyLabel: string;
  syncPolicyValue: string;
  syncPermissionLabel: string;
  syncPermissionValue: string;
  localSyncTitle: string;
  localSyncHint: string;
  infoTitle: string;
  syncTitle: string;
  advancedTitle: string;
  advancedHint: string;
  publicLabel: string;
  privateLabel: string;
  localSyncStrategy: string;
  localSyncOptions: { value: string; label: string }[];
}>();

const emit = defineEmits<{
  "update:localSyncStrategy": [value: string];
}>();
</script>

<template>
  <div class="panelBody">
    <RoomSettingsPanel
      :room="room"
      :room-name-label="roomNameLabel"
      :visibility-label="visibilityLabel"
      :sync-policy-label="syncPolicyLabel"
      :sync-policy-value="syncPolicyValue"
      :sync-permission-label="syncPermissionLabel"
      :sync-permission-value="syncPermissionValue"
      :local-sync-title="localSyncTitle"
      :local-sync-hint="localSyncHint"
      :info-title="infoTitle"
      :sync-title="syncTitle"
      :advanced-title="advancedTitle"
      :advanced-hint="advancedHint"
      :public-label="publicLabel"
      :private-label="privateLabel"
      :local-sync-strategy="localSyncStrategy"
      :local-sync-options="localSyncOptions"
      @update:local-sync-strategy="emit('update:localSyncStrategy', $event)"
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
</style>
