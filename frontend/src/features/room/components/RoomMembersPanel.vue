<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import {
  ArrowRightStartOnRectangleIcon,
  MagnifyingGlassIcon,
  UserIcon,
  TrashIcon,
  UserPlusIcon,
} from "@heroicons/vue/24/outline";
import { useI18n } from "vue-i18n";
import RoomMemberAvatar from "@/features/room/components/RoomMemberAvatar.vue";
import { getUsers, type UserResponse } from "@/infra/api/users.api";
import { resolveMediaUrl } from "@/infra/media";
import type { MemberStatus, RoomRole } from "@/features/room/types";

type RoomMemberPanelItem = {
  id: number;
  name: string;
  email?: string | null;
  avatarUrl?: string | null;
  role: RoomRole;
  status: MemberStatus;
};

type PendingJoinRequestState = {
  userId: number;
  source: "apply" | "invite" | "member_invite";
};

const props = defineProps<{
  members: RoomMemberPanelItem[];
  searchPlaceholder: string;
  inviteLabel: string;
  leaveRoomLabel: string;
  disbandRoomLabel: string;
  isOwner?: boolean;
  canRemoveMembers?: boolean;
  actionDisabled?: boolean;
  leaving?: boolean;
  disbanding?: boolean;
  pendingJoinRequests?: PendingJoinRequestState[];
  settingManagerUserIds?: number[];
  removingMemberUserIds?: number[];
  loading?: boolean;
  loadingLabel?: string;
  emptyLabel?: string;
}>();

const emit = defineEmits<{
  inviteUser: [user: UserResponse];
  leaveRoom: [];
  disbandRoom: [];
  setManager: [userId: number];
  unsetManager: [userId: number];
  removeMember: [userId: number];
}>();

const { t } = useI18n();
const memberKeyword = ref("");
const inviteDialogOpen = ref(false);
const inviteKeyword = ref("");
const inviteResults = ref<UserResponse[]>([]);
const inviteLoading = ref(false);
const inviteError = ref("");
const hasSearchedInviteUsers = ref(false);
const leaveConfirmOpen = ref(false);
const disbandConfirmOpen = ref(false);
const selectedMember = ref<RoomMemberPanelItem | null>(null);
const removeMemberConfirmOpen = ref(false);
const disbandCountdown = ref(5);
let disbandCountdownTimer = 0;

const filteredMembers = computed(() => {
  const keyword = memberKeyword.value.trim().toLowerCase();
  if (!keyword) return props.members;

  return props.members.filter((member) =>
    member.name.toLowerCase().includes(keyword),
  );
});

const currentMemberIds = computed(() => new Set(props.members.map((member) => member.id)));
const filteredInviteResults = computed(() => inviteResults.value);
const dangerActionLabel = computed(() =>
  props.isOwner ? props.disbandRoomLabel : props.leaveRoomLabel);
const dangerActionIcon = computed(() =>
  props.isOwner ? TrashIcon : ArrowRightStartOnRectangleIcon);
const dangerActionLoading = computed(() =>
  props.isOwner ? props.disbanding : props.leaving);
const dangerActionDisabled = computed(() =>
  props.actionDisabled || dangerActionLoading.value);
const disbandConfirmDisabled = computed(() =>
  props.disbanding || disbandCountdown.value > 0);
const disbandConfirmText = computed(() =>
  disbandCountdown.value > 0
    ? t("room.members.disbandConfirmWait", { seconds: disbandCountdown.value })
    : props.disbandRoomLabel);
const selectedMemberIsOwner = computed(() => selectedMember.value?.role === "owner");
const selectedMemberIsManager = computed(() => selectedMember.value?.role === "manager");
const showSetSelectedMemberManager = computed(() =>
  !!selectedMember.value &&
  props.isOwner &&
  !selectedMemberIsOwner.value);
const canSetSelectedMemberManager = computed(() =>
  showSetSelectedMemberManager.value &&
  !selectedMemberIsManager.value);
const canRemoveSelectedMember = computed(() =>
  !!selectedMember.value &&
  props.canRemoveMembers &&
  (props.isOwner || selectedMember.value.role !== "manager") &&
  !selectedMemberIsOwner.value);
const showProfileActions = computed(() =>
  showSetSelectedMemberManager.value || canRemoveSelectedMember.value);
const selectedMemberSettingManager = computed(() =>
  !!selectedMember.value &&
  !!props.settingManagerUserIds?.includes(selectedMember.value.id));
const selectedMemberRemoving = computed(() =>
  !!selectedMember.value &&
  !!props.removingMemberUserIds?.includes(selectedMember.value.id));
const profileActionCount = computed(() =>
  Number(showSetSelectedMemberManager.value) + Number(canRemoveSelectedMember.value));

function userDisplayName(user: UserResponse) {
  return user.username || user.email || `User #${user.id}`;
}

function openMemberProfile(member: RoomMemberPanelItem) {
  selectedMember.value = member;
}

function closeMemberProfile() {
  selectedMember.value = null;
  removeMemberConfirmOpen.value = false;
}

function handleMemberProfileOpenChange(open: boolean) {
  if (!open) {
    closeMemberProfile();
  }
}

function openInviteDialog() {
  inviteDialogOpen.value = true;
}

function closeInviteDialog() {
  inviteDialogOpen.value = false;
  inviteError.value = "";
}

function pendingJoinRequestForUser(userId: number) {
  return props.pendingJoinRequests?.find((request) => request.userId === userId) ?? null;
}

function inviteActionLabel(user: UserResponse) {
  if (currentMemberIds.value.has(user.id)) {
    return t("room.members.alreadyInRoom");
  }

  const pendingRequest = pendingJoinRequestForUser(user.id);
  if (!pendingRequest) return props.inviteLabel;

  return pendingRequest.source === "apply"
    ? t("room.members.applyPending")
    : t("room.members.invitePending");
}

function inviteActionDisabled(user: UserResponse) {
  return currentMemberIds.value.has(user.id) || !!pendingJoinRequestForUser(user.id);
}

function handleInviteUser(user: UserResponse) {
  if (inviteActionDisabled(user)) return;
  emit("inviteUser", user);
}

function openRemoveMemberConfirm() {
  if (!canRemoveSelectedMember.value) return;
  removeMemberConfirmOpen.value = true;
}

function handleSetSelectedMemberManager() {
  if (!selectedMember.value || !canSetSelectedMemberManager.value) return;
  emit("setManager", selectedMember.value.id);
}

function handleUnsetSelectedMemberManager() {
  if (!selectedMember.value || !selectedMemberIsManager.value) return;
  emit("unsetManager", selectedMember.value.id);
}

function handleRemoveSelectedMember() {
  if (!selectedMember.value || !canRemoveSelectedMember.value) return;
  emit("removeMember", selectedMember.value.id);
}

async function searchInviteUsers() {
  const keyword = inviteKeyword.value.trim();
  if (!keyword) {
    inviteResults.value = [];
    inviteError.value = "";
    hasSearchedInviteUsers.value = false;
    return;
  }

  hasSearchedInviteUsers.value = true;
  inviteLoading.value = true;
  inviteError.value = "";

  try {
    const response = await getUsers({
      page: 1,
      page_size: 20,
      username: keyword,
      email: keyword,
    });
    inviteResults.value = response.items;
  } catch (error: any) {
    inviteError.value =
      error?.response?.data?.detail ||
      error?.message ||
      t("room.members.inviteSearchFailed");
  } finally {
    inviteLoading.value = false;
  }
}

function openDangerConfirm() {
  if (dangerActionDisabled.value) return;

  if (props.isOwner) {
    disbandConfirmOpen.value = true;
    return;
  }

  leaveConfirmOpen.value = true;
}

function confirmLeaveRoom() {
  emit("leaveRoom");
}

function confirmDisbandRoom() {
  emit("disbandRoom");
}

function clearDisbandCountdownTimer() {
  if (!disbandCountdownTimer) return;
  window.clearInterval(disbandCountdownTimer);
  disbandCountdownTimer = 0;
}

watch(disbandConfirmOpen, (open) => {
  clearDisbandCountdownTimer();

  if (!open) {
    disbandCountdown.value = 5;
    return;
  }

  disbandCountdown.value = 5;
  disbandCountdownTimer = window.setInterval(() => {
    disbandCountdown.value = Math.max(0, disbandCountdown.value - 1);
    if (disbandCountdown.value === 0) {
      clearDisbandCountdownTimer();
    }
  }, 1000);
});

watch(
  () => props.members,
  (members) => {
    if (!selectedMember.value) return;

    const updatedMember = members.find((member) => member.id === selectedMember.value?.id);
    if (!updatedMember) {
      closeMemberProfile();
      return;
    }

    selectedMember.value = updatedMember;
  },
);

onBeforeUnmount(() => {
  clearDisbandCountdownTimer();
});
</script>

<template>
  <div class="membersPanel">
    <BaseInput
      v-model="memberKeyword"
      :placeholder="searchPlaceholder"
    />

    <div class="membersScrollArea">
      <div v-if="loading" class="membersFeedback">
        {{ loadingLabel || "Loading…" }}
      </div>
      <div v-else-if="filteredMembers.length === 0" class="membersFeedback">
        {{ emptyLabel || "No members yet." }}
      </div>
      <div v-else class="memberList">
        <div
          v-for="member in filteredMembers"
          :key="member.id"
          class="memberItem"
        >
          <button
            class="memberAvatarButton"
            type="button"
            :aria-label="t('room.members.viewProfile', { user: member.name })"
            @click="openMemberProfile(member)"
          >
            <RoomMemberAvatar
              :name="member.name"
              :src="member.avatarUrl"
              :role="member.role"
              :status="member.status"
            />
          </button>
          <div class="memberMeta">
            <div class="memberName">{{ member.name }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="membersFooter">
      <BaseButton variant="primary" @click="openInviteDialog">
        <span class="buttonContent">
          <AppIcon :icon="UserPlusIcon" :size="17" />
          <span>{{ inviteLabel }}</span>
        </span>
      </BaseButton>
      <BaseButton
        variant="danger"
        :disabled="dangerActionDisabled"
        :loading="dangerActionLoading"
        @click="openDangerConfirm"
      >
        <span class="buttonContent">
          <AppIcon :icon="dangerActionIcon" :size="17" />
          <span>{{ dangerActionLabel }}</span>
        </span>
      </BaseButton>
    </div>

    <BaseDialog
      v-model="inviteDialogOpen"
      :aria-label="t('room.members.inviteDialogTitle')"
      :max-width="520"
      @close="closeInviteDialog"
    >
      <BaseCard class="inviteDialogCard">
        <form class="inviteSearchBar" @submit.prevent="searchInviteUsers">
          <input
            v-model="inviteKeyword"
            class="inviteSearchInput"
            :aria-label="t('room.members.inviteSearchLabel')"
            :placeholder="t('room.members.inviteSearchPlaceholder')"
            :disabled="inviteLoading"
            autocomplete="off"
          >
          <BaseIconButton
            class="inviteSearchButton"
            type="submit"
            :aria-label="t('room.members.searchUsers')"
            :disabled="inviteLoading"
          >
            <AppIcon :icon="MagnifyingGlassIcon" :size="17" />
          </BaseIconButton>
        </form>

        <div v-if="inviteError" class="inviteState error">{{ inviteError }}</div>
        <div v-else-if="inviteLoading" class="inviteState">
          {{ t("common.loading") }}
        </div>
        <div v-else-if="hasSearchedInviteUsers && filteredInviteResults.length === 0" class="inviteState">
          {{ t("room.members.inviteSearchEmpty") }}
        </div>
        <div v-else class="inviteResults">
          <div
            v-for="user in filteredInviteResults"
            :key="user.id"
            class="inviteUserItem"
          >
            <RoomMemberAvatar
              :size="32"
              :src="resolveMediaUrl(user.avatar_url)"
              :name="userDisplayName(user)"
              role="member"
              status="idle"
            />
            <div class="inviteUserMeta">
              <div class="inviteUserName">{{ userDisplayName(user) }}</div>
              <div class="inviteUserEmail">{{ user.email }}</div>
            </div>
            <BaseButton
              class="inviteUserAction"
              :variant="inviteActionDisabled(user) ? 'default' : 'primary'"
              :disabled="inviteActionDisabled(user)"
              @click="handleInviteUser(user)"
            >
              {{ inviteActionLabel(user) }}
            </BaseButton>
          </div>
        </div>
      </BaseCard>
    </BaseDialog>

    <BaseDialog
      :model-value="!!selectedMember"
      :aria-label="selectedMember ? t('room.members.profileDialogTitle', { user: selectedMember.name }) : t('room.members.profileDialogFallbackTitle')"
      :max-width="328"
      @update:model-value="handleMemberProfileOpenChange"
      @close="closeMemberProfile"
    >
      <BaseCard v-if="selectedMember" class="memberProfileCard">
        <div class="memberProfileTitle">{{ t("room.members.profileTitle") }}</div>
        <div class="memberProfileAvatar" aria-hidden="true">
          <img
            v-if="selectedMember.avatarUrl"
            class="memberProfileAvatarImage"
            :src="selectedMember.avatarUrl"
            :alt="selectedMember.name"
          >
          <AppIcon
            v-else
            class="memberProfileAvatarFallback"
            :icon="UserIcon"
            :size="54"
          />
        </div>
        <div class="memberProfileText">
          <div class="memberProfileName">{{ selectedMember.name }}</div>
          <div class="memberProfileEmail">
            {{ selectedMember.email || t("room.members.profileNoEmail") }}
          </div>
        </div>
        <div
          v-if="showProfileActions"
          class="memberProfileActions"
          :class="{ single: profileActionCount === 1 }"
        >
          <BaseButton
            v-if="showSetSelectedMemberManager"
            class="managerActionButton"
            variant="primary"
            :loading="selectedMemberSettingManager"
            :disabled="selectedMemberRemoving"
            @click="selectedMemberIsManager ? handleUnsetSelectedMemberManager() : handleSetSelectedMemberManager()"
          >
            <span class="managerActionLabelWrap">
              <Transition name="memberActionLabel">
                <span
                  :key="selectedMemberIsManager ? 'unset' : 'set'"
                  class="managerActionLabelText"
                >
                  {{ selectedMemberIsManager ? t("room.members.unsetManager") : t("room.members.setManager") }}
                </span>
              </Transition>
            </span>
          </BaseButton>
          <BaseButton
            v-if="canRemoveSelectedMember"
            variant="danger"
            :loading="selectedMemberRemoving"
            :disabled="selectedMemberSettingManager"
            @click="openRemoveMemberConfirm"
          >
            {{ t("room.members.removeFromRoom") }}
          </BaseButton>
        </div>
      </BaseCard>
    </BaseDialog>

    <BaseConfirmDialog
      v-model="removeMemberConfirmOpen"
      :title="t('room.members.removeConfirmTitle')"
      :message="selectedMember ? t('room.members.removeConfirmMessage', { user: selectedMember.name }) : ''"
      :confirm-text="t('room.members.removeFromRoom')"
      :cancel-text="t('common.cancel')"
      variant="danger"
      :loading="selectedMemberRemoving"
      @confirm="handleRemoveSelectedMember"
    />

    <BaseConfirmDialog
      v-model="leaveConfirmOpen"
      :title="t('room.members.leaveConfirmTitle')"
      :message="t('room.members.leaveConfirmMessage')"
      :confirm-text="leaveRoomLabel"
      :cancel-text="t('common.cancel')"
      variant="danger"
      :loading="leaving"
      @confirm="confirmLeaveRoom"
    />

    <BaseConfirmDialog
      v-model="disbandConfirmOpen"
      :title="t('room.members.disbandConfirmTitle')"
      :message="t('room.members.disbandConfirmMessage')"
      :confirm-text="disbandConfirmText"
      :cancel-text="t('common.cancel')"
      variant="danger"
      :loading="disbanding"
      :confirm-disabled="disbandConfirmDisabled"
      @confirm="confirmDisbandRoom"
    />
  </div>
</template>

<style scoped>
.membersPanel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 14px;
  height: 100%;
  min-height: 0;
  align-self: stretch;
}

.membersScrollArea {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  padding-top: 2px;
  padding-bottom: 4px;
  padding-left: 6px;
  padding-right: 6px;
  margin-left: -14px;
  margin-right: -14px;
}

.memberList {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.membersFeedback {
  min-height: 100%;
  display: grid;
  place-items: center;
  color: var(--c-text-muted);
  font-size: 13px;
  text-align: center;
  padding: 18px;
}

.memberItem {
  padding: 6px 2px 4px;
  display: grid;
  justify-items: center;
  align-content: start;
  gap: 6px;
}

.memberAvatarButton {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  border-radius: 999px;
  display: inline-grid;
  place-items: center;
}

.memberAvatarButton:hover {
  background: color-mix(in srgb, var(--c-hover) 80%, transparent);
}

.memberAvatarButton:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--c-primary) 60%, transparent);
  outline-offset: 3px;
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

.membersFooter {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding-top: 2px;
}

.membersFooter :deep(button) {
  width: 100%;
  justify-content: center;
}

.buttonContent {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 0;
}

.inviteDialogCard {
  padding: 12px;
  display: grid;
  gap: 12px;
}

.inviteSearchBar {
  min-height: 46px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 0 6px 0 14px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 86%, var(--c-bg));
}

.inviteSearchInput {
  width: 100%;
  min-width: 0;
  height: 42px;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--c-text);
  font: inherit;
  font-size: 14px;
}

.inviteSearchButton {
  width: 34px;
  height: 34px;
}

.inviteState {
  min-height: 56px;
  display: grid;
  place-items: center;
  color: var(--c-text-muted);
  font-size: 13px;
  text-align: center;
}

.inviteState.error {
  color: var(--c-danger);
}

.inviteResults {
  display: grid;
  gap: 8px;
  max-height: min(320px, 48dvh);
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.inviteUserItem {
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--c-border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--c-surface) 78%, var(--c-bg));
}

.inviteUserMeta {
  flex: 1;
  min-width: 0;
}

.inviteUserAction {
  flex: 0 0 auto;
}

.inviteUserName {
  font-size: 13px;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inviteUserEmail {
  margin-top: 3px;
  font-size: 12px;
  color: var(--c-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.memberProfileCard {
  padding: 20px;
  display: grid;
  justify-items: center;
  gap: 14px;
}

.memberProfileTitle {
  justify-self: center;
  color: var(--c-text);
  font-size: 16px;
  font-weight: 650;
}

.memberProfileAvatar {
  width: 152px;
  height: 152px;
  border-radius: 24px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--c-border) 78%, white);
  background:
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--c-surface) 88%, white),
      color-mix(in srgb, var(--c-bg) 82%, var(--c-surface))
    );
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.32),
    0 18px 42px rgb(0 0 0 / 0.12);
}

.memberProfileAvatarImage {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.memberProfileAvatarFallback {
  color: var(--c-text-muted);
}

.memberProfileText {
  min-width: 0;
  width: 100%;
  display: grid;
  gap: 6px;
  text-align: center;
}

.memberProfileName {
  min-width: 0;
  color: var(--c-text);
  font-size: 20px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.memberProfileEmail {
  min-width: 0;
  color: var(--c-text-muted);
  font-size: 13px;
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.memberProfileActions {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 4px;
}

.memberProfileActions.single {
  grid-template-columns: minmax(128px, 176px);
  justify-content: center;
}

.memberProfileActions :deep(button) {
  width: 100%;
  justify-content: center;
}

.managerActionLabelWrap {
  min-width: 6em;
  display: inline-grid;
  place-items: center;
  position: relative;
}

.managerActionLabelText {
  grid-area: 1 / 1;
}

.memberActionLabel-enter-active,
.memberActionLabel-leave-active {
  transition: opacity 160ms ease, transform 160ms ease;
}

.memberActionLabel-leave-active {
  position: absolute;
}

.memberActionLabel-enter-from {
  opacity: 0;
  transform: translateY(3px);
}

.memberActionLabel-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}

@media (max-width: 800px) {
  .membersFooter {
    grid-template-columns: 1fr;
  }

  .inviteSearchBar {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .inviteUserItem {
    align-items: stretch;
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
  }

  .inviteUserAction {
    grid-column: 1 / -1;
    width: 100%;
  }
}

</style>
