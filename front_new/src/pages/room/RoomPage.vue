<script setup lang="ts">
import { computed, onMounted, ref, watch, type Component } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  ChatBubbleLeftRightIcon,
  Cog6ToothIcon,
  UserGroupIcon,
  ClipboardDocumentCheckIcon,
} from "@heroicons/vue/24/outline";
import { getRoomById, type Room } from "@/infra/api/rooms.api";
import BasePill from "@/ui/base/BasePill.vue";
import AppTabs from "@/ui/layout/AppTabs.vue";
import RoomMemberAvatar from "@/features/room/components/RoomMemberAvatar.vue";
import ChatPanel from "@/features/chat/components/ChatPanel.vue";
import RoomPlaybackControls from "@/features/room/components/RoomPlaybackControls.vue";
import RoomRequestItem from "@/features/room/components/RoomRequestItem.vue";
import RoomSettingsPanel from "@/features/room/components/RoomSettingsPanel.vue";
import type { RoomPanelKey, RoomRequestMockItem, RoomRole } from "@/features/room/types";
import { createMockChatMessages, createMockMembers, createMockRequests } from "@/features/room/room.mock";
import { useRoomWorkspaceLayout } from "@/features/room/composables/useRoomWorkspaceLayout";

const { t } = useI18n();
const route = useRoute();

const room = ref<Room | null>(null);
const isLoading = ref(false);
const error = ref("");

const roomId = computed(() => {
  const raw = route.params.id;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
});

const currentUserRole = ref<RoomRole>("owner");
const activePanel = ref<RoomPanelKey>("chat");
const isPlaying = ref(false);
const mockProgress = ref(24);
const localSyncStrategy = ref("soft-lock");

const allPanelOptions = computed<{ key: RoomPanelKey; label: string; badge?: string; icon?: Component }[]>(() => [
  { key: "chat", label: t("room.mock.tabs.chat"), icon: ChatBubbleLeftRightIcon },
  { key: "members", label: t("room.mock.tabs.members"), icon: UserGroupIcon },
  { key: "requests", label: t("room.mock.tabs.requests"), badge: "3", icon: ClipboardDocumentCheckIcon },
  { key: "settings", label: t("room.mock.tabs.settings"), icon: Cog6ToothIcon },
]);

const panelOptions = computed(() => {
  if (currentUserRole.value === "member") {
    return allPanelOptions.value.filter((panel) => panel.key === "chat");
  }

  return allPanelOptions.value;
});

const localSyncOptions = computed(() => [
  { value: "soft-lock", label: t("room.mock.localSyncModes.softLock") },
  { value: "follow-host", label: t("room.mock.localSyncModes.followHost") },
  { value: "manual-first", label: t("room.mock.localSyncModes.manualFirst") },
]);

const mockMembers = computed(() => createMockMembers());
const mockRequests = computed<RoomRequestMockItem[]>(() => createMockRequests(t));
const mockChatMessages = computed(() => createMockChatMessages(t));
const layout = useRoomWorkspaceLayout({
  activePanel,
  roomId: computed(() => room.value?.id),
  isLoading,
});
const mainGridStyle = computed(() => layout.mainGridStyle.value);
const workspaceCardStyle = computed(() => layout.workspaceCardStyle.value);

function togglePlayback() {
  isPlaying.value = !isPlaying.value;
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

onMounted(fetchRoom);
watch(roomId, fetchRoom);
watch(panelOptions, (nextPanels) => {
  if (!nextPanels.some((panel) => panel.key === activePanel.value)) {
    activePanel.value = nextPanels[0]?.key ?? "chat";
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

              <Transition name="workspacePanel" mode="out-in">
                <div v-if="activePanel === 'chat'" key="chat" class="panelBody chatPanelBody">
                  <ChatPanel
                    class="chatPanelFill"
                    :messages="mockChatMessages"
                    :send-label="t('room.mock.send')"
                  />
                </div>

                <div
                  v-else-if="activePanel === 'members'"
                  key="members"
                  class="panelBody membersPanelBody"
                >
                  <div class="memberList">
                    <div
                      v-for="member in mockMembers"
                      :key="member.id"
                      class="memberItem"
                    >
                      <RoomMemberAvatar
                        :name="member.name"
                        :role="member.role"
                        :status="member.status"
                      />
                      <div class="memberMeta">
                        <div class="memberName">{{ member.name }}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div
                  v-else-if="activePanel === 'requests'"
                  key="requests"
                  class="panelBody"
                >
                  <div class="requestList">
                    <RoomRequestItem
                      v-for="request in mockRequests"
                      :key="request.id"
                      :user="request.user"
                      :time="request.time"
                      :note="request.note"
                      :approve-label="t('room.mock.approve')"
                      :reject-label="t('room.mock.reject')"
                    />
                  </div>
                </div>

                <div
                  v-else
                  key="settings"
                  class="panelBody"
                >
                  <RoomSettingsPanel
                    :room="room"
                    :room-name-label="t('room.mock.settingLabels.roomName')"
                    :visibility-label="t('room.mock.settingLabels.visibility')"
                    :sync-policy-label="t('room.mock.settingLabels.policy')"
                    :sync-policy-value="t('room.mock.syncPolicy')"
                    :sync-permission-label="t('room.mock.settingLabels.permission')"
                    :sync-permission-value="t('room.mock.syncPermission')"
                    :local-sync-title="t('room.mock.localSyncTitle')"
                    :local-sync-hint="t('room.mock.localSyncHint')"
                    :info-title="t('room.mock.settingGroups.info')"
                    :sync-title="t('room.mock.settingGroups.sync')"
                    :advanced-title="t('room.mock.settingGroups.advanced')"
                    :advanced-hint="t('room.mock.advancedHint')"
                    :public-label="t('room.fields.public')"
                    :private-label="t('room.fields.private')"
                    :local-sync-strategy="localSyncStrategy"
                    :local-sync-options="localSyncOptions"
                    @update:local-sync-strategy="localSyncStrategy = $event"
                  />
                </div>
              </Transition>
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

.chatPanelBody {
  grid-template-rows: minmax(0, 1fr);
  overflow: hidden;
}

.membersPanelBody {
  padding-left: 6px;
  padding-right: 6px;
}

:deep(.chatPanelFill) {
  height: 100%;
  min-height: 0;
}

.memberList,
.requestList {
  display: grid;
  gap: 10px;
}

.memberList {
  grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
  gap: 6px;
}

.memberItem {
  padding: 6px 2px 4px;
  display: grid;
  justify-items: center;
  align-content: start;
  gap: 6px;
}

.memberMeta {
  width: 100%;
  display: grid;
  justify-items: center;
}

.memberName {
  font-size: 13px;
  color: var(--c-text);
  max-width: 5em;
  margin: 0 auto;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspacePanel-enter-active,
.workspacePanel-leave-active {
  transition:
    opacity 180ms ease,
    transform 220ms ease;
}

.workspacePanel-enter-from,
.workspacePanel-leave-to {
  opacity: 0;
  transform: translateY(8px);
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

  .chatPanelBody {
    min-height: 0;
    height: 100%;
  }

  :deep(.chatPanelFill) {
    min-height: 100%;
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
