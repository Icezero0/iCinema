<script setup lang="ts">
import { computed, reactive, watch } from "vue";
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

type RoomSettingsDraft = {
  name: string;
  visibility: RoomVisibility;
  joinAuditMode: RoomJoinAuditMode;
  syncPolicy: RoomSyncPolicy;
  activeSyncPermission: RoomActiveSyncPermission;
  localSyncStrategy: LocalRoomSyncStrategy;
};

type RoomSettingsDraftKey = keyof RoomSettingsDraft;

const defaultSyncPolicy: RoomSyncPolicy = "auto_sync";
const defaultActiveSyncPermission: RoomActiveSyncPermission = "owner_and_manager";

const draft = reactive<RoomSettingsDraft>({
  name: props.room.name,
  visibility: props.room.visibility,
  joinAuditMode: props.room.join_audit_mode ?? "manual_review",
  syncPolicy: props.roomSettings?.sync_policy ?? defaultSyncPolicy,
  activeSyncPermission: props.roomSettings?.active_sync_permission ?? defaultActiveSyncPermission,
  localSyncStrategy: props.localSyncStrategy,
});
const dirty = reactive<Record<RoomSettingsDraftKey, boolean>>({
  name: false,
  visibility: false,
  joinAuditMode: false,
  syncPolicy: false,
  activeSyncPermission: false,
  localSyncStrategy: false,
});

const hasLoadedRoomSettings = computed(() => Boolean(props.roomSettings));
const saved = computed<RoomSettingsDraft>(() => ({
  name: props.room.name,
  visibility: props.room.visibility,
  joinAuditMode: props.room.join_audit_mode ?? "manual_review",
  syncPolicy: props.roomSettings?.sync_policy ?? defaultSyncPolicy,
  activeSyncPermission: props.roomSettings?.active_sync_permission ?? defaultActiveSyncPermission,
  localSyncStrategy: props.localSyncStrategy,
}));

const hasRoomInfoChanges = computed(() =>
  props.canManageRoomSettings &&
  (
    draft.name.trim() !== saved.value.name ||
    draft.visibility !== saved.value.visibility ||
    draft.joinAuditMode !== saved.value.joinAuditMode
  ));
const hasRoomSettingsChanges = computed(() =>
  props.canManageRoomSettings &&
  hasLoadedRoomSettings.value &&
  (
    draft.syncPolicy !== saved.value.syncPolicy ||
    (props.isOwner && draft.activeSyncPermission !== saved.value.activeSyncPermission)
  ));
const hasLocalChanges = computed(() =>
  draft.localSyncStrategy !== saved.value.localSyncStrategy);
const hasChanges = computed(() =>
  hasRoomInfoChanges.value || hasRoomSettingsChanges.value || hasLocalChanges.value);
const actionsDisabled = computed(() => !hasChanges.value || props.settingsSaving);

function resetDraft() {
  (Object.keys(draft) as RoomSettingsDraftKey[]).forEach(syncDraftFieldFromSaved);
}

function save() {
  if (actionsDisabled.value) return;

  emit("save", {
    name: draft.name.trim(),
    visibility: draft.visibility,
    joinAuditMode: draft.joinAuditMode,
    syncPolicy: draft.syncPolicy,
    activeSyncPermission: draft.activeSyncPermission,
    localSyncStrategy: draft.localSyncStrategy,
  });
}

function isDraftFieldSaved(key: RoomSettingsDraftKey) {
  if (key === "name") return draft.name.trim() === saved.value.name;
  return draft[key] === saved.value[key];
}

function syncDraftFieldFromSaved(key: RoomSettingsDraftKey) {
  draft[key] = saved.value[key] as never;
  dirty[key] = false;
}

function reconcileDraftField(key: RoomSettingsDraftKey) {
  if (dirty[key]) {
    dirty[key] = !isDraftFieldSaved(key);
    return;
  }

  syncDraftFieldFromSaved(key);
}

function setDraftField<K extends RoomSettingsDraftKey>(key: K, value: RoomSettingsDraft[K]) {
  draft[key] = value as never;
  dirty[key] = !isDraftFieldSaved(key);
}

watch(
  () => props.room,
  () => {
    reconcileDraftField("name");
    reconcileDraftField("visibility");
    reconcileDraftField("joinAuditMode");
  },
  { deep: true },
);

watch(
  () => props.roomSettings,
  () => {
    if (!props.roomSettings) return;
    reconcileDraftField("syncPolicy");
    reconcileDraftField("activeSyncPermission");
  },
  { immediate: true },
);

watch(
  () => props.localSyncStrategy,
  () => {
    reconcileDraftField("localSyncStrategy");
  },
);
</script>

<template>
  <div class="settingsTab">
    <div class="panelBody">
      <RoomSettingsPanel
        :room-name="draft.name"
        :visibility="draft.visibility"
        :join-audit-mode="draft.joinAuditMode"
        :sync-policy="draft.syncPolicy"
        :active-sync-permission="draft.activeSyncPermission"
        :settings-loading="settingsLoading"
        :settings-error="settingsError"
        :can-manage-room-settings="canManageRoomSettings"
        :is-owner="isOwner"
        :local-sync-strategy="draft.localSyncStrategy"
        :local-sync-options="localSyncOptions"
        @update:room-name="setDraftField('name', $event)"
        @update:visibility="setDraftField('visibility', $event)"
        @update:join-audit-mode="setDraftField('joinAuditMode', $event)"
        @update:sync-policy="setDraftField('syncPolicy', $event)"
        @update:active-sync-permission="setDraftField('activeSyncPermission', $event)"
        @update:local-sync-strategy="setDraftField('localSyncStrategy', $event as LocalRoomSyncStrategy)"
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
