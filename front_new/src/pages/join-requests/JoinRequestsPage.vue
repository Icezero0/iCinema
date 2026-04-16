<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  approveJoinRequestById,
  rejectJoinRequestById,
  listJoinRequests,
  type RoomJoinRequestListScope,
  type RoomJoinRequestSortBy,
} from "@/infra/api/join-requests.api";
import type {
  RoomJoinRequest,
  RoomJoinRequestStatus,
} from "@/infra/api/rooms.api";

const { t } = useI18n();

const items = ref<RoomJoinRequest[]>([]);
const isLoading = ref(false);
const error = ref("");

const scope = ref<RoomJoinRequestListScope>("all_related_to_me");
const sortBy = ref<RoomJoinRequestSortBy>("updated_at");
const status = ref<RoomJoinRequestStatus | "all">("pending");

const scopeOptions = computed(() => [
  { value: "all_related_to_me", label: t("joinRequests.filters.allRelated") },
  { value: "created_by_me", label: t("joinRequests.filters.createdByMe") },
  { value: "pending_for_me", label: t("joinRequests.filters.pendingForMe") },
]);

const statusOptions = computed(() => [
  { value: "all", label: t("joinRequests.filters.allStatus") },
  { value: "pending", label: t("joinRequests.status.pending") },
  { value: "approved", label: t("joinRequests.status.approved") },
  { value: "rejected", label: t("joinRequests.status.rejected") },
  { value: "cancelled", label: t("joinRequests.status.cancelled") },
]);

async function fetchItems() {
  isLoading.value = true;
  error.value = "";

  try {
    const data = await listJoinRequests({
      page: 1,
      page_size: 30,
      scope: scope.value,
      sort_by: sortBy.value,
      status: status.value === "all" ? null : status.value,
    });

    items.value = data.items;
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

function canReview(item: RoomJoinRequest) {
  return scope.value !== "created_by_me" && item.status === "pending";
}

function roomName(item: RoomJoinRequest) {
  return item.room?.name || `#${item.room_id}`;
}

function actorName(item: RoomJoinRequest) {
  return (
    item.initiator?.username ||
    item.initiator?.email ||
    item.target?.username ||
    item.target?.email ||
    "-"
  );
}

onMounted(fetchItems);
watch([scope, sortBy, status], fetchItems);
</script>

<template>
  <AppPageShell
    :title="t('joinRequests.title')"
    :back-text="t('common.backHome')"
    :max-width="980"
  >
    <BaseCard class="card">
      <div class="filters">
        <label class="field">
          <span class="label">{{ t("joinRequests.filters.scope") }}</span>
          <BaseSelect v-model="scope" :options="scopeOptions" />
        </label>

        <label class="field">
          <span class="label">{{ t("joinRequests.filters.statusLabel") }}</span>
          <BaseSelect v-model="status" :options="statusOptions" />
        </label>

        <label class="field">
          <span class="label">{{ t("joinRequests.filters.sortBy") }}</span>
          <BaseSelect
            v-model="sortBy"
            :options="[
              { value: 'updated_at', label: t('joinRequests.filters.updatedAt') },
              { value: 'created_at', label: t('joinRequests.filters.createdAt') },
            ]"
          />
        </label>
      </div>

      <div v-if="isLoading" class="state">{{ t("common.loading") }}</div>
      <div v-else-if="error" class="state error">{{ error }}</div>
      <div v-else-if="items.length === 0" class="state">{{ t("joinRequests.empty") }}</div>

      <div v-else class="list">
        <RowListItem v-for="item in items" :key="item.id">
          <div class="requestBody">
            <div class="requestTitle">
              {{ actorName(item) }} · {{ roomName(item) }}
            </div>
            <div class="requestMeta">
              <span>{{ t(`joinRequests.status.${item.status}`) }}</span>
              <span>{{ item.source }}</span>
              <span>{{ item.updated_at || item.created_at || "-" }}</span>
            </div>
          </div>

          <template #right>
            <div v-if="canReview(item)" class="actions">
              <BaseButton variant="primary" @click="approve(item)">
                {{ t("joinRequests.actions.approve") }}
              </BaseButton>
              <BaseButton variant="danger" @click="reject(item)">
                {{ t("joinRequests.actions.reject") }}
              </BaseButton>
            </div>
          </template>
        </RowListItem>
      </div>
    </BaseCard>
  </AppPageShell>
</template>

<style scoped>
.card {
  padding: 22px;
}

.filters {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.field {
  display: grid;
  gap: 8px;
}

.label {
  font-size: 12px;
  color: var(--c-text-muted);
}

.state {
  color: var(--c-text-muted);
}

.state.error {
  color: var(--c-danger);
}

.list {
  display: grid;
  gap: 10px;
}

.requestBody {
  min-width: 0;
}

.requestTitle {
  font-size: 14px;
  font-weight: 650;
  color: var(--c-text);
}

.requestMeta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: var(--c-text-muted);
}

.actions {
  display: inline-flex;
  gap: 8px;
}

@media (max-width: 800px) {
  .filters {
    grid-template-columns: 1fr;
  }

  .actions {
    flex-direction: column;
  }
}
</style>
