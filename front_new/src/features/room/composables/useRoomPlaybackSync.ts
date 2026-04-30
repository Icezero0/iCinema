import { computed, ref, type ComputedRef, type Ref } from "vue";
import type {
  RoomRole,
  RoomSettings,
  RoomVideoSourceType,
} from "@/infra/api/rooms.api";
import {
  sendRoomRealtimePlaybackPause,
  sendRoomRealtimePlaybackPlay,
  sendRoomRealtimePlaybackSeek,
  sendRoomRealtimeUserResourceStatus,
  setRoomRealtimeVideoSource,
  type RoomRealtimePlaybackState,
  type RoomRealtimeResourceStatus,
  type RoomRealtimeVideoSourceState,
} from "@/infra/realtime/roomRealtime";
import { useToastsStore } from "@/stores/toasts.store";
import { computeFileSha256 } from "@/features/room/video/fileHash";
import type { useRoomRealtimeSession } from "@/features/room/composables/useRoomRealtimeSession";

export type DisplayResourceStatus = "idle" | RoomRealtimeResourceStatus;

type RoomRoleState = RoomRole | "unknown";
type SyncGateState = "locked" | "unlocked";
type LocalFileSourceIssue = "none" | "select_required" | "hash_mismatch" | "hash_failed";
type LocalFileSourceAction = "match_room_target" | "set_room_target";

type PlaybackSourcePayload = {
  sourceType: RoomVideoSourceType;
  externalUrl: string;
  localFile: File | null;
  localFileAction?: LocalFileSourceAction | null;
};

type UseRoomPlaybackSyncOptions = {
  roomId: ComputedRef<number>;
  currentUserRole: Ref<RoomRoleState>;
  roomSettings: Ref<RoomSettings | null>;
  routeRequiresSyncGate: () => boolean;
  realtime: ReturnType<typeof useRoomRealtimeSession>;
  playback: {
    playbackIsPlaying: Ref<boolean>;
    playbackCurrentTime: Ref<number>;
    playbackDuration: Ref<number>;
    playbackSourceType: Ref<RoomVideoSourceType>;
    playbackSourceUrl: Ref<string>;
    playbackSourceFile: Ref<File | null>;
    playbackSourceFileHash: Ref<string>;
    toggleLocalPlayback: () => void;
    handleLocalPlaybackProgressChange: (value: number) => void;
    applyLocalPlaybackSource: (payload: PlaybackSourcePayload & { localFileHash?: string | null }) => void;
    applyRealtimeVideoSource: (source: RoomRealtimeVideoSourceState | null) => unknown;
    applyRealtimePlaybackState: (
      state: RoomRealtimePlaybackState | null,
      options?: { syncPosition?: boolean },
    ) => Promise<void>;
  };
  t: (key: string, params?: Record<string, unknown>) => string;
  te: (key: string) => boolean;
};

type RoomRealtimePlaybackEvent = {
  action: "snapshot" | "playback_play" | "playback_pause" | "playback_seek";
  state: RoomRealtimePlaybackState;
};

type RoomRealtimeVideoSourceEvent = {
  action: "snapshot" | "room_video_source_set";
  state: RoomRealtimeVideoSourceState | null;
};

const ROOM_PLAYBACK_DEBUG = false;
const MIN_HASH_PROGRESS_VISIBLE_MS = 450;

export function useRoomPlaybackSync(options: UseRoomPlaybackSyncOptions) {
  const toasts = useToastsStore();
  let lastReportedResourceStatus: RoomRealtimeResourceStatus | null = null;

  const localResourceStatus = ref<DisplayResourceStatus>("idle");
  const latestResourceStatus = ref<DisplayResourceStatus>("idle");
  const syncGateState = ref<SyncGateState>(getInitialSyncGateState());
  const localFileSourceIssue = ref<LocalFileSourceIssue>("none");
  const sourcePanelOpenKey = ref(0);
  const sourcePanelCloseKey = ref(0);
  const sourceApplying = ref(false);
  const sourceHashProgress = ref<number | null>(null);

  const canControlRealtimePlayback = computed(() => {
    const permission = options.roomSettings.value?.active_sync_permission;
    if (!permission) return true;
    if (permission === "all_members") return true;
    if (permission === "owner_and_manager") {
      return options.currentUserRole.value === "owner" || options.currentUserRole.value === "manager";
    }
    return options.currentUserRole.value === "owner";
  });
  const roomRuntimeLocalFileHash = computed(() => {
    const source = options.realtime.roomVideoSource.value;
    return source?.source_type === "local_file"
      ? source.file_hash?.trim() || null
      : null;
  });
  const hasMatchingRoomLocalFile = computed(() =>
    Boolean(
      roomRuntimeLocalFileHash.value &&
        options.playback.playbackSourceType.value === "local_file" &&
        options.playback.playbackSourceFile.value &&
        options.playback.playbackSourceFileHash.value === roomRuntimeLocalFileHash.value,
    ));
  const needsRoomLocalFileSelection = computed(() =>
    isSyncGateUnlocked() &&
    Boolean(roomRuntimeLocalFileHash.value) &&
    !hasMatchingRoomLocalFile.value);
  const sourcePanelMessage = computed(() => {
    if (sourceApplying.value) return options.t("room.sourcePanel.hashingFile");
    if (localFileSourceIssue.value === "hash_mismatch") {
      return options.t("room.sourcePanel.localFileMismatch");
    }
    if (localFileSourceIssue.value === "hash_failed") {
      return options.t("room.sourcePanel.localFileHashFailed");
    }
    if (needsRoomLocalFileSelection.value) {
      return options.t("room.sourcePanel.localFileRequiredForSync");
    }
    return "";
  });
  const sourcePanelMessageTone = computed<"muted" | "error">(() =>
    localFileSourceIssue.value === "hash_mismatch" ||
    localFileSourceIssue.value === "hash_failed"
      ? "error"
      : "muted");

  function getInitialSyncGateState(): SyncGateState {
    return options.routeRequiresSyncGate() ? "locked" : "unlocked";
  }

  function isSyncGateUnlocked() {
    return syncGateState.value === "unlocked";
  }

  function wait(ms: number) {
    return new Promise<void>((resolve) => {
      window.setTimeout(resolve, ms);
    });
  }

  async function keepHashProgressVisibleSince(startedAt: number) {
    const elapsed = performance.now() - startedAt;
    if (elapsed >= MIN_HASH_PROGRESS_VISIBLE_MS) return;
    await wait(MIN_HASH_PROGRESS_VISIBLE_MS - elapsed);
  }

  function closeSourcePanelAfterApply() {
    sourcePanelCloseKey.value += 1;
  }

  function openSourcePanelForLocalFile(issue: LocalFileSourceIssue = "select_required") {
    localFileSourceIssue.value = issue;
    sourcePanelOpenKey.value += 1;
  }

  function markRoomLocalFilePending(issue: LocalFileSourceIssue = "select_required") {
    openSourcePanelForLocalFile(issue);
    handleResourceStatusChange("stalling");
  }

  function syncRoomLocalFileRequirement() {
    if (!roomRuntimeLocalFileHash.value) {
      localFileSourceIssue.value = "none";
      return true;
    }

    if (hasMatchingRoomLocalFile.value) {
      localFileSourceIssue.value = "none";
      return true;
    }

    markRoomLocalFilePending("select_required");
    return false;
  }

  function canUseRoomRuntimePlaybackCommands() {
    if (!options.realtime.isRealtimeActive.value) return false;

    if (options.playback.playbackSourceType.value === "local_file") {
      return hasMatchingRoomLocalFile.value;
    }

    return (
      options.playback.playbackSourceType.value === "external_url" &&
      options.playback.playbackSourceUrl.value.trim().length > 0
    );
  }

  function getRealtimeErrorReason(error: unknown) {
    if (!error || typeof error !== "object") return "";
    const reason = (error as { reason?: unknown }).reason;
    return typeof reason === "string" ? reason : "";
  }

  function getRealtimeErrorDetails(error: unknown) {
    if (!error || typeof error !== "object") return null;
    const details = (error as { details?: unknown }).details;
    return details && typeof details === "object"
      ? details as Record<string, unknown>
      : null;
  }

  function showRealtimePlaybackError(error?: unknown) {
    const reason = getRealtimeErrorReason(error);
    const reasonKey = reason ? `room.playback.errors.${reason}` : "";
    const details = getRealtimeErrorDetails(error);
    const stallingUserIds = Array.isArray(details?.stalling_user_ids)
      ? details.stalling_user_ids
      : [];

    toasts.push({
      message: reasonKey && options.te(reasonKey)
        ? options.t(reasonKey, { count: stallingUserIds.length })
        : options.t("room.playback.errors.playFailed"),
      tone: "danger",
    });
  }

  function showRealtimePlaybackPermissionDenied() {
    showRealtimePlaybackError({
      reason: "room_video_control_permission_denied",
    });
  }

  function ensureRealtimePlaybackControlAllowed() {
    if (canControlRealtimePlayback.value) return true;

    showRealtimePlaybackPermissionDenied();
    return false;
  }

  function logPlaybackDebug(event: string, extra: Record<string, unknown> = {}) {
    if (!ROOM_PLAYBACK_DEBUG) return;

    console.info("[iCinema room playback debug]", {
      event,
      roomId: options.roomId.value,
      realtimeActive: options.realtime.isRealtimeActive.value,
      realtimeStatus: options.realtime.realtimeStatus.value,
      playbackIsPlaying: options.playback.playbackIsPlaying.value,
      playbackCurrentTime: options.playback.playbackCurrentTime.value,
      playbackDuration: options.playback.playbackDuration.value,
      playbackSourceType: options.playback.playbackSourceType.value,
      hasExternalSource: options.playback.playbackSourceUrl.value.trim().length > 0,
      localResourceStatus: localResourceStatus.value,
      roomPlayback: options.realtime.roomPlayback.value,
      roomPlaybackEvent: options.realtime.roomPlaybackEvent.value,
      ...extra,
    });
  }

  async function syncRoomRuntimeAfterUnlock() {
    let currentVideoSource = options.realtime.roomVideoSource.value;
    let currentPlayback = options.realtime.roomPlayback.value;

    try {
      const runtime = await options.realtime.fetchVideoRuntimeSnapshot({ updateState: false });
      currentVideoSource = runtime?.room_video_source ?? null;
      currentPlayback = runtime?.playback ?? null;
    } catch (error) {
      logPlaybackDebug("syncRoomRuntimeAfterUnlockFailed", {
        errorName: error instanceof Error ? error.name : null,
        errorMessage: error instanceof Error ? error.message : String(error),
      });
    }

    await applyRoomRuntimeSnapshot(currentVideoSource, currentPlayback);
  }

  async function applyRoomRuntimeSnapshot(
    currentVideoSource: RoomRealtimeVideoSourceState | null,
    currentPlayback: RoomRealtimePlaybackState | null,
  ) {
    options.playback.applyRealtimeVideoSource(currentVideoSource);
    if (currentVideoSource?.source_type === "local_file" && !syncRoomLocalFileRequirement()) {
      return;
    }

    if (currentPlayback) {
      await options.playback.applyRealtimePlaybackState(currentPlayback, { syncPosition: true });
      return;
    }

    if (!currentVideoSource) return;

    await options.playback.applyRealtimePlaybackState({
      room_id: currentVideoSource.room_id,
      status: "paused",
      position_seconds: 0,
      anchor_ts_ms: Date.now(),
      playback_rate: 1,
    }, {
      syncPosition: true,
    });
  }

  async function handleManualSyncNow() {
    if (!isSyncGateUnlocked()) {
      unlockSyncGate();
      return;
    }

    if (!options.realtime.isRealtimeActive.value) return;

    try {
      const runtime = await options.realtime.fetchVideoRuntimeSnapshot({ updateState: false });
      await applyRoomRuntimeSnapshot(
        runtime?.room_video_source ?? null,
        runtime?.playback ?? null,
      );
    } catch (error) {
      logPlaybackDebug("manualSyncRuntimeFetchFailed", {
        errorName: error instanceof Error ? error.name : null,
        errorMessage: error instanceof Error ? error.message : String(error),
      });
      showRealtimePlaybackError(error);
    }
  }

  function unlockSyncGate() {
    if (isSyncGateUnlocked()) return;

    syncGateState.value = "unlocked";
    localResourceStatus.value = latestResourceStatus.value;
    reportDisplayedResourceStatus(latestResourceStatus.value);
    void syncRoomRuntimeAfterUnlock();
  }

  function handlePlaybackPlayStateChange(value: boolean) {
    logPlaybackDebug("localPlayStateChange", { value });
    options.playback.playbackIsPlaying.value = value;
  }

  async function handleApplyPlaybackSource(payload: PlaybackSourcePayload) {
    localFileSourceIssue.value = "none";

    if (payload.sourceType === "local_file") {
      const localFileAction = payload.localFileAction ??
        (roomRuntimeLocalFileHash.value ? "match_room_target" : "set_room_target");
      const selectedLocalFile = payload.localFile;

      if (!selectedLocalFile) {
        markRoomLocalFilePending("select_required");
        return;
      }

      if (!options.realtime.isRealtimeActive.value) {
        options.playback.applyLocalPlaybackSource({
          ...payload,
          localFile: selectedLocalFile,
        });
        closeSourcePanelAfterApply();
        return;
      }

      sourceApplying.value = true;
      sourceHashProgress.value = 0;
      const hashStartedAt = performance.now();
      let localFileHash = "";
      try {
        localFileHash = await computeFileSha256(selectedLocalFile, {
          onProgress: (progress) => {
            sourceHashProgress.value = progress.percent;
          },
        });
        sourceHashProgress.value = 100;
        await keepHashProgressVisibleSince(hashStartedAt);
      } catch {
        localFileSourceIssue.value = "hash_failed";
        sourcePanelOpenKey.value += 1;
        await keepHashProgressVisibleSince(hashStartedAt);
        sourceApplying.value = false;
        sourceHashProgress.value = null;
        return;
      }

      try {
        if (localFileAction === "match_room_target") {
          const runtimeLocalFileHash = roomRuntimeLocalFileHash.value;
          if (!runtimeLocalFileHash) {
            markRoomLocalFilePending("select_required");
            return;
          }

          if (localFileHash !== runtimeLocalFileHash) {
            markRoomLocalFilePending("hash_mismatch");
            return;
          }

          options.playback.applyLocalPlaybackSource({
            ...payload,
            localFile: selectedLocalFile,
            localFileHash,
          });
          localFileSourceIssue.value = "none";

          if (options.realtime.roomPlayback.value) {
            await options.playback.applyRealtimePlaybackState(options.realtime.roomPlayback.value, { syncPosition: true });
          }
          closeSourcePanelAfterApply();
          return;
        }

        if (!ensureRealtimePlaybackControlAllowed()) return;

        const response = await setRoomRealtimeVideoSource({
          source_type: "local_file",
          file_hash: localFileHash,
          anchor_ts_ms: Date.now(),
        });
        options.playback.applyLocalPlaybackSource({
          ...payload,
          localFile: selectedLocalFile,
          localFileHash,
        });
        if ("room_video_source" in response) {
          options.playback.applyRealtimeVideoSource(response.room_video_source ?? null);
        }
        await options.playback.applyRealtimePlaybackState(response.playback ?? null, { syncPosition: true });
        closeSourcePanelAfterApply();
      } catch (error) {
        showRealtimePlaybackError(error);
      } finally {
        sourceApplying.value = false;
        sourceHashProgress.value = null;
      }
      return;
    }

    if (!options.realtime.isRealtimeActive.value) {
      options.playback.applyLocalPlaybackSource(payload);
      closeSourcePanelAfterApply();
      return;
    }

    if (!ensureRealtimePlaybackControlAllowed()) return;

    try {
      const response = await setRoomRealtimeVideoSource({
        source_type: "external_url",
        external_url: payload.externalUrl.trim(),
        anchor_ts_ms: Date.now(),
      });
      if ("room_video_source" in response) {
        options.playback.applyRealtimeVideoSource(response.room_video_source ?? null);
      }
      await options.playback.applyRealtimePlaybackState(response.playback ?? null, { syncPosition: true });
      closeSourcePanelAfterApply();
    } catch (error) {
      showRealtimePlaybackError(error);
    }
  }

  async function togglePlayback() {
    logPlaybackDebug("togglePlaybackRequested", {
      commandMode: canUseRoomRuntimePlaybackCommands() ? "realtime" : "local",
    });

    if (!isSyncGateUnlocked()) {
      unlockSyncGate();
      return;
    }

    if (roomRuntimeLocalFileHash.value && !hasMatchingRoomLocalFile.value) {
      markRoomLocalFilePending("select_required");
      return;
    }

    if (!canUseRoomRuntimePlaybackCommands()) {
      options.playback.toggleLocalPlayback();
      return;
    }

    if (!ensureRealtimePlaybackControlAllowed()) return;

    try {
      const payload = {
        position_seconds: options.playback.playbackCurrentTime.value,
        anchor_ts_ms: Date.now(),
        playback_rate: 1,
      };
      const action = options.playback.playbackIsPlaying.value ? "playback_pause" : "playback_play";
      logPlaybackDebug("sendPlaybackCommand", {
        action,
        payload,
      });
      const response = options.playback.playbackIsPlaying.value
        ? await sendRoomRealtimePlaybackPause(payload)
        : await sendRoomRealtimePlaybackPlay(payload);
      logPlaybackDebug("playbackCommandAck", {
        action,
        response,
      });
      await options.playback.applyRealtimePlaybackState(response.playback ?? null);
    } catch (error) {
      logPlaybackDebug("playbackCommandFailed", {
        errorName: error instanceof Error ? error.name : null,
        errorMessage: error instanceof Error ? error.message : String(error),
      });
      showRealtimePlaybackError(error);
    }
  }

  function handlePlaybackProgressChange(value: number) {
    if (!isSyncGateUnlocked()) {
      unlockSyncGate();
      return;
    }

    if (roomRuntimeLocalFileHash.value && !hasMatchingRoomLocalFile.value) {
      markRoomLocalFilePending("select_required");
      return;
    }

    if (!canUseRoomRuntimePlaybackCommands() || options.playback.playbackDuration.value <= 0) {
      options.playback.handleLocalPlaybackProgressChange(value);
      return;
    }

    if (!ensureRealtimePlaybackControlAllowed()) return;

    const normalizedValue = Math.min(100, Math.max(0, value));
    const positionSeconds = options.playback.playbackDuration.value * (normalizedValue / 100);
    void sendRoomRealtimePlaybackSeek({
      position_seconds: positionSeconds,
      anchor_ts_ms: Date.now(),
    }).then((response) => {
      void options.playback.applyRealtimePlaybackState(response.playback ?? null, { syncPosition: true });
    }).catch(showRealtimePlaybackError);
  }

  function reportDisplayedResourceStatus(status: DisplayResourceStatus) {
    if (!options.realtime.isRealtimeActive.value) return;
    if (status === "idle") {
      lastReportedResourceStatus = null;
      return;
    }

    if (status === lastReportedResourceStatus) return;

    lastReportedResourceStatus = status;
    void sendRoomRealtimeUserResourceStatus({
      status,
      reported_at_ms: Date.now(),
      position_seconds: options.playback.playbackCurrentTime.value,
    }).catch(() => {
      // Status reporting is opportunistic; playback commands surface their own errors.
    });
  }

  function handleResourceStatusChange(status: DisplayResourceStatus) {
    const nextStatus =
      roomRuntimeLocalFileHash.value && !hasMatchingRoomLocalFile.value && status !== "error"
        ? "stalling"
        : status;

    latestResourceStatus.value = nextStatus;
    if (!isSyncGateUnlocked()) {
      localResourceStatus.value = "idle";
      return;
    }

    localResourceStatus.value = nextStatus;
    reportDisplayedResourceStatus(nextStatus);
  }

  function handleRealtimeVideoSourceEvent(event: RoomRealtimeVideoSourceEvent | null) {
    if (!event) return;
    if (!isSyncGateUnlocked()) return;

    options.playback.applyRealtimeVideoSource(event.state);
    if (event.action !== "room_video_source_set" || !event.state) return;
    if (event.state.source_type === "local_file" && !syncRoomLocalFileRequirement()) {
      return;
    }
    if (event.state.source_type === "external_url") {
      localFileSourceIssue.value = "none";
    }

    void options.playback.applyRealtimePlaybackState({
      room_id: event.state.room_id,
      status: "paused",
      position_seconds: 0,
      anchor_ts_ms: Date.now(),
      playback_rate: 1,
    }, {
      syncPosition: true,
    });
  }

  function handleRealtimePlaybackEvent(event: RoomRealtimePlaybackEvent | null) {
    logPlaybackDebug("applyRealtimePlaybackEvent", {
      action: event?.action ?? null,
      state: event?.state ?? null,
      syncPosition: event?.action === "snapshot" || event?.action === "playback_seek",
    });
    if (!isSyncGateUnlocked()) return;
    if (roomRuntimeLocalFileHash.value && !hasMatchingRoomLocalFile.value) {
      markRoomLocalFilePending("select_required");
      return;
    }

    void options.playback.applyRealtimePlaybackState(event?.state ?? null, {
      syncPosition: event?.action === "snapshot" || event?.action === "playback_seek",
    });
  }

  function resetPlaybackSyncState() {
    localResourceStatus.value = "idle";
    latestResourceStatus.value = "idle";
    lastReportedResourceStatus = null;
    syncGateState.value = getInitialSyncGateState();
    localFileSourceIssue.value = "none";
    sourceApplying.value = false;
    sourceHashProgress.value = null;
    sourcePanelOpenKey.value = 0;
    sourcePanelCloseKey.value = 0;
  }

  return {
    syncGateState,
    localResourceStatus,
    latestResourceStatus,
    sourcePanelOpenKey,
    sourcePanelCloseKey,
    sourceApplying,
    sourceHashProgress,
    canControlRealtimePlayback,
    roomRuntimeLocalFileHash,
    hasMatchingRoomLocalFile,
    needsRoomLocalFileSelection,
    sourcePanelMessage,
    sourcePanelMessageTone,
    syncRoomRuntimeAfterUnlock,
    unlockSyncGate,
    handleManualSyncNow,
    handlePlaybackPlayStateChange,
    handleApplyPlaybackSource,
    togglePlayback,
    handlePlaybackProgressChange,
    handleResourceStatusChange,
    handleRealtimeVideoSourceEvent,
    handleRealtimePlaybackEvent,
    resetPlaybackSyncState,
  };
}
