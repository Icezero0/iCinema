<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, type Component, type Ref } from "vue";
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
  getRoomJoinRequests,
  deleteRoom,
  leaveRoom,
  removeRoomMember,
  setRoomMemberManager,
  unsetRoomMemberManager,
  type Room,
  type RoomJoinRequest,
  type RoomVideoSourceType,
} from "@/infra/api/rooms.api";
import {
  approveJoinRequestById,
  rejectJoinRequestById,
} from "@/infra/api/join-requests.api";
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
import { useMessagesStore } from "@/stores/messages.store";
import {
  DEFAULT_LOCAL_ROOM_VOLUME,
  useEntitiesStore,
} from "@/stores/entities.store";
import { useAuthStore } from "@/stores/auth.store";
import { useToastsStore } from "@/stores/toasts.store";
import { resolveMediaUrl } from "@/infra/media";
import { formatLocalDateTime } from "@/utils/datetime";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const entitiesStore = useEntitiesStore();
const messagesStore = useMessagesStore();
const toasts = useToastsStore();

type RoomRoleState = RoomRole | "unknown";

const room = ref<Room | null>(null);
const isLoading = ref(false);
const error = ref("");
const membersLoading = ref(false);
const membersError = ref("");
const requestsLoading = ref(false);
const requestsError = ref("");
const requestsLoaded = ref(false);
const roomJoinRequests = ref<RoomJoinRequest[]>([]);
const requestActionIds = ref<number[]>([]);
const isLeavingRoom = ref(false);
const isDisbandingRoom = ref(false);
const settingManagerUserIds = ref<number[]>([]);
const removingMemberUserIds = ref<number[]>([]);
const mainGridRef = ref<HTMLElement | null>(null);
const playerStageRef = ref<{
  togglePlayback: () => Promise<void>;
  pauseVideo: () => void;
  seekToPercent: (percent: number) => void;
  captureCurrentFrame: () => Promise<Blob>;
} | null>(null);

const roomId = computed(() => {
  const raw = route.params.id;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
});

const currentUserRole = ref<RoomRoleState>("unknown");
const activePanel = ref<RoomPanelKey>("chat");
const panelBeforeTheater = ref<RoomPanelKey>("chat");
const playbackIsPlaying = ref(false);
const playbackProgress = ref(0);
const playbackBufferedProgress = ref(0);
const playbackBufferedRanges = ref<Array<{ startPercent: number; endPercent: number }>>([]);
const playbackVolume = ref(DEFAULT_LOCAL_ROOM_VOLUME);
const playbackCurrentTime = ref(0);
const playbackDuration = ref(0);
const playbackSourceType = ref<RoomVideoSourceType>("external_url");
const playbackSourceUrl = ref("");
const playbackSourceFile = ref<File | null>(null);
const playbackSourceFileName = ref("");
const playbackSourceRevision = ref(0);
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
const roomRequestItems = computed(() => roomJoinRequests.value.map((request) => {
  const isApply = request.source === "apply";
  const user = isApply ? request.initiator : request.target;

  return {
    id: request.id,
    user:
      user?.username ||
      user?.email ||
      `User #${isApply ? request.initiator_user_id : request.target_user_id}`,
    note: isApply
      ? t("room.requests.applyNote")
      : t("room.requests.inviteNote"),
    time: formatLocalDateTime(request.updated_at || request.created_at),
  };
}));
const pendingMemberInviteStates = computed(() => roomJoinRequests.value
  .filter((request) => request.status === "pending")
  .map((request) => ({
    userId:
      request.source === "apply"
        ? request.initiator_user_id
        : request.target_user_id,
    source: request.source,
  })));
const roomMemberItems = computed(() => entityRoomMembers.value.map((member) => {
  const user = entitiesStore.getUser(member.user_id);

  return {
    id: member.user_id,
    name:
      user?.username ||
      user?.email ||
      `User #${member.user_id}`,
    email: user?.email ?? null,
    avatarUrl: resolveMediaUrl(user?.avatar_url),
    role: member.role,
    status: "idle" as const,
  };
}));
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
const playbackTimelineLabel = computed(() =>
  `${formatPlaybackTime(playbackCurrentTime.value)} / ${formatPlaybackTime(playbackDuration.value)}`);

function formatPlaybackTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "00:00";

  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const restSeconds = totalSeconds % 60;
  const mm = String(minutes).padStart(2, "0");
  const ss = String(restSeconds).padStart(2, "0");

  if (hours <= 0) return `${mm}:${ss}`;
  return `${hours}:${mm}:${ss}`;
}

function updatePlaybackProgress() {
  playbackProgress.value =
    playbackDuration.value > 0
      ? Math.min(100, Math.max(0, (playbackCurrentTime.value / playbackDuration.value) * 100))
      : 0;
}

function togglePlayback() {
  void playerStageRef.value?.togglePlayback();
}

function handlePlaybackProgressChange(value: number) {
  playerStageRef.value?.pauseVideo();
  playbackIsPlaying.value = false;
  playbackProgress.value = value;
  playerStageRef.value?.seekToPercent(value);
}

function handlePlaybackDurationChange(value: number) {
  playbackDuration.value = value;
  updatePlaybackProgress();
}

function handlePlaybackTimeChange(value: number) {
  playbackCurrentTime.value = value;
  updatePlaybackProgress();
}

function handleApplyPlaybackSource(payload: {
  sourceType: RoomVideoSourceType;
  externalUrl: string;
  localFile: File | null;
}) {
  playbackSourceType.value = payload.sourceType;

  if (payload.sourceType === "external_url") {
    playbackSourceUrl.value = payload.externalUrl.trim();
    playbackSourceFile.value = null;
    playbackSourceFileName.value = "";
  } else if (payload.localFile) {
    playbackSourceFile.value = payload.localFile;
    playbackSourceFileName.value = payload.localFile.name;
    playbackSourceUrl.value = "";
    playbackBufferedProgress.value = 0;
    playbackBufferedRanges.value = [];
  }

  playbackCurrentTime.value = 0;
  playbackDuration.value = 0;
  playbackProgress.value = 0;
  playbackBufferedProgress.value = 0;
  playbackBufferedRanges.value = [];
  playbackIsPlaying.value = false;
  playbackSourceRevision.value += 1;
}

async function handleCopyPlayerScreenshot() {
  try {
    const blob = await playerStageRef.value?.captureCurrentFrame();
    if (!blob) {
      throw new Error(t("room.playback.screenshotNoFrame"));
    }

    if (!navigator.clipboard?.write || typeof ClipboardItem === "undefined") {
      throw new Error(t("room.playback.screenshotClipboardUnsupported"));
    }

    await navigator.clipboard.write([
      new ClipboardItem({ [blob.type]: blob }),
    ]);
    toasts.push({
      message: t("room.playback.screenshotCopied"),
      tone: "success",
    });
  } catch (error) {
    toasts.push({
      message:
        error instanceof Error && error.message
          ? error.message
          : t("room.playback.screenshotFailed"),
      tone: "danger",
    });
  }
}

function loadLocalPlaybackVolume() {
  playbackVolume.value = entitiesStore.loadRoomLocalVolume(roomId.value);
}

function handlePlaybackVolumeChange(value: number) {
  playbackVolume.value = entitiesStore.setRoomLocalVolume(roomId.value, value);
}

function resetPlaybackState() {
  playbackIsPlaying.value = false;
  playbackProgress.value = 0;
  playbackBufferedProgress.value = 0;
  playbackBufferedRanges.value = [];
  playbackCurrentTime.value = 0;
  playbackDuration.value = 0;
  playbackSourceType.value = "external_url";
  playbackSourceUrl.value = "";
  playbackSourceFile.value = null;
  playbackSourceFileName.value = "";
  playbackSourceRevision.value += 1;
}

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

async function fetchRoomRequests(options?: { force?: boolean }) {
  if (!roomId.value || !canManageRoomRequests.value) {
    roomJoinRequests.value = [];
    requestsLoaded.value = false;
    requestsError.value = "";
    return;
  }

  if (requestsLoading.value) return;
  if (!options?.force && requestsLoaded.value) return;

  requestsLoading.value = true;
  requestsError.value = "";

  try {
    const response = await getRoomJoinRequests(roomId.value, {
      page: 1,
      page_size: 30,
      status: "pending",
    });
    roomJoinRequests.value = response.items;
    entitiesStore.upsertJoinRequests(response.items);
    requestsLoaded.value = true;
  } catch (e: any) {
    requestsError.value =
      e?.response?.data?.detail ||
      e?.message ||
      t("room.requestsLoadFailed");
  } finally {
    requestsLoading.value = false;
  }
}

function isRequestActionLoading(requestId: number) {
  return requestActionIds.value.includes(requestId);
}

function setRequestActionLoading(requestId: number, loading: boolean) {
  requestActionIds.value = loading
    ? [...new Set([...requestActionIds.value, requestId])]
    : requestActionIds.value.filter((id) => id !== requestId);
}

async function approveRequest(requestId: number) {
  setRequestActionLoading(requestId, true);
  requestsError.value = "";

  try {
    await approveJoinRequestById(requestId);
    await fetchRoomRequests({ force: true });
  } catch (e: any) {
    requestsError.value =
      e?.response?.data?.detail ||
      e?.message ||
      t("room.requestsLoadFailed");
  } finally {
    setRequestActionLoading(requestId, false);
  }
}

async function rejectRequest(requestId: number) {
  setRequestActionLoading(requestId, true);
  requestsError.value = "";

  try {
    await rejectJoinRequestById(requestId);
    await fetchRoomRequests({ force: true });
  } catch (e: any) {
    requestsError.value =
      e?.response?.data?.detail ||
      e?.message ||
      t("room.requestsLoadFailed");
  } finally {
    setRequestActionLoading(requestId, false);
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

async function handleLeaveRoom() {
  if (!roomId.value || isLeavingRoom.value) return;

  isLeavingRoom.value = true;

  try {
    await leaveRoom(roomId.value);
    toasts.push({
      message: t("room.members.leaveSuccess"),
      tone: "success",
    });
    await router.push("/");
  } catch (e: any) {
    toasts.push({
      message:
        e?.response?.data?.detail ||
        e?.message ||
        t("room.members.leaveFailed"),
      tone: "danger",
    });
  } finally {
    isLeavingRoom.value = false;
  }
}

async function handleDisbandRoom() {
  if (!roomId.value || isDisbandingRoom.value) return;

  isDisbandingRoom.value = true;

  try {
    await deleteRoom(roomId.value);
    toasts.push({
      message: t("room.members.disbandSuccess"),
      tone: "success",
    });
    await router.push("/");
  } catch (e: any) {
    toasts.push({
      message:
        e?.response?.data?.detail ||
        e?.message ||
        t("room.members.disbandFailed"),
      tone: "danger",
    });
  } finally {
    isDisbandingRoom.value = false;
  }
}

function setMemberActionLoading(actionIds: Ref<number[]>, userId: number, loading: boolean) {
  actionIds.value = loading
    ? [...new Set([...actionIds.value, userId])]
    : actionIds.value.filter((id) => id !== userId);
}

async function handleSetMemberManager(userId: number) {
  if (!roomId.value || settingManagerUserIds.value.includes(userId)) return;

  setMemberActionLoading(settingManagerUserIds, userId, true);

  try {
    const member = await setRoomMemberManager(roomId.value, userId);
    entitiesStore.upsertRoomMember(member);
    syncCurrentUserRole();
    toasts.push({
      message: t("room.members.setManagerSuccess"),
      tone: "success",
    });
  } catch (e: any) {
    toasts.push({
      message:
        e?.response?.data?.detail ||
        e?.message ||
        t("room.members.setManagerFailed"),
      tone: "danger",
    });
  } finally {
    setMemberActionLoading(settingManagerUserIds, userId, false);
  }
}

async function handleUnsetMemberManager(userId: number) {
  if (!roomId.value || settingManagerUserIds.value.includes(userId)) return;

  setMemberActionLoading(settingManagerUserIds, userId, true);

  try {
    const member = await unsetRoomMemberManager(roomId.value, userId);
    entitiesStore.upsertRoomMember(member);
    syncCurrentUserRole();
    toasts.push({
      message: t("room.members.unsetManagerSuccess"),
      tone: "success",
    });
  } catch (e: any) {
    toasts.push({
      message:
        e?.response?.data?.detail ||
        e?.message ||
        t("room.members.unsetManagerFailed"),
      tone: "danger",
    });
  } finally {
    setMemberActionLoading(settingManagerUserIds, userId, false);
  }
}

async function handleRemoveRoomMember(userId: number) {
  if (!roomId.value || removingMemberUserIds.value.includes(userId)) return;

  setMemberActionLoading(removingMemberUserIds, userId, true);

  try {
    await removeRoomMember(roomId.value, userId);
    entitiesStore.removeRoomMember(roomId.value, userId);
    syncCurrentUserRole();
    toasts.push({
      message: t("room.members.removeSuccess"),
      tone: "success",
    });
  } catch (e: any) {
    toasts.push({
      message:
        e?.response?.data?.detail ||
        e?.message ||
        t("room.members.removeFailed"),
      tone: "danger",
    });
  } finally {
    setMemberActionLoading(removingMemberUserIds, userId, false);
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
  roomJoinRequests.value = [];
  requestsLoaded.value = false;
  requestsError.value = "";
  resetRoomSettingsState();
  requestActionIds.value = [];
  settingManagerUserIds.value = [];
  removingMemberUserIds.value = [];
  playbackVolume.value = DEFAULT_LOCAL_ROOM_VOLUME;
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
                @play-state-change="playbackIsPlaying = $event"
                @duration-change="handlePlaybackDurationChange"
                @time-change="handlePlaybackTimeChange"
                @buffered-progress-change="playbackBufferedProgress = $event"
                @buffered-ranges-change="playbackBufferedRanges = $event"
              />

              <RoomPlaybackControls
                class="playbackControls"
                :is-playing="playbackIsPlaying"
                :progress="playbackProgress"
                :buffered-progress="playbackBufferedProgress"
                :buffered-ranges="playbackBufferedRanges"
                :volume="playbackVolume"
                :source-type="playbackSourceType"
                :source-url="playbackSourceUrl"
                :source-file-name="playbackSourceFileName"
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
                :messages="roomChatMessages"
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
  padding: 16px;
  display: grid;
  gap: 14px;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--c-surface) 92%, white), color-mix(in srgb, var(--c-surface) 86%, var(--c-bg)));
}

.mainGrid.theaterMode .stageCard {
  height: 100%;
  min-height: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
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
