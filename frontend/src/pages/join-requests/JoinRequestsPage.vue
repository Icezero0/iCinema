<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  CheckCircleIcon,
  ChevronDownIcon,
  ClockIcon,
  XCircleIcon,
} from "@heroicons/vue/24/outline";
import {
  approveJoinRequestById,
  rejectJoinRequestById,
  listJoinRequests,
  type RoomJoinRequestListScope,
} from "@/infra/api/join-requests.api";
import type {
  RoomJoinRequestAction,
  RoomJoinRequest,
  RoomJoinRequestStatus,
} from "@/infra/api/rooms.api";
import { useAuthStore } from "@/stores/auth.store";
import { useRoomsStore } from "@/stores/rooms.store";
import { useEntitiesStore } from "@/stores/entities.store";
import { formatLocalDateTime } from "@/utils/datetime";
import { resolveMediaUrl } from "@/infra/media";

const { t } = useI18n();
const auth = useAuthStore();
const rooms = useRoomsStore();
const entities = useEntitiesStore();
const items = ref<RoomJoinRequest[]>([]);
const isLoading = ref(false);
const error = ref("");
const expandedIds = ref<number[]>([]);

const scope = ref<RoomJoinRequestListScope>("all_related_to_me");
const status = ref<RoomJoinRequestStatus | "all">("pending");

const scopeOptions = computed(() => [
  { value: "all_related_to_me", label: t("joinRequests.filters.allRelated") },
  { value: "created_by_me", label: t("joinRequests.filters.createdByMe") },
  { value: "handled_by_me", label: t("joinRequests.filters.pendingForMe") },
]);

const statusOptions = computed(() => [
  { value: "all", label: t("joinRequests.filters.allStatus") },
  { value: "pending", label: t("joinRequests.status.pending") },
  { value: "approved", label: t("joinRequests.status.approved") },
  { value: "rejected", label: t("joinRequests.status.rejected") },
  { value: "cancelled", label: t("joinRequests.status.cancelled") },
]);

const myRoomRoles = computed(() => {
  return new Map(
    rooms.myRooms.map((room) => [room.id, room.my_role ?? null] as const),
  );
});

async function fetchItems() {
  isLoading.value = true;
  error.value = "";

  try {
    const data = await listJoinRequests({
      page: 1,
      page_size: 30,
      scope: scope.value,
      status: status.value === "all" ? null : status.value,
    });

    items.value = data.items;
    entities.upsertJoinRequests(data.items);
  } catch (e: any) {
    error.value =
      e?.response?.data?.detail || e?.message || t("joinRequests.loadFailed");
  } finally {
    isLoading.value = false;
  }
}

async function approve(item: RoomJoinRequest) {
  await approveJoinRequestById(item.id);
  await fetchItems();
}

async function reject(item: RoomJoinRequest) {
  await rejectJoinRequestById(item.id);
  await fetchItems();
}

function isExpanded(id: number) {
  return expandedIds.value.includes(id);
}

function toggleExpanded(id: number) {
  expandedIds.value = isExpanded(id)
    ? expandedIds.value.filter((value) => value !== id)
    : [...expandedIds.value, id];
}

function currentUserCanHandleTargetSide(item: RoomJoinRequest) {
  return auth.me?.id === item.target_user_id && item.target_action === "pending";
}

function currentUserCanHandleRoomSide(item: RoomJoinRequest) {
  const role = myRoomRoles.value.get(item.room_id);
  return (role === "owner" || role === "manager") && item.room_action === "pending";
}

function canReview(item: RoomJoinRequest) {
  return (
    item.status === "pending" &&
    (currentUserCanHandleTargetSide(item) || currentUserCanHandleRoomSide(item))
  );
}

function roomName(item: RoomJoinRequest) {
  return item.room?.name || `#${item.room_id}`;
}

function userName(user: RoomJoinRequest["initiator"]) {
  return user?.username || user?.email || "-";
}

function userAvatarUrl(user: RoomJoinRequest["initiator"]) {
  return resolveMediaUrl(user?.avatar_url);
}

function joiningUser(item: RoomJoinRequest) {
  return item.source === "apply" ? item.initiator : item.target;
}

function requestTitle(item: RoomJoinRequest) {
  const room = roomName(item);

  if (item.source === "apply") {
    return t("joinRequests.item.applyTitle", {
      user: userName(item.initiator),
      room,
    });
  }

  return t("joinRequests.item.inviteTitle", {
    inviter: userName(item.initiator),
    invitee: userName(item.target),
    room,
  });
}

function actionIcon(action: RoomJoinRequestAction) {
  if (action === "approved") return CheckCircleIcon;
  if (action === "rejected") return XCircleIcon;
  return ClockIcon;
}

function actionTone(action: RoomJoinRequestAction) {
  if (action === "approved") return "success";
  if (action === "rejected") return "danger";
  return "pending";
}

function actionAvatarUrl(user: RoomJoinRequest["room_action_by"]) {
  return resolveMediaUrl(user?.avatar_url);
}

function overallTone(status: RoomJoinRequestStatus) {
  if (status === "approved") return "success";
  if (status === "rejected" || status === "cancelled") return "danger";
  return "pending";
}

function overallIcon(status: RoomJoinRequestStatus) {
  if (status === "approved") return CheckCircleIcon;
  if (status === "rejected" || status === "cancelled") return XCircleIcon;
  return ClockIcon;
}

async function bootstrap() {
  if (!rooms.isLoading && rooms.myRooms.length === 0) {
    await rooms.fetchHomeRooms();
  }
  await fetchItems();
}

onMounted(bootstrap);
watch([scope, status], fetchItems);
</script>

<template>
  <AppPageShell
    :title="t('joinRequests.title')"
    :back-text="t('common.backHome')"
    :max-width="980"
  >
    <template #toolbar>
      <BaseCard class="toolbarCard">
        <div class="filters">
          <BaseSelect
            v-model="scope"
            :options="scopeOptions"
            :label="t('joinRequests.filters.scope')"
            label-position="start"
            :width="176"
            max-width="32vw"
          />

          <BaseSelect
            v-model="status"
            :options="statusOptions"
            :label="t('joinRequests.filters.statusLabel')"
            label-position="start"
            :width="176"
            max-width="32vw"
          />
        </div>
      </BaseCard>
    </template>

    <BaseCard class="card">
      <div v-if="isLoading" class="state">{{ t("common.loading") }}</div>
      <div v-else-if="error" class="state error">{{ error }}</div>
      <div v-else-if="items.length === 0" class="empty">
        <div class="emptyTitle">{{ t("joinRequests.empty.title") }}</div>
        <div class="emptyHint">{{ t("joinRequests.empty.hint") }}</div>
      </div>

      <div v-else class="list">
        <RowListItem
          v-for="item in items"
          :key="item.id"
          class="requestItem"
          :data-status="item.status"
        >
          <div class="requestBody">
            <button
              class="summaryButton"
              type="button"
              :aria-expanded="isExpanded(item.id)"
              @mousedown.prevent
              @click="toggleExpanded(item.id)"
            >
              <div class="requestTop">
                <div class="requestTitle">
                  {{ requestTitle(item) }}
                </div>
                <div class="summaryRight">
                  <div class="summaryMeta">
                    <span class="summaryTime">
                      {{ formatLocalDateTime(item.updated_at || item.created_at) }}
                    </span>
                    <span class="overallBadge" :data-tone="overallTone(item.status)">
                      <AppIcon :icon="overallIcon(item.status)" :size="16" />
                      <span>{{ t(`joinRequests.status.${item.status}`) }}</span>
                    </span>
                  </div>
                  <AppIcon
                    class="chevron"
                    :class="{ expanded: isExpanded(item.id) }"
                    :icon="ChevronDownIcon"
                    :size="18"
                  />
                </div>
              </div>
            </button>

            <Transition name="detail">
              <div v-if="isExpanded(item.id)" class="detailPanel">
                <div class="statusGrid">
                  <div class="statusCard">
                    <div class="statusCardHeader">
                      <span class="statusCardTitle">{{ t("joinRequests.item.userSide") }}</span>
                      <span class="statusPill" :data-tone="actionTone(item.target_action)">
                        <AppIcon :icon="actionIcon(item.target_action)" :size="16" />
                        <span>{{ t(`joinRequests.status.${item.target_action}`) }}</span>
                      </span>
                    </div>

                    <div class="participantRow">
                      <BaseAvatar
                        size="xs"
                        :src="userAvatarUrl(joiningUser(item))"
                        :name="userName(joiningUser(item))"
                      />
                      <span class="participantName">{{ userName(joiningUser(item)) }}</span>
                    </div>
                  </div>

                  <div class="statusCard">
                    <div class="statusCardHeader">
                      <span class="statusCardTitle">{{ t("joinRequests.item.roomSide") }}</span>
                      <span class="statusPill" :data-tone="actionTone(item.room_action)">
                        <AppIcon :icon="actionIcon(item.room_action)" :size="16" />
                        <span>{{ t(`joinRequests.status.${item.room_action}`) }}</span>
                      </span>
                    </div>

                    <div v-if="item.room_action !== 'pending' && item.room_action_by" class="participantRow">
                      <span class="participantLabel">{{ t("joinRequests.item.handler") }}</span>
                      <BaseAvatar
                        size="xs"
                        :src="actionAvatarUrl(item.room_action_by)"
                        :name="userName(item.room_action_by)"
                      />
                      <span class="participantName">{{ userName(item.room_action_by) }}</span>
                    </div>
                    <div v-else class="participantPlaceholder">
                      {{ roomName(item) }}
                    </div>
                  </div>
                </div>

                <div class="detailFooter">
                  <div v-if="canReview(item)" class="actions">
                    <BaseButton variant="primary" @click.stop="approve(item)">
                      {{ t("joinRequests.actions.approve") }}
                    </BaseButton>
                    <BaseButton variant="danger" @click.stop="reject(item)">
                      {{ t("joinRequests.actions.reject") }}
                    </BaseButton>
                  </div>
                </div>
              </div>
            </Transition>
          </div>
        </RowListItem>
      </div>
    </BaseCard>
  </AppPageShell>
</template>

<style scoped>
.toolbarCard {
  padding: 14px 18px;
}

.card {
  padding: 22px;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}


.state {
  color: var(--c-text-muted);
}

.state.error {
  color: var(--c-danger);
}

.empty {
  padding: 18px 6px;
  color: var(--c-text-muted);
  text-align: center;
}

.emptyTitle {
  font-size: 14px;
  color: var(--c-text);
  margin-bottom: 6px;
}

.emptyHint {
  font-size: 12px;
  color: var(--c-text-muted);
}

.list {
  display: grid;
  gap: 10px;
}

.requestBody {
  min-width: 0;
}

.summaryButton {
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
}

.requestItem[data-status="approved"] {
  border-color: color-mix(in srgb, #3aa675 20%, var(--c-border));
}

.requestItem[data-status="rejected"],
.requestItem[data-status="cancelled"] {
  border-color: color-mix(in srgb, var(--c-danger) 20%, var(--c-border));
}

.requestTop {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.summaryRight {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}

.summaryMeta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.requestTitle {
  font-size: 14px;
  font-weight: 650;
  color: var(--c-text);
}

.summaryTime {
  font-size: 12px;
  color: var(--c-text-muted);
  white-space: nowrap;
}

.chevron {
  color: var(--c-text-muted);
  transition: transform 160ms ease;
}

.chevron.expanded {
  transform: rotate(180deg);
}

.overallBadge,
.statusPill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  user-select: none;
}

.overallBadge[data-tone="pending"],
.statusPill[data-tone="pending"] {
  background: color-mix(in srgb, var(--c-hover) 72%, var(--c-surface));
  color: var(--c-text-muted);
}

.overallBadge[data-tone="success"],
.statusPill[data-tone="success"] {
  background: color-mix(in srgb, #3aa675 16%, var(--c-surface));
  color: #267454;
}

.overallBadge[data-tone="danger"],
.statusPill[data-tone="danger"] {
  background: color-mix(in srgb, var(--c-danger) 14%, var(--c-surface));
  color: var(--c-danger);
}

.detailPanel {
  margin-top: 14px;
  display: grid;
  gap: 14px;
}

.statusGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.statusCard {
  padding: 14px;
  border: 1px solid var(--c-border);
  border-radius: 16px;
  background: color-mix(in srgb, var(--c-surface) 84%, white);
  display: grid;
  gap: 12px;
}

.statusCardHeader {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.statusCardTitle {
  font-size: 12px;
  font-weight: 650;
  color: var(--c-text-muted);
}

.participantRow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.participantName {
  font-size: 12px;
  color: var(--c-text-muted);
}

.participantLabel {
  font-size: 12px;
  color: var(--c-text-muted);
}

.participantPlaceholder {
  min-height: 28px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  color: var(--c-text-muted);
}

.detailFooter {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.actions {
  display: inline-flex;
  gap: 8px;
}

.detail-enter-active,
.detail-leave-active {
  transition: all 180ms ease;
}

.detail-enter-from,
.detail-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 800px) {
  .filters {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .card {
    padding: 16px;
  }

  .requestTop {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .summaryRight,
  .statusCardHeader,
  .detailFooter {
    width: 100%;
  }

  .summaryRight {
    justify-content: space-between;
    align-items: flex-start;
  }

  .summaryMeta {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .statusGrid {
    grid-template-columns: 1fr;
  }

  .statusCard {
    padding: 12px;
  }

  .participantRow {
    flex-wrap: wrap;
  }

  .actions {
    width: 100%;
    flex-direction: column;
  }

  .actions :deep(button) {
    width: 100%;
    justify-content: center;
  }

  .filters :deep(.selectRoot) {
    width: 100% !important;
    max-width: 100% !important;
  }
}

@media (max-width: 520px) {
  .card {
    padding: 8px;
  }

  .filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    margin-bottom: 14px;
  }

  .requestTitle {
    font-size: 13px;
    line-height: 1.45;
  }

  .summaryTime,
  .participantName,
  .participantLabel,
  .participantPlaceholder,
  .statusCardTitle {
    font-size: 11px;
  }

  .overallBadge,
  .statusPill {
    min-height: 24px;
    padding: 0 9px;
    font-size: 11px;
  }

  .detailPanel {
    margin-top: 12px;
    gap: 12px;
  }

  .statusGrid {
    gap: 10px;
  }

  .statusCard {
    padding: 10px;
    border-radius: 14px;
  }
}
</style>
