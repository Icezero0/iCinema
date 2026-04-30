import { computed, ref, type ComputedRef, type Ref } from "vue";
import { useI18n } from "vue-i18n";
import {
  getRoomSettings,
  patchRoom,
  patchRoomSettings,
  type Room,
  type RoomActiveSyncPermission,
  type RoomJoinAuditMode,
  type RoomSettings,
  type RoomSyncPolicy,
  type RoomVisibility,
} from "@/infra/api/rooms.api";
import {
  DEFAULT_LOCAL_ROOM_SYNC_STRATEGY,
  useEntitiesStore,
  type LocalRoomSyncStrategy,
} from "@/stores/entities.store";
import { useToastsStore } from "@/stores/toasts.store";
import type { RoomRole } from "@/features/room/types";
import { getBackendErrorMessage } from "@/infra/http/client";

type RoomRoleState = RoomRole | "unknown";

export type RoomSettingsSavePayload = {
  name: string;
  visibility: RoomVisibility;
  joinAuditMode: RoomJoinAuditMode;
  syncPolicy: RoomSyncPolicy;
  activeSyncPermission: RoomActiveSyncPermission;
  localSyncStrategy: LocalRoomSyncStrategy;
};

type UseRoomSettingsStateOptions = {
  roomId: ComputedRef<number>;
  room: Ref<Room | null>;
  currentUserRole: Ref<RoomRoleState>;
  canManageRoomSettings: ComputedRef<boolean>;
  isOwner: ComputedRef<boolean>;
};

export function useRoomSettingsState(options: UseRoomSettingsStateOptions) {
  const { t } = useI18n();
  const entitiesStore = useEntitiesStore();
  const toasts = useToastsStore();

  const roomSettings = ref<RoomSettings | null>(null);
  const roomSettingsLoading = ref(false);
  const roomSettingsError = ref("");
  const roomSettingsLoaded = ref(false);
  const roomSettingsSaving = ref(false);
  const localSyncStrategy = ref<LocalRoomSyncStrategy>(
    DEFAULT_LOCAL_ROOM_SYNC_STRATEGY,
  );

  const localSyncOptions = computed<Array<{ value: LocalRoomSyncStrategy; label: string }>>(() => [
    { value: "adaptive-speed", label: t("room.settings.localSyncAdaptiveSpeed") },
    { value: "auto-seek", label: t("room.settings.localSyncAutoSeek") },
    { value: "manual-sync", label: t("room.settings.localSyncManual") },
  ]);

  function loadLocalSyncStrategy() {
    if (!options.roomId.value) {
      localSyncStrategy.value = DEFAULT_LOCAL_ROOM_SYNC_STRATEGY;
      return;
    }

    localSyncStrategy.value = entitiesStore.loadRoomLocalSyncStrategy(
      options.roomId.value,
    );
  }

  function resetRoomSettingsState() {
    roomSettings.value = null;
    roomSettingsError.value = "";
    roomSettingsLoaded.value = false;
    roomSettingsSaving.value = false;
  }

  async function fetchRoomSettings(fetchOptions?: { force?: boolean }) {
    if (!options.roomId.value || options.currentUserRole.value === "unknown") {
      resetRoomSettingsState();
      return;
    }

    if (roomSettingsLoading.value) return;
    if (!fetchOptions?.force && roomSettingsLoaded.value) return;

    roomSettingsLoading.value = true;
    roomSettingsError.value = "";

    try {
      roomSettings.value = await getRoomSettings(options.roomId.value);
      entitiesStore.upsertRoomSettings(roomSettings.value);
      roomSettingsLoaded.value = true;
    } catch (e: any) {
      roomSettingsError.value =
        getBackendErrorMessage(e) ||
        t("room.settings.loadFailed");
    } finally {
      roomSettingsLoading.value = false;
    }
  }

  async function handleSaveRoomSettings(payload: RoomSettingsSavePayload) {
    if (!options.room.value || !options.roomId.value || roomSettingsSaving.value) return;

    if (!payload.name) {
      toasts.push({
        message: t("room.settings.nameRequired"),
        tone: "danger",
      });
      return;
    }

    roomSettingsSaving.value = true;

    try {
      const roomPatch: {
        name?: string;
        visibility?: RoomVisibility;
        join_audit_mode?: RoomJoinAuditMode;
      } = {};

      if (options.canManageRoomSettings.value) {
        if (payload.name !== options.room.value.name) roomPatch.name = payload.name;
        if (payload.visibility !== options.room.value.visibility) {
          roomPatch.visibility = payload.visibility;
        }
        if (payload.joinAuditMode !== (options.room.value.join_audit_mode ?? "manual_review")) {
          roomPatch.join_audit_mode = payload.joinAuditMode;
        }
      }

      if (Object.keys(roomPatch).length > 0) {
        options.room.value = await patchRoom(options.roomId.value, roomPatch);
        entitiesStore.upsertRoom(options.room.value);
      }

      const settingsPatch: {
        sync_policy?: RoomSyncPolicy;
        active_sync_permission?: RoomActiveSyncPermission;
      } = {};

      if (options.canManageRoomSettings.value) {
        if (payload.syncPolicy !== (roomSettings.value?.sync_policy ?? "auto_sync")) {
          settingsPatch.sync_policy = payload.syncPolicy;
        }
        if (
          options.isOwner.value &&
          payload.activeSyncPermission !==
            (roomSettings.value?.active_sync_permission ?? "owner_and_manager")
        ) {
          settingsPatch.active_sync_permission = payload.activeSyncPermission;
        }
      }

      if (Object.keys(settingsPatch).length > 0) {
        roomSettings.value = await patchRoomSettings(
          options.roomId.value,
          settingsPatch,
        );
        entitiesStore.upsertRoomSettings(roomSettings.value);
      }

      if (payload.localSyncStrategy !== localSyncStrategy.value) {
        localSyncStrategy.value = payload.localSyncStrategy;
        entitiesStore.setRoomLocalSyncStrategy(
          options.roomId.value,
          payload.localSyncStrategy,
        );
      }

      toasts.push({
        message: t("room.settings.saveSuccess"),
        tone: "success",
      });
    } catch (e: any) {
      toasts.push({
        message:
          getBackendErrorMessage(e) ||
          t("room.settings.saveFailed"),
        tone: "danger",
      });
    } finally {
      roomSettingsSaving.value = false;
    }
  }

  return {
    roomSettings,
    roomSettingsLoading,
    roomSettingsError,
    roomSettingsSaving,
    localSyncStrategy,
    localSyncOptions,
    loadLocalSyncStrategy,
    resetRoomSettingsState,
    fetchRoomSettings,
    handleSaveRoomSettings,
  };
}
