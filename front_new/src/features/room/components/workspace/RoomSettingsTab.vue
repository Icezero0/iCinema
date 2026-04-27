<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type {
  Room,
  RoomActiveSyncPermission,
  RoomJoinAuditMode,
  RoomSettings,
  RoomSyncPolicy,
  RoomVisibility,
} from "@/infra/api/rooms.api";
import type { LocalRoomSyncStrategy } from "@/stores/entities.store";
import RoomSettingsPanel from "@/features/room/components/RoomSettingsPanel.vue";

const props = defineProps<{
  room: Room;
  roomSettings?: RoomSettings | null;
  settingsLoading?: boolean;
  settingsError?: string;
  settingsSaving?: boolean;
  canManageRoomSettings?: boolean;
  isOwner?: boolean;
  localSyncStrategy: LocalRoomSyncStrategy;
  localSyncOptions: { value: LocalRoomSyncStrategy; label: string }[];
}>();

const emit = defineEmits<{
  save: [payload: RoomSettingsSavePayload];
}>();

type RoomSettingsSavePayload = {
  name: string;
  visibility: RoomVisibility;
  joinAuditMode: RoomJoinAuditMode;
  syncPolicy: RoomSyncPolicy;
  activeSyncPermission: RoomActiveSyncPermission;
  localSyncStrategy: LocalRoomSyncStrategy;
};

const { t } = useI18n();

const draftName = ref(props.room.name);
const draftVisibility = ref<RoomVisibility>(props.room.visibility);
const draftJoinAuditMode = ref<RoomJoinAuditMode>(props.room.join_audit_mode ?? "manual_review");
const draftSyncPolicy = ref<RoomSyncPolicy>(props.roomSettings?.sync_policy ?? "auto_sync");
const draftActiveSyncPermission = ref<RoomActiveSyncPermission>(
  props.roomSettings?.active_sync_permission ?? "owner_and_manager",
);
const draftLocalSyncStrategy = ref<LocalRoomSyncStrategy>(props.localSyncStrategy);

const savedName = computed(() => props.room.name);
const savedVisibility = computed(() => props.room.visibility);
const savedJoinAuditMode = computed(() => props.room.join_audit_mode ?? "manual_review");
const savedSyncPolicy = computed(() => props.roomSettings?.sync_policy ?? "auto_sync");
const savedActiveSyncPermission = computed(() =>
  props.roomSettings?.active_sync_permission ?? "owner_and_manager");
const savedLocalSyncStrategy = computed(() => props.localSyncStrategy);

const hasRoomInfoChanges = computed(() =>
  props.canManageRoomSettings &&
  (
    draftName.value.trim() !== savedName.value ||
    draftVisibility.value !== savedVisibility.value ||
    draftJoinAuditMode.value !== savedJoinAuditMode.value
  ));
const hasRoomSettingsChanges = computed(() =>
  props.canManageRoomSettings &&
  (
    draftSyncPolicy.value !== savedSyncPolicy.value ||
    (props.isOwner && draftActiveSyncPermission.value !== savedActiveSyncPermission.value)
  ));
const hasLocalChanges = computed(() =>
  draftLocalSyncStrategy.value !== savedLocalSyncStrategy.value);
const hasChanges = computed(() =>
  hasRoomInfoChanges.value || hasRoomSettingsChanges.value || hasLocalChanges.value);
const actionsDisabled = computed(() => !hasChanges.value || props.settingsSaving);

function resetDraft() {
  draftName.value = savedName.value;
  draftVisibility.value = savedVisibility.value;
  draftJoinAuditMode.value = savedJoinAuditMode.value;
  draftSyncPolicy.value = savedSyncPolicy.value;
  draftActiveSyncPermission.value = savedActiveSyncPermission.value;
  draftLocalSyncStrategy.value = savedLocalSyncStrategy.value;
}

function save() {
  if (actionsDisabled.value) return;

  emit("save", {
    name: draftName.value.trim(),
    visibility: draftVisibility.value,
    joinAuditMode: draftJoinAuditMode.value,
    syncPolicy: draftSyncPolicy.value,
    activeSyncPermission: draftActiveSyncPermission.value,
    localSyncStrategy: draftLocalSyncStrategy.value,
  });
}

watch(
  () => props.room,
  () => {
    if (hasRoomInfoChanges.value) return;

    draftName.value = savedName.value;
    draftVisibility.value = savedVisibility.value;
    draftJoinAuditMode.value = savedJoinAuditMode.value;
  },
  { deep: true },
);

watch(
  () => props.roomSettings,
  () => {
    if (hasRoomSettingsChanges.value) return;

    draftSyncPolicy.value = savedSyncPolicy.value;
    draftActiveSyncPermission.value = savedActiveSyncPermission.value;
  },
  { immediate: true },
);

watch(
  () => props.localSyncStrategy,
  () => {
    if (hasLocalChanges.value) return;
    draftLocalSyncStrategy.value = savedLocalSyncStrategy.value;
  },
);
</script>

<template>
  <div class="settingsTab">
    <div class="panelBody">
      <RoomSettingsPanel
        :room-name="draftName"
        :visibility="draftVisibility"
        :join-audit-mode="draftJoinAuditMode"
        :sync-policy="draftSyncPolicy"
        :active-sync-permission="draftActiveSyncPermission"
        :settings-loading="settingsLoading"
        :settings-error="settingsError"
        :can-manage-room-settings="canManageRoomSettings"
        :is-owner="isOwner"
        :local-sync-strategy="draftLocalSyncStrategy"
        :local-sync-options="localSyncOptions"
        @update:room-name="draftName = $event"
        @update:visibility="draftVisibility = $event"
        @update:join-audit-mode="draftJoinAuditMode = $event"
        @update:sync-policy="draftSyncPolicy = $event"
        @update:active-sync-permission="draftActiveSyncPermission = $event"
        @update:local-sync-strategy="draftLocalSyncStrategy = $event as LocalRoomSyncStrategy"
      />
    </div>

    <div class="settingsFooter">
      <BaseButton
        variant="default"
        :disabled="actionsDisabled"
        @click="resetDraft"
      >
        {{ t("common.cancel") }}
      </BaseButton>
      <BaseButton
        variant="primary"
        :disabled="actionsDisabled"
        :loading="settingsSaving"
        @click="save"
      >
        {{ t("common.save") }}
      </BaseButton>
    </div>
  </div>
</template>

<style scoped>
.settingsTab {
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
}

.panelBody {
  display: grid;
  gap: 14px;
  padding: 14px;
  min-height: 0;
  align-content: start;
  overflow: auto;
  scrollbar-gutter: stable;
}

.panelBody > * {
  align-self: start;
}

.settingsFooter {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 10px 14px 14px;
  border-top: 1px solid color-mix(in srgb, var(--c-border) 72%, transparent);
  background: color-mix(in srgb, var(--c-surface) 88%, var(--c-bg));
}

.settingsFooter :deep(button) {
  width: 100%;
}
</style>
