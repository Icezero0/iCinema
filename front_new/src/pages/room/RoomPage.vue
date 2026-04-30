<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, type Component } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  ChatBubbleLeftRightIcon,
  Cog6ToothIcon,
  UserGroupIcon,
  ClipboardDocumentCheckIcon,
} from "@heroicons/vue/24/outline";
import {
  getRoomById,
  getRoomMembers,
  type Room,
} from "@/infra/api/rooms.api";
import BasePill from "@/ui/base/BasePill.vue";
import AppTabs from "@/ui/layout/AppTabs.vue";
import RoomPlayerStage from "@/features/room/components/RoomPlayerStage.vue";
import RoomPlaybackControls from "@/features/room/components/RoomPlaybackControls.vue";
import RoomChatTab from "@/features/room/components/workspace/RoomChatTab.vue";
import RoomMembersTab from "@/features/room/components/workspace/RoomMembersTab.vue";
import RoomRequestsTab from "@/features/room/components/workspace/RoomRequestsTab.vue";
import RoomSettingsTab from "@/features/room/components/workspace/RoomSettingsTab.vue";
import type { RoomPanelKey, RoomRole } from "@/features/room/types";
import type { ChatSegment } from "@/features/chat/types";
import { useRoomTheaterLayout } from "@/features/room/composables/useRoomTheaterLayout";
import { useRoomWorkspaceLayout } from "@/features/room/composables/useRoomWorkspaceLayout";
import { useRoomSettingsState } from "@/features/room/composables/useRoomSettingsState";
import {
  useRoomPlaybackState,
  type RoomPlayerStageHandle,
} from "@/features/room/composables/useRoomPlaybackState";
import { useRoomJoinRequests } from "@/features/room/composables/useRoomJoinRequests";
import { useRoomMemberActions } from "@/features/room/composables/useRoomMemberActions";
import { useRoomRealtimeSession } from "@/features/room/composables/useRoomRealtimeSession";
import {
  sendRoomRealtimePlaybackPause,
  sendRoomRealtimePlaybackPlay,
  sendRoomRealtimePlaybackSeek,
  sendRoomRealtimeUserPlayerStatus,
  setRoomRealtimeVideoSource,
  type RoomRealtimePlayerStatus,
  type RoomRealtimeSessionClosed,
} from "@/infra/realtime/roomRealtime";
import { useMessagesStore } from "@/stores/messages.store";
import { useEntitiesStore } from "@/stores/entities.store";
import { useAuthStore } from "@/stores/auth.store";
import { useToastsStore } from "@/stores/toasts.store";
import { resolveMediaUrl } from "@/infra/media";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const entitiesStore = useEntitiesStore();
const messagesStore = useMessagesStore();
const toasts = useToastsStore();

type RoomRoleState = RoomRole | "unknown";
type DisplayPlayerStatus = "idle" | RoomRealtimePlayerStatus;
type SyncGateState = "locked" | "unlocked";
const ROOM_PLAYBACK_DEBUG = false;

const room = ref<Room | null>(null);
const isLoading = ref(false);
const error = ref("");
const membersLoading = ref(false);
const membersError = ref("");
const mainGridRef = ref<HTMLElement | null>(null);
const playerStageRef = ref<RoomPlayerStageHandle | null>(null);
let lastReportedPlayerStatus: RoomRealtimePlayerStatus | null = null;
const localPlayerStatus = ref<DisplayPlayerStatus>("idle");
const latestPlayerStatus = ref<DisplayPlayerStatus>("idle");
const syncGateState = ref<SyncGateState>(getInitialSyncGateState());

const roomId = computed(() => {
  const raw = route.params.id;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
});

const currentUserRole = ref<RoomRoleState>("unknown");
const activePanel = ref<RoomPanelKey>("chat");
const panelBeforeTheater = ref<RoomPanelKey>("chat");
const canManageRoomRequests = computed(() =>
  currentUserRole.value === "owner" || currentUserRole.value === "manager");
const currentUserIsOwner = computed(() => currentUserRole.value === "owner");
const currentUserCanRemoveMembers = computed(() =>
  currentUserRole.value === "owner" || currentUserRole.value === "manager");
const memberDangerActionDisabled = computed(() => currentUserRole.value === "unknown");

const allPanelOptions = computed<{ key: RoomPanelKey; label: string; badge?: string; icon?: Component }[]>(() => [
  { key: "chat", label: t("room.tabs.chat"), icon: ChatBubbleLeftRightIcon },
  { key: "members", label: t("room.tabs.members"), icon: UserGroupIcon },
  {
    key: "requests",
    label: t("room.tabs.requests"),
    badge: roomJoinRequests.value.length > 0 ? String(roomJoinRequests.value.length) : undefined,
    icon: ClipboardDocumentCheckIcon,
  },
  { key: "settings", label: t("room.tabs.settings"), icon: Cog6ToothIcon },
]);

const panelOptions = computed(() => {
  if (!canManageRoomRequests.value) {
    return allPanelOptions.value.filter((panel) =>
      panel.key === "chat" || panel.key === "members" || panel.key === "settings");
  }

  return allPanelOptions.value;
});

const roomMessagesState = computed(() => messagesStore.getRoomState(roomId.value));
const roomChatMessages = computed(() => messagesStore.getRoomChatMessages(roomId.value));
const entityRoomMembers = computed(() => entitiesStore.getRoomMembers(roomId.value));
const playback = useRoomPlaybackState({
  roomId,
  playerStageRef,
  t,
});
const {
  playbackIsPlaying,
  playbackDisplayProgress,
  playbackBufferedProgress,
  playbackBufferedRanges,
  playbackCanSeek,
  playbackVolume,
  playbackCurrentTime,
  playbackDuration,
  playbackSourceType,
  playbackSourceUrl,
  playbackSourceFile,
  playbackSourceFileName,
  playbackSourceRevision,
  playbackTimelineLabel,
  togglePlayback: toggleLocalPlayback,
  handlePlaybackProgressChange: handleLocalPlaybackProgressChange,
  handlePlaybackDurationChange,
  handlePlaybackTimeChange,
  handleApplyPlaybackSource: applyLocalPlaybackSource,
  applyRealtimeVideoSource,
  applyRealtimePlaybackState,
  handleCopyPlayerScreenshot,
  loadLocalPlaybackVolume,
  handlePlaybackVolumeChange,
  handlePlaybackCanSeekChange,
  resetPlaybackState,
  resetPlaybackVolume,
} = playback;
const memberActions = useRoomMemberActions({
  roomId,
  router,
  t,
  syncCurrentUserRole,
  fetchRoomRequests: (options) => fetchRoomRequests(options),
});
const {
  isLeavingRoom,
  isDisbandingRoom,
  invitingMemberUserIds,
  settingManagerUserIds,
  removingMemberUserIds,
  handleLeaveRoom,
  handleDisbandRoom,
  handleInviteUser,
  handleSetMemberManager,
  handleUnsetMemberManager,
  handleRemoveRoomMember,
  resetMemberActionState,
} = memberActions;
const {
  requestsLoading,
  requestsError,
  roomJoinRequests,
  roomRequestItems,
  pendingMemberInviteStates,
  fetchRoomRequests,
  isRequestActionLoading,
  approveRequest,
  rejectRequest,
  resetRoomRequestsState,
} = useRoomJoinRequests({
  roomId,
  canManageRoomRequests,
  optimisticInviteUserIds: invitingMemberUserIds,
  t,
});
const layout = useRoomWorkspaceLayout({
  activePanel,
  roomId: computed(() => room.value?.id),
  isLoading,
});
const theaterLayout = useRoomTheaterLayout(roomId);
const mainGridStyle = computed(() => layout.mainGridStyle.value);
const workspaceCardStyle = computed(() => layout.workspaceCardStyle.value);
const effectiveMainGridStyle = computed(() =>
  theaterLayout.isTheaterMode.value
    ? theaterLayout.theaterMainGridStyle.value
    : mainGridStyle.value);
const effectiveWorkspaceCardStyle = computed(() =>
  theaterLayout.isTheaterMode.value ? undefined : workspaceCardStyle.value);
const hasOlderMessages = computed(() => roomMessagesState.value.nextBeforeId != null);
const {
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
} = useRoomSettingsState({
  roomId,
  room,
  currentUserRole,
  canManageRoomSettings: canManageRoomRequests,
  isOwner: currentUserIsOwner,
});
const realtime = useRoomRealtimeSession({
  roomId,
  refreshRoom: fetchRoom,
  refreshRoomMembers: fetchRoomMembers,
  refreshRoomRequests: () => fetchRoomRequests({ force: true }),
  refreshRoomSettings: fetchRoomSettings,
  onSessionClosed: handleRealtimeSessionClosed,
});
const presentUserIds = computed(() => new Set(realtime.presentUserIds.value));
const displayPlayerStatusByUserId = computed(() => {
  const statuses = new Map<number, DisplayPlayerStatus>(
    realtime.userPlayerStates.value.map((state) => [state.user_id, state.status]),
  );
  if (auth.me?.id && realtime.isRealtimeActive.value && presentUserIds.value.has(auth.me.id)) {
    statuses.set(auth.me.id, localPlayerStatus.value);
  }
  return statuses;
});
const roomMemberItems = computed(() => entityRoomMembers.value.map((member) => {
  const user = entitiesStore.getUser(member.user_id);
  const memberStatus =
    realtime.hasPresenceSnapshot.value && presentUserIds.value.has(member.user_id)
      ? displayPlayerStatusByUserId.value.get(member.user_id) ?? "idle"
      : "offline";

  return {
    id: member.user_id,
    name:
      user?.username ||
      user?.email ||
      `User #${member.user_id}`,
    email: user?.email ?? null,
    avatarUrl: resolveMediaUrl(user?.avatar_url),
    role: member.role,
    status: memberStatus,
  };
}));
const roomMemberStatusByUserId = computed(() =>
  new Map(roomMemberItems.value.map((member) => [member.id, member.status])));
const syncPolicyStatusLabel = computed(() => {
  if (roomSettingsError.value && !roomSettings.value) {
    return t("room.playback.syncPolicyUnavailable");
  }

  if (!roomSettings.value) {
    return t("room.playback.syncPolicyLoading");
  }

  if (roomSettings.value?.sync_policy === "disabled") {
    return t("room.playback.syncPolicyManual");
  }

  return t("room.playback.syncPolicyAuto");
});

function isTheaterFullscreenActive() {
  return Boolean(
    mainGridRef.value &&
      document.fullscreenElement === mainGridRef.value,
  );
}

async function enterTheaterFullscreen() {
  try {
    await mainGridRef.value?.requestFullscreen?.();
  } catch {
    // The CSS theater layout still works when browser fullscreen is unavailable.
  }
}

async function exitTheaterFullscreen() {
  if (!isTheaterFullscreenActive()) return;

  try {
    await document.exitFullscreen?.();
  } catch {
    // Browser may already be exiting fullscreen.
  }
}

async function toggleTheaterMode() {
  if (theaterLayout.isTheaterMode.value) {
    await exitTheaterFullscreen();
    theaterLayout.setTheaterMode(false);
    activePanel.value = panelBeforeTheater.value;
    return;
  }

  if (!theaterLayout.canUseTheaterMode.value) return;

  panelBeforeTheater.value = activePanel.value;
  activePanel.value = "chat";
  theaterLayout.setTheaterMode(true);
  await enterTheaterFullscreen();
}

function syncTheaterFullscreenState() {
  if (!theaterLayout.isTheaterMode.value) return;
  if (document.fullscreenElement) return;

  theaterLayout.setTheaterMode(false);
  activePanel.value = panelBeforeTheater.value;
}

function syncCurrentUserRole() {
  const meId = auth.me?.id;
  if (!meId) {
    currentUserRole.value = "unknown";
    return;
  }

  if (room.value?.owner_id === meId) {
    currentUserRole.value = "owner";
    return;
  }

  const selfMember = entityRoomMembers.value.find((member) => member.user_id === meId);
  if (selfMember) {
    currentUserRole.value = selfMember.role;
    return;
  }

  currentUserRole.value = "unknown";
}

async function fetchRoom() {
  if (!roomId.value) {
    error.value = t("room.invalidId");
    return;
  }

  isLoading.value = true;
  error.value = "";

  try {
    room.value = await getRoomById(roomId.value);
    entitiesStore.upsertRoom(room.value);
    loadLocalSyncStrategy();
    loadLocalPlaybackVolume();
    syncCurrentUserRole();
  } catch (e: any) {
    room.value = null;
    error.value =
      e?.response?.data?.detail ||
      e?.message ||
      t("room.loadFailed");
  } finally {
    isLoading.value = false;
  }
}

async function fetchRoomMembers() {
  if (!roomId.value) {
    membersError.value = t("room.invalidId");
    return;
  }

  membersLoading.value = true;
  membersError.value = "";

  try {
    const response = await getRoomMembers(roomId.value);
    entitiesStore.upsertRoomMembers(response.items);
    syncCurrentUserRole();
    await fetchRoomRequests({ force: true });
  } catch (e: any) {
    membersError.value =
      e?.response?.data?.detail ||
      e?.message ||
      t("room.membersLoadFailed");
  } finally {
    membersLoading.value = false;
  }
}

async function fetchRoomMessages() {
  if (!roomId.value) return;

  try {
    await messagesStore.refreshRoomMessages(roomId.value, 20);
  } catch {
    // messages.store already keeps the error state for the panel
  }
}

async function loadOlderRoomMessages() {
  if (!roomId.value) return;

  try {
    await messagesStore.loadOlderMessages(roomId.value, 20);
  } catch {
    // messages.store already keeps the error state for the panel
  }
}

async function handleSend(segments: ChatSegment[]) {
  if (!roomId.value) return;

  try {
    await messagesStore.sendSegments(roomId.value, segments);
  } catch (error) {
    // messages.store already keeps the error state for the panel
    toasts.push({
      message: t("room.chatSendFailed"),
      tone: "danger",
    });
    throw error;
  }
}

function canUseRealtimePlaybackCommands() {
  return (
    realtime.isRealtimeActive.value &&
    playbackSourceType.value === "external_url" &&
    playbackSourceUrl.value.trim().length > 0
  );
}

function showRealtimePlaybackError() {
  toasts.push({
    message: t("room.playback.errors.playFailed"),
    tone: "danger",
  });
}

function logPlaybackDebug(event: string, extra: Record<string, unknown> = {}) {
  if (!ROOM_PLAYBACK_DEBUG) return;

  console.info("[iCinema room playback debug]", {
    event,
    roomId: roomId.value,
    realtimeActive: realtime.isRealtimeActive.value,
    realtimeStatus: realtime.realtimeStatus.value,
    playbackIsPlaying: playbackIsPlaying.value,
    playbackCurrentTime: playbackCurrentTime.value,
    playbackDuration: playbackDuration.value,
    playbackSourceType: playbackSourceType.value,
    hasExternalSource: playbackSourceUrl.value.trim().length > 0,
    localPlayerStatus: localPlayerStatus.value,
    roomPlayback: realtime.roomPlayback.value,
    roomPlaybackEvent: realtime.roomPlaybackEvent.value,
    ...extra,
  });
}

function isSyncGateUnlocked() {
  return syncGateState.value === "unlocked";
}

function getInitialSyncGateState(): SyncGateState {
  return route.meta.requiresSyncGate === true ? "locked" : "unlocked";
}

async function syncRoomRuntimeAfterUnlock() {
  // TODO: call the backend runtime snapshot command once it is available.
  const currentVideoSource = realtime.roomVideoSource.value;
  const currentPlayback = realtime.roomPlayback.value;

  applyRealtimeVideoSource(currentVideoSource);

  if (currentPlayback) {
    await applyRealtimePlaybackState(currentPlayback, { syncPosition: true });
    return;
  }

  if (!currentVideoSource) return;

  await applyRealtimePlaybackState({
    room_id: currentVideoSource.room_id,
    status: "paused",
    position_seconds: 0,
    anchor_ts_ms: Date.now(),
    playback_rate: 1,
  }, {
    syncPosition: true,
  });
}

function unlockSyncGate() {
  if (isSyncGateUnlocked()) return;

  syncGateState.value = "unlocked";
  localPlayerStatus.value = latestPlayerStatus.value;
  reportDisplayedPlayerStatus(latestPlayerStatus.value);
  void syncRoomRuntimeAfterUnlock();
}

function handlePlaybackPlayStateChange(value: boolean) {
  logPlaybackDebug("localPlayStateChange", { value });
  playbackIsPlaying.value = value;
}

async function handleApplyPlaybackSource(payload: {
  sourceType: "external_url" | "local_file";
  externalUrl: string;
  localFile: File | null;
}) {
  if (!realtime.isRealtimeActive.value || payload.sourceType === "local_file") {
    applyLocalPlaybackSource(payload);
    return;
  }

  try {
    const response = await setRoomRealtimeVideoSource({
      source_type: "external_url",
      external_url: payload.externalUrl.trim(),
      anchor_ts_ms: Date.now(),
    });
    if ("room_video_source" in response) {
      applyRealtimeVideoSource(response.room_video_source ?? null);
    }
    await applyRealtimePlaybackState(response.playback ?? null, { syncPosition: true });
  } catch {
    showRealtimePlaybackError();
  }
}

async function togglePlayback() {
  logPlaybackDebug("togglePlaybackRequested", {
    commandMode: canUseRealtimePlaybackCommands() ? "realtime" : "local",
  });

  if (!isSyncGateUnlocked()) {
    unlockSyncGate();
    return;
  }

  if (!canUseRealtimePlaybackCommands()) {
    toggleLocalPlayback();
    return;
  }

  try {
    const payload = {
      position_seconds: playbackCurrentTime.value,
      anchor_ts_ms: Date.now(),
      playback_rate: 1,
    };
    const action = playbackIsPlaying.value ? "playback_pause" : "playback_play";
    logPlaybackDebug("sendPlaybackCommand", {
      action,
      payload,
    });
    const response = playbackIsPlaying.value
      ? await sendRoomRealtimePlaybackPause(payload)
      : await sendRoomRealtimePlaybackPlay(payload);
    logPlaybackDebug("playbackCommandAck", {
      action,
      response,
    });
    await applyRealtimePlaybackState(response.playback ?? null);
  } catch (error) {
    logPlaybackDebug("playbackCommandFailed", {
      errorName: error instanceof Error ? error.name : null,
      errorMessage: error instanceof Error ? error.message : String(error),
    });
    showRealtimePlaybackError();
  }
}

function handlePlaybackProgressChange(value: number) {
  if (!isSyncGateUnlocked()) {
    unlockSyncGate();
    return;
  }

  handleLocalPlaybackProgressChange(value);
  if (!canUseRealtimePlaybackCommands() || playbackDuration.value <= 0) return;

  const normalizedValue = Math.min(100, Math.max(0, value));
  const positionSeconds = playbackDuration.value * (normalizedValue / 100);
  void sendRoomRealtimePlaybackSeek({
    position_seconds: positionSeconds,
    anchor_ts_ms: Date.now(),
  }).then((response) => {
    void applyRealtimePlaybackState(response.playback ?? null, { syncPosition: true });
  }).catch(showRealtimePlaybackError);
}

function toRealtimePlayerStatus(status: DisplayPlayerStatus): RoomRealtimePlayerStatus {
  return status === "idle" ? "ready" : status;
}

function reportDisplayedPlayerStatus(status: DisplayPlayerStatus) {
  if (!realtime.isRealtimeActive.value) return;
  const realtimeStatus = toRealtimePlayerStatus(status);
  if (realtimeStatus === lastReportedPlayerStatus) return;

  lastReportedPlayerStatus = realtimeStatus;
  void sendRoomRealtimeUserPlayerStatus({
    status: realtimeStatus,
    reported_at_ms: Date.now(),
    position_seconds: playbackCurrentTime.value,
  }).catch(() => {
    // Status reporting is opportunistic; playback commands surface their own errors.
  });
}

function handlePlayerStatusChange(status: DisplayPlayerStatus) {
  latestPlayerStatus.value = status;
  if (!isSyncGateUnlocked()) {
    localPlayerStatus.value = "idle";
    return;
  }

  localPlayerStatus.value = status;
  reportDisplayedPlayerStatus(status);
}

function handleRealtimeSessionClosed(payload: RoomRealtimeSessionClosed) {
  toasts.push({
    message: t(`room.realtime.sessionClosed.${payload.reason}`),
    tone: "warning",
  });

  if (payload.reason === "removed_from_room" || payload.reason === "room_deleted") {
    void router.push("/");
  }
}

onMounted(() => {
  document.addEventListener("fullscreenchange", syncTheaterFullscreenState);
  void fetchRoom();
  void fetchRoomMessages();
  void fetchRoomMembers();
});

onBeforeUnmount(() => {
  document.removeEventListener("fullscreenchange", syncTheaterFullscreenState);
});
watch(roomId, () => {
  currentUserRole.value = "unknown";
  localPlayerStatus.value = "idle";
  latestPlayerStatus.value = "idle";
  lastReportedPlayerStatus = null;
  syncGateState.value = getInitialSyncGateState();
  resetRoomRequestsState();
  resetRoomSettingsState();
  resetMemberActionState();
  resetPlaybackVolume();
  resetPlaybackState();
  theaterLayout.setTheaterMode(false);
  void fetchRoom();
  void fetchRoomMessages();
  void fetchRoomMembers();
});
watch(panelOptions, (nextPanels) => {
  if (!nextPanels.some((panel) => panel.key === activePanel.value)) {
    activePanel.value = nextPanels[0]?.key ?? "chat";
  }
});
watch(() => auth.me?.id, () => {
  syncCurrentUserRole();
});
watch([roomId, currentUserRole], () => {
  void fetchRoomRequests();
  void fetchRoomSettings();
});
watch(activePanel, (panel) => {
  if (panel === "requests") {
    void fetchRoomRequests();
  }
});

watch(
  () => realtime.roomVideoSourceEvent.value,
  (event) => {
    if (!event) return;
    if (!isSyncGateUnlocked()) return;

    applyRealtimeVideoSource(event.state);
    if (event.action !== "room_video_source_set" || !event.state) return;

    void applyRealtimePlaybackState({
      room_id: event.state.room_id,
      status: "paused",
      position_seconds: 0,
      anchor_ts_ms: Date.now(),
      playback_rate: 1,
    }, {
      syncPosition: true,
    });
  },
);
watch(
  () => realtime.roomPlaybackEvent.value,
  (event) => {
    logPlaybackDebug("applyRealtimePlaybackEvent", {
      action: event?.action ?? null,
      state: event?.state ?? null,
      syncPosition: event?.action === "snapshot" || event?.action === "playback_seek",
    });
    if (!isSyncGateUnlocked()) return;

    void applyRealtimePlaybackState(event?.state ?? null, {
      syncPosition: event?.action === "snapshot" || event?.action === "playback_seek",
    });
  },
);
watch(
  () => theaterLayout.isTheaterMode.value,
  (active) => {
    if (!active) {
      void exitTheaterFullscreen();
    }
  },
);
watch(
  () => theaterLayout.canUseTheaterMode.value,
  async (canUse) => {
    if (canUse || !theaterLayout.isTheaterMode.value) return;
    await exitTheaterFullscreen();
    theaterLayout.setTheaterMode(false);
    activePanel.value = panelBeforeTheater.value;
  },
);
</script>

<template>
  <BaseLayout :max-width="1320">
    <div class="roomShell">
      <div v-if="isLoading" class="state">{{ t("common.loading") }}</div>

      <div v-else-if="error" class="state error">{{ error }}</div>

      <template v-else-if="room">
        <BaseCard v-if="!theaterLayout.isTheaterMode.value" class="topStrip">
          <div class="roomIntro">
            <h2 class="roomName">{{ room.name }}</h2>
          </div>

          <div class="statusBar">
            <BasePill tone="default">{{ syncPolicyStatusLabel }}</BasePill>
          </div>
        </BaseCard>

        <div
          ref="mainGridRef"
          class="mainGrid"
          :class="{
            theaterMode: theaterLayout.isTheaterMode.value,
          }"
          :style="effectiveMainGridStyle"
        >
          <section
            :ref="(el) => { layout.setStageColumnEl(el as HTMLElement | null); }"
            class="stageColumn"
          >
            <BaseCard class="stageCard">
              <div
                class="stageContent"
                :inert="syncGateState === 'locked'"
              >
                <RoomPlayerStage
                  ref="playerStageRef"
                  class="playerStage"
                  :title="t('room.playback.emptyTitle')"
                  :hint="t('room.playback.emptyHint')"
                  :source-type="playbackSourceType"
                  :source-url="playbackSourceUrl"
                  :source-file="playbackSourceFile"
                  :source-revision="playbackSourceRevision"
                  :volume="playbackVolume"
                  :video-fullscreen-label="t('room.playback.controls.videoFullscreen')"
                  :exit-video-fullscreen-label="t('room.playback.controls.exitVideoFullscreen')"
                  :theater-mode-label="t('room.playback.controls.theaterMode')"
                  :exit-theater-mode-label="t('room.playback.controls.exitTheaterMode')"
                  :is-theater-mode="theaterLayout.isTheaterMode.value"
                  :theater-mode-available="theaterLayout.canUseTheaterMode.value"
                  @toggle-theater-mode="toggleTheaterMode"
                  @play-state-change="handlePlaybackPlayStateChange"
                  @player-status-change="handlePlayerStatusChange"
                  @duration-change="handlePlaybackDurationChange"
                  @time-change="handlePlaybackTimeChange"
                  @buffered-progress-change="playbackBufferedProgress = $event"
                  @buffered-ranges-change="playbackBufferedRanges = $event"
                  @seek-capability-change="handlePlaybackCanSeekChange"
                />

                <RoomPlaybackControls
                  class="playbackControls"
                  :is-playing="playbackIsPlaying"
                  :progress="playbackDisplayProgress"
                  :buffered-progress="playbackBufferedProgress"
                  :buffered-ranges="playbackBufferedRanges"
                  :seek-disabled="!playbackCanSeek"
                  :volume="playbackVolume"
                  :source-type="playbackSourceType"
                  :source-url="playbackSourceUrl"
                  :source-file-name="playbackSourceFileName"
                  :current-time="playbackCurrentTime"
                  :duration="playbackDuration"
                  :timeline-label="playbackTimelineLabel"
                  :play-label="t('room.playback.controls.play')"
                  :pause-label="t('room.playback.controls.pause')"
                  :sync-label="t('room.playback.controls.syncNow')"
                  :source-label="t('room.playback.controls.source')"
                  :source-panel-title="t('room.sourcePanel.title')"
                  :volume-label="t('room.playback.controls.volume')"
                  @toggle-play="togglePlayback"
                  @update:progress="handlePlaybackProgressChange"
                  @update:volume="handlePlaybackVolumeChange"
                  @apply-source="handleApplyPlaybackSource"
                />
              </div>

              <button
                v-if="syncGateState === 'locked'"
                class="stageSyncGateOverlay"
                type="button"
                @click="unlockSyncGate"
              >
                <span class="stageSyncGatePrompt">
                  <span class="stageSyncGateTitle">{{ t('room.playback.syncGateStart') }}</span>
                </span>
              </button>
            </BaseCard>
          </section>

          <div
            v-if="theaterLayout.isTheaterMode.value"
            class="theaterDivider"
            :class="{ resizing: theaterLayout.isResizing.value }"
            role="separator"
            aria-orientation="vertical"
            :aria-label="t('room.playback.resizeChatPanel')"
            @pointerdown="theaterLayout.startWorkspaceResize"
          >
            <span class="dividerHandle" />
          </div>

          <aside
            :ref="(el) => { layout.setWorkspaceColumnEl(el as HTMLElement | null); }"
            class="workspaceColumn"
          >
            <BaseCard
              class="workspaceCard"
              :class="{ theaterWorkspaceCard: theaterLayout.isTheaterMode.value }"
              :style="effectiveWorkspaceCardStyle"
            >
              <AppTabs
                v-if="!theaterLayout.isTheaterMode.value"
                v-model="activePanel"
                :items="panelOptions"
              />

              <RoomChatTab
                v-show="activePanel === 'chat'"
                :room-key="roomId"
                :active="activePanel === 'chat'"
                :messages="roomChatMessages"
                :member-status-by-user-id="roomMemberStatusByUserId"
                :send-label="t('room.chat.send')"
                :loading="roomMessagesState.isLoading"
                :sending="roomMessagesState.isSending"
                :loading-history="roomMessagesState.isLoadingHistory"
                :has-older="hasOlderMessages"
                :error="roomMessagesState.error"
                :loading-label="t('common.loading')"
                :empty-label="t('room.chatEmpty')"
                :send-message="handleSend"
                :capture-screenshot="handleCopyPlayerScreenshot"
                @load-older="loadOlderRoomMessages"
              />

              <RoomMembersTab
                v-show="activePanel === 'members'"
                :members="roomMemberItems"
                :search-placeholder="t('room.members.searchPlaceholder')"
                :invite-label="t('room.members.invite')"
                :leave-room-label="t('room.members.leaveRoom')"
                :disband-room-label="t('room.members.disbandRoom')"
                :is-owner="currentUserIsOwner"
                :can-remove-members="currentUserCanRemoveMembers"
                :action-disabled="memberDangerActionDisabled"
                :leaving="isLeavingRoom"
                :disbanding="isDisbandingRoom"
                :pending-join-requests="pendingMemberInviteStates"
                :setting-manager-user-ids="settingManagerUserIds"
                :removing-member-user-ids="removingMemberUserIds"
                :loading="membersLoading"
                :loading-label="t('common.loading')"
                :empty-label="membersError || t('room.membersEmpty')"
                @leave-room="handleLeaveRoom"
                @disband-room="handleDisbandRoom"
                @invite-user="handleInviteUser"
                @set-manager="handleSetMemberManager"
                @unset-manager="handleUnsetMemberManager"
                @remove-member="handleRemoveRoomMember"
              />

              <RoomRequestsTab
                v-show="activePanel === 'requests'"
                :loading="requestsLoading"
                :error="requestsError"
                :empty-label="t('room.requestsEmpty')"
                :items="roomRequestItems"
                :is-request-action-loading="isRequestActionLoading"
                @approve="approveRequest"
                @reject="rejectRequest"
              />

              <RoomSettingsTab
                v-show="activePanel === 'settings'"
                :room="room"
                :room-settings="roomSettings"
                :settings-loading="roomSettingsLoading"
                :settings-error="roomSettingsError"
                :settings-saving="roomSettingsSaving"
                :can-manage-room-settings="canManageRoomRequests"
                :is-owner="currentUserIsOwner"
                :local-sync-strategy="localSyncStrategy"
                :local-sync-options="localSyncOptions"
                @save="handleSaveRoomSettings"
              />
            </BaseCard>
          </aside>
        </div>
      </template>
    </div>
  </BaseLayout>
</template>

<style scoped>
.roomShell {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
  padding-top: 6px;
  min-height: 0;
}

.state {
  color: var(--c-text-muted);
  font-size: 14px;
}

.state.error {
  color: var(--c-danger);
}

.topStrip {
  padding: 18px 20px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  background:
    radial-gradient(circle at top right, rgb(210 233 255 / 0.75), transparent 28%),
    linear-gradient(180deg, color-mix(in srgb, var(--c-surface) 92%, white), color-mix(in srgb, var(--c-surface) 88%, var(--c-bg)));
}

.roomIntro {
  min-width: 0;
}

.roomName {
  margin: 0;
  font-size: 24px;
  color: var(--c-text);
}

.statusBar {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.mainGrid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
  gap: 16px;
  align-items: start;
}

.mainGrid.theaterMode {
  position: fixed;
  top: var(--room-visual-viewport-offset-top, 0px);
  right: 0;
  bottom: auto;
  left: 0;
  z-index: 80;
  height: var(--room-visual-viewport-height, 100dvh);
  min-height: 0;
  padding: 16px;
  box-sizing: border-box;
  gap: 0;
  align-items: stretch;
  grid-template-rows: minmax(0, 1fr);
  background:
    radial-gradient(
      circle at top left,
      color-mix(in srgb, var(--c-primary) 14%, transparent),
      transparent 34%
    ),
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--c-bg) 92%, var(--c-surface)),
      color-mix(in srgb, var(--c-surface) 84%, var(--c-bg))
    );
}

:global([data-theme="dark"]) .mainGrid.theaterMode {
  background:
    radial-gradient(circle at top left, rgb(65 93 126 / 0.26), transparent 32%),
    linear-gradient(145deg, rgb(10 14 20), rgb(18 24 34));
}

.stageColumn,
.workspaceColumn {
  min-width: 0;
}

.workspaceColumn {
  align-self: start;
  height: 100%;
  max-height: 100%;
  overflow: hidden;
}

.mainGrid.theaterMode .stageColumn,
.mainGrid.theaterMode .workspaceColumn {
  align-self: stretch;
  height: 100%;
  max-height: 100%;
  overflow: hidden;
}

.stageCard {
  position: relative;
  padding: 16px;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--c-surface) 92%, white), color-mix(in srgb, var(--c-surface) 86%, var(--c-bg)));
  overflow: hidden;
}

.stageContent {
  display: grid;
  gap: 14px;
}

.mainGrid.theaterMode .stageCard {
  height: 100%;
  min-height: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
}

.mainGrid.theaterMode .stageContent {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 12px;
}

.mainGrid.theaterMode .playerStage {
  width: 100%;
  height: 100%;
  min-height: 0;
}

.mainGrid.theaterMode .playerStage :deep(.playerSurface) {
  height: 100%;
  aspect-ratio: auto;
}

.mainGrid.theaterMode .playbackControls {
  width: 100%;
}

.stageSyncGateOverlay {
  position: absolute;
  inset: 0;
  z-index: 8;
  border: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at center, color-mix(in srgb, var(--c-primary) 14%, transparent), transparent 44%),
    color-mix(in srgb, var(--c-surface) 70%, transparent);
  color: var(--c-text);
  cursor: pointer;
  transition: background-color 160ms ease;
  backdrop-filter: blur(3px);
}

.stageSyncGateOverlay:hover {
  background:
    radial-gradient(circle at center, color-mix(in srgb, var(--c-primary) 18%, transparent), transparent 46%),
    color-mix(in srgb, var(--c-surface) 64%, transparent);
}

:global([data-theme="dark"]) .stageSyncGateOverlay {
  background:
    radial-gradient(circle at center, rgb(98 165 255 / 0.16), transparent 42%),
    rgb(3 7 12 / 0.68);
  color: rgb(245 248 252 / 0.96);
}

:global([data-theme="dark"]) .stageSyncGateOverlay:hover {
  background:
    radial-gradient(circle at center, rgb(98 165 255 / 0.22), transparent 44%),
    rgb(3 7 12 / 0.62);
}

.stageSyncGatePrompt {
  min-width: min(220px, 100%);
  min-height: 52px;
  padding: 12px 20px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 18%, var(--c-border));
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 86%, white);
  box-shadow:
    0 18px 42px rgb(20 31 45 / 0.12),
    inset 0 1px 0 rgb(255 255 255 / 0.5);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

:global([data-theme="dark"]) .stageSyncGatePrompt {
  border-color: rgb(255 255 255 / 0.2);
  background: rgb(255 255 255 / 0.1);
  box-shadow:
    0 18px 42px rgb(0 0 0 / 0.3),
    inset 0 1px 0 rgb(255 255 255 / 0.1);
  backdrop-filter: blur(12px);
}

.stageSyncGateTitle {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0;
}

.theaterDivider {
  height: 100%;
  display: grid;
  place-items: center;
  cursor: col-resize;
  touch-action: none;
}

.dividerHandle {
  width: 3px;
  height: 78px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-text-muted) 62%, var(--c-border));
  transition:
    background-color 160ms ease,
    box-shadow 180ms ease,
    height 180ms ease;
}

:global([data-theme="dark"]) .dividerHandle {
  background: rgb(255 255 255 / 0.18);
}

.theaterDivider:hover .dividerHandle,
.theaterDivider.resizing .dividerHandle {
  height: 112px;
  background: color-mix(in srgb, var(--c-primary) 62%, white);
  box-shadow: 0 0 0 4px rgb(255 255 255 / 0.08);
}

.workspaceCard {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 0;
  height: 100%;
  overflow: hidden;
  max-height: 100%;
}

.workspaceCard.theaterWorkspaceCard {
  grid-template-rows: minmax(0, 1fr);
  height: 100%;
  max-height: 100%;
  border-radius: 16px;
  border-color: rgb(255 255 255 / 0.12);
  background: color-mix(in srgb, var(--c-surface) 94%, var(--c-bg));
  box-shadow: 0 20px 46px rgb(0 0 0 / 0.22);
}

:global([data-theme="dark"]) .workspaceCard.theaterWorkspaceCard {
  background: color-mix(in srgb, var(--c-surface) 92%, rgb(18 24 34));
}

:deep(.workspaceCard.card) {
  padding: 0;
}

@media (max-width: 720px) {
  :deep(.page) {
    height: calc(100dvh - 56px);
    padding: 8px;
    overflow: hidden;
    box-sizing: border-box;
  }

  :deep(.container) {
    height: 100%;
  }

  .roomShell {
    height: 100%;
    overflow: hidden;
  }

  .mainGrid {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(0, 1fr);
    height: 100%;
    min-height: 0;
  }

  .workspaceCard {
    min-height: 0;
  }

  .workspaceColumn {
    min-height: 0;
    overflow: hidden;
  }
}

@media (max-width: 800px) {
  .topStrip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
}

@media (max-width: 640px) {
  .topStrip,
  .stageCard {
    padding: 12px;
  }

  .roomName {
    font-size: 20px;
  }

  .topStrip {
    gap: 8px;
  }

  .statusBar {
    margin-top: 0;
    flex-wrap: nowrap;
    justify-content: flex-end;
  }

  .statusBar :deep(.pill) {
    min-width: 0;
  }
}

:global(body.icinema-room-theater-active .app > .header) {
  display: none;
}

:global(body.icinema-room-theater-active .app > .body) {
  grid-template-columns: 1fr;
  min-height: 100dvh;
}

:global(body.icinema-room-theater-active .app > .body > .sidebar) {
  display: none;
}

:global(body.icinema-room-theater-active .app > .body > .content) {
  z-index: 90;
}
</style>
