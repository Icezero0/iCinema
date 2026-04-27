<script setup lang="ts">
import { computed, onMounted, ref, watch, type Component, type Ref } from "vue";
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
} from "@/infra/api/rooms.api";
import {
  approveJoinRequestById,
  rejectJoinRequestById,
} from "@/infra/api/join-requests.api";
import BasePill from "@/ui/base/BasePill.vue";
import AppTabs from "@/ui/layout/AppTabs.vue";
import RoomPlaybackControls from "@/features/room/components/RoomPlaybackControls.vue";
import RoomChatTab from "@/features/room/components/workspace/RoomChatTab.vue";
import RoomMembersTab from "@/features/room/components/workspace/RoomMembersTab.vue";
import RoomRequestsTab from "@/features/room/components/workspace/RoomRequestsTab.vue";
import RoomSettingsTab from "@/features/room/components/workspace/RoomSettingsTab.vue";
import type { RoomPanelKey, RoomRole } from "@/features/room/types";
import type { ChatSegment } from "@/features/chat/types";
import { useRoomWorkspaceLayout } from "@/features/room/composables/useRoomWorkspaceLayout";
import { useRoomSettingsState } from "@/features/room/composables/useRoomSettingsState";
import { useMessagesStore } from "@/stores/messages.store";
import { useEntitiesStore } from "@/stores/entities.store";
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

const roomId = computed(() => {
  const raw = route.params.id;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
});

const currentUserRole = ref<RoomRoleState>("unknown");
const activePanel = ref<RoomPanelKey>("chat");
const isPlaying = ref(false);
const mockProgress = ref(24);
const canManageRoomRequests = computed(() =>
  currentUserRole.value === "owner" || currentUserRole.value === "manager");
const currentUserIsOwner = computed(() => currentUserRole.value === "owner");
const currentUserCanRemoveMembers = computed(() =>
  currentUserRole.value === "owner" || currentUserRole.value === "manager");
const memberDangerActionDisabled = computed(() => currentUserRole.value === "unknown");

const allPanelOptions = computed<{ key: RoomPanelKey; label: string; badge?: string; icon?: Component }[]>(() => [
  { key: "chat", label: t("room.mock.tabs.chat"), icon: ChatBubbleLeftRightIcon },
  { key: "members", label: t("room.mock.tabs.members"), icon: UserGroupIcon },
  {
    key: "requests",
    label: t("room.mock.tabs.requests"),
    badge: roomJoinRequests.value.length > 0 ? String(roomJoinRequests.value.length) : undefined,
    icon: ClipboardDocumentCheckIcon,
  },
  { key: "settings", label: t("room.mock.tabs.settings"), icon: Cog6ToothIcon },
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
      ? t("room.mock.requestApply")
      : t("room.mock.requestInvite"),
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
const mainGridStyle = computed(() => layout.mainGridStyle.value);
const workspaceCardStyle = computed(() => layout.workspaceCardStyle.value);
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

function togglePlayback() {
  isPlaying.value = !isPlaying.value;
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
  void fetchRoom();
  void fetchRoomMessages();
  void fetchRoomMembers();
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
</script>

<template>
  <BaseLayout :max-width="1320">
    <div class="roomShell">
      <div v-if="isLoading" class="state">{{ t("common.loading") }}</div>

      <div v-else-if="error" class="state error">{{ error }}</div>

      <template v-else-if="room">
        <BaseCard class="topStrip">
          <div class="roomIntro">
            <h2 class="roomName">{{ room.name }}</h2>
          </div>

          <div class="statusBar">
            <BasePill tone="default">{{ t("room.mock.syncPolicy") }}</BasePill>
          </div>
        </BaseCard>

        <div class="mainGrid" :style="mainGridStyle">
          <section
            :ref="(el) => { layout.setStageColumnEl(el as HTMLElement | null); }"
            class="stageColumn"
          >
            <BaseCard class="stageCard">
              <div class="playerShell" role="presentation">
                <div class="playerSurface">
                  <div class="playerOverlay">
                    <div class="screenLabel">{{ t("room.mock.playerLabel") }}</div>
                    <div class="screenHint">{{ t("room.mock.playerHint") }}</div>
                  </div>
                </div>
              </div>

              <RoomPlaybackControls
                :is-playing="isPlaying"
                :progress="mockProgress"
                timeline-label="01:24 / 13:42"
                :play-label="t('room.mock.controls.play')"
                :pause-label="t('room.mock.controls.pause')"
                :sync-label="t('room.mock.controls.syncNow')"
                :source-label="t('room.mock.controls.source')"
                :source-panel-title="t('room.mock.controls.sourcePanelTitle')"
                :volume-label="t('room.mock.controls.volume')"
                @toggle-play="togglePlayback"
                @update:progress="mockProgress = $event"
              />
            </BaseCard>
          </section>

          <aside
            :ref="(el) => { layout.setWorkspaceColumnEl(el as HTMLElement | null); }"
            class="workspaceColumn"
          >
            <BaseCard
              class="workspaceCard"
              :style="workspaceCardStyle"
            >
              <AppTabs v-model="activePanel" :items="panelOptions" />

              <RoomChatTab
                v-show="activePanel === 'chat'"
                :room-key="roomId"
                :messages="roomChatMessages"
                :send-label="t('room.mock.send')"
                :loading="roomMessagesState.isLoading"
                :sending="roomMessagesState.isSending"
                :loading-history="roomMessagesState.isLoadingHistory"
                :has-older="hasOlderMessages"
                :error="roomMessagesState.error"
                :loading-label="t('common.loading')"
                :empty-label="t('room.chatEmpty')"
                :send-message="handleSend"
                @load-older="loadOlderRoomMessages"
              />

              <RoomMembersTab
                v-show="activePanel === 'members'"
                :members="roomMemberItems"
                :search-placeholder="t('room.mock.membersSearchPlaceholder')"
                :invite-label="t('room.mock.invite')"
                :leave-room-label="t('room.mock.leaveRoom')"
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

.stageCard {
  padding: 16px;
  display: grid;
  gap: 14px;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--c-surface) 92%, white), color-mix(in srgb, var(--c-surface) 86%, var(--c-bg)));
}

.playerShell {
  width: 100%;
  border-radius: 22px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 16%, var(--c-border));
  background:
    linear-gradient(145deg, rgb(17 23 31), rgb(37 50 68)),
    radial-gradient(circle at top left, rgb(255 255 255 / 0.06), transparent 30%);
  box-shadow: 0 20px 60px rgb(0 0 0 / 0.18);
}

.playerSurface {
  width: 100%;
  aspect-ratio: 16 / 9;
  display: grid;
  place-items: center;
}

.playerOverlay {
  text-align: center;
  color: white;
}

.screenLabel {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.screenHint {
  margin-top: 8px;
  font-size: 13px;
  color: rgb(226 233 242 / 0.78);
}

.workspaceCard {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 0;
  height: 100%;
  overflow: hidden;
  max-height: 100%;
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
</style>
