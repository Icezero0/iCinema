<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type {
  RoomActiveSyncPermission,
  RoomJoinAuditMode,
  RoomSyncPolicy,
  RoomVisibility,
} from "@/infra/api/rooms.api";

defineProps<{
  roomName: string;
  visibility: RoomVisibility;
  joinAuditMode: RoomJoinAuditMode;
  syncPolicy: RoomSyncPolicy;
  activeSyncPermission: RoomActiveSyncPermission;
  settingsLoading?: boolean;
  settingsError?: string;
  canManageRoomSettings?: boolean;
  isOwner?: boolean;
  localSyncStrategy: string;
  localSyncOptions: { value: string; label: string }[];
}>();

const emit = defineEmits<{
  (e: "update:roomName", value: string): void;
  (e: "update:visibility", value: RoomVisibility): void;
  (e: "update:joinAuditMode", value: RoomJoinAuditMode): void;
  (e: "update:syncPolicy", value: RoomSyncPolicy): void;
  (e: "update:activeSyncPermission", value: RoomActiveSyncPermission): void;
  (e: "update:localSyncStrategy", value: string): void;
}>();

const { t } = useI18n();

const visibilityOptions = computed(() => [
  { value: "public", label: t("room.settings.visibilityPublic") },
  { value: "private", label: t("room.settings.visibilityPrivate") },
]);
const joinAuditOptions = computed(() => [
  { value: "manual_review", label: t("room.settings.auditManual") },
  { value: "auto_approve", label: t("room.settings.auditAutoApprove") },
  { value: "auto_reject", label: t("room.settings.auditAutoReject") },
]);
const syncPolicyOptions = computed(() => [
  { value: "auto_sync", label: t("room.settings.syncAuto") },
  { value: "disabled", label: t("room.settings.syncManual") },
]);
const activeSyncPermissionOptions = computed(() => [
  { value: "owner_only", label: t("room.settings.activeSyncOwnerOnly") },
  { value: "owner_and_manager", label: t("room.settings.activeSyncOwnerAndManager") },
  { value: "all_members", label: t("room.settings.activeSyncAllMembers") },
]);
</script>

<template>
  <div class="settingsStack">
    <section class="settingsSection">
      <div class="sectionTitle">{{ t("room.settings.infoSection") }}</div>

      <label class="settingField">
        <span class="settingLabel">{{ t("room.settings.roomName") }}</span>
        <BaseInput
          v-if="canManageRoomSettings"
          :model-value="roomName"
          @update:model-value="emit('update:roomName', $event)"
        />
        <span v-else class="readonlyValue">{{ roomName }}</span>
      </label>

      <label class="settingField">
        <span class="settingLabel">{{ t("room.settings.visibility") }}</span>
        <BaseSelect
          v-if="canManageRoomSettings"
          :model-value="visibility"
          :options="visibilityOptions"
          @update:model-value="emit('update:visibility', $event as RoomVisibility)"
        />
        <span v-else class="readonlyValue">
          {{ visibility === "public" ? t("room.settings.visibilityPublic") : t("room.settings.visibilityPrivate") }}
        </span>
      </label>
    </section>

    <section v-if="canManageRoomSettings" class="settingsSection">
      <div class="sectionHeader">
        <div class="sectionTitle">{{ t("room.settings.policySection") }}</div>
        <div v-if="settingsLoading" class="sectionState">{{ t("common.loading") }}</div>
        <div v-else-if="settingsError" class="sectionState error">{{ settingsError }}</div>
      </div>

      <label class="settingField">
        <span class="settingLabel">{{ t("room.settings.joinAuditMode") }}</span>
        <BaseSelect
          :model-value="joinAuditMode"
          :options="joinAuditOptions"
          @update:model-value="emit('update:joinAuditMode', $event as RoomJoinAuditMode)"
        />
      </label>

      <label class="settingField">
        <span class="settingLabel">{{ t("room.settings.roomSyncPolicy") }}</span>
        <BaseSelect
          :model-value="syncPolicy"
          :options="syncPolicyOptions"
          :disabled="settingsLoading"
          @update:model-value="emit('update:syncPolicy', $event as RoomSyncPolicy)"
        />
      </label>

      <label v-if="isOwner" class="settingField">
        <span class="settingLabel">{{ t("room.settings.activeSyncPermission") }}</span>
        <BaseSelect
          :model-value="activeSyncPermission"
          :options="activeSyncPermissionOptions"
          :disabled="settingsLoading"
          @update:model-value="emit('update:activeSyncPermission', $event as RoomActiveSyncPermission)"
        />
      </label>
    </section>

  </div>
</template>

<style scoped>
.settingsStack {
  display: grid;
  gap: 12px;
}

.settingsSection {
  padding: 12px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 76%, var(--c-bg));
  display: grid;
  gap: 12px;
}

.sectionTitle {
  font-size: 13px;
  font-weight: 650;
  color: var(--c-text);
}

.sectionHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.sectionState {
  min-width: 0;
  color: var(--c-text-muted);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sectionState.error {
  color: var(--c-danger);
}

.settingField {
  display: grid;
  grid-template-columns: minmax(72px, 0.8fr) minmax(0, 1.4fr);
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.settingLabel {
  font-size: 12px;
  color: var(--c-text-muted);
  line-height: 1.25;
}

.settingField :deep(.inp),
.settingField :deep(.trigger) {
  min-height: 34px;
  height: 34px;
  border-radius: 10px;
  font-size: 12px;
}

.settingField :deep(.inp) {
  padding: 0 10px;
}

.settingField :deep(.trigger) {
  padding: 0 10px;
}

.settingField :deep(.triggerLabel) {
  font-size: 12px;
}

.settingField :deep(.fieldRoot) {
  gap: 5px;
}

.readonlyValue {
  min-height: 34px;
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 0 10px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: color-mix(in srgb, var(--c-surface) 70%, var(--c-bg));
  color: var(--c-text);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 420px) {
  .settingField {
    grid-template-columns: 1fr;
    align-items: stretch;
    gap: 6px;
  }
}
</style>
