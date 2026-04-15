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

const scope = ref<RoomJoinRequestListScope>("pending_for_me");
const sortBy = ref<RoomJoinRequestSortBy>("updated_at");
const status = ref<RoomJoinRequestStatus | "all">("pending");

const scopeOptions = computed(() => [
  { value: "pending_for_me", label: t("joinRequests.filters.pendingForMe") },
  { value: "created_by_me", label: t("joinRequests.filters.createdByMe") },
  { value: "all_related_to_me", label: t("joinRequests.filters.allRelated") },
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
  <BaseLayout :title="t('joinRequests.title')" :max-width="980">
    <BaseCard class="card">
      <div class="header">
        <div>
          <h2 class="headline">{{ t("joinRequests.title") }}</h2>
          <p class="copy">{{ t("joinRequests.pageHint") }}</p>
        </div>
      </div>

      <div class="filters">
        <label class="field">
          <span class="label">{{ t("joinRequests.filters.scope") }}</span>
          <select v-model="scope" class="select">
            <option v-for="opt in scopeOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>

        <label class="field">
          <span class="label">{{ t("joinRequests.filters.statusLabel") }}</span>
          <select v-model="status" class="select">
            <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </label>

        <label class="field">
          <span class="label">{{ t("joinRequests.filters.sortBy") }}</span>
          <select v-model="sortBy" class="select">
            <option value="updated_at">{{ t("joinRequests.filters.updatedAt") }}</option>
            <option value="created_at">{{ t("joinRequests.filters.createdAt") }}</option>
          </select>
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
  </BaseLayout>
</template>

<style scoped>
.card {
  padding: 22px;
}

.header {
  margin-bottom: 18px;
}

.headline {
  margin: 0;
  font-size: 22px;
  color: var(--c-text);
}

.copy {
  margin: 8px 0 0;
  color: var(--c-text-muted);
  line-height: 1.6;
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

.select {
  height: 40px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: var(--c-surface);
  color: var(--c-text);
  padding: 0 12px;
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
