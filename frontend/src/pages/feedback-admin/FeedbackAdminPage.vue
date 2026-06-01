<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import {
  CheckCircleIcon,
  ChevronDownIcon,
} from "@heroicons/vue/24/outline";
import {
  getFeedbackScreenshotBlob,
  listAllFeedback,
  updateFeedback,
  type Feedback,
  type FeedbackStatus,
} from "@/infra/api/feedback.api";
import { useFeedbackScreenshotUrls } from "@/features/feedback/composables/useFeedbackScreenshotUrls";
import { getBackendErrorMessage } from "@/infra/http/client";
import { useAuthStore } from "@/stores/auth.store";
import { useMediaViewerStore } from "@/stores/media-viewer.store";
import { useToastsStore } from "@/stores/toasts.store";
import { formatLocalDateTime } from "@/utils/datetime";
import AppIcon from "@/ui/base/AppIcon.vue";

const { t } = useI18n();
const auth = useAuthStore();
const router = useRouter();
const toasts = useToastsStore();
const mediaViewer = useMediaViewerStore();

const items = ref<Feedback[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const totalPages = ref(0);
const statusFilter = ref<FeedbackStatus | "all">("open");
const isLoading = ref(false);
const error = ref("");
const editingId = ref<number | null>(null);
const draftStatus = ref<FeedbackStatus>("open");
const draftNote = ref("");
const expandedIds = ref<number[]>([]);
const {
  urls: screenshotUrls,
  hasFailed: hasScreenshotFailed,
  ensureUrl: ensureScreenshotUrl,
  loadAll: loadScreenshotUrls,
} = useFeedbackScreenshotUrls(getFeedbackScreenshotBlob);

const statusOptions = computed(() => [
  { value: "all", label: t("feedbackAdmin.filters.allStatus") },
  { value: "open", label: t("feedbackAdmin.status.open") },
  { value: "reviewing", label: t("feedbackAdmin.status.reviewing") },
  { value: "resolved", label: t("feedbackAdmin.status.resolved") },
  { value: "closed", label: t("feedbackAdmin.status.closed") },
]);
const editStatusOptions = computed(() =>
  statusOptions.value.filter((option) => option.value !== "all"),
);

function statusLabel(status: FeedbackStatus) {
  return t(`feedbackAdmin.status.${status}`);
}

function statusTone(status: FeedbackStatus) {
  if (status === "resolved") return "success";
  if (status === "closed") return "closed";
  if (status === "reviewing") return "reviewing";
  return "pending";
}

function feedbackTypeLabel(type: string) {
  return t(`contact.feedback.types.${type}`);
}

function pageLabel(pageKey: string) {
  const map: Record<string, string> = {
    public_rooms: "publicRooms",
    join_requests: "joinRequests",
  };
  return t(`contact.feedback.pages.${map[pageKey] ?? pageKey}`);
}

async function refresh() {
  if (!auth.canManageFeedback) {
    await router.replace("/");
    return;
  }

  isLoading.value = true;
  error.value = "";

  try {
    const data = await listAllFeedback({
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value === "all" ? null : statusFilter.value,
    });
    items.value = data.items;
    expandedIds.value = expandedIds.value.filter((id) =>
      data.items.some((item) => item.id === id),
    );
    total.value = data.total;
    page.value = data.page;
    pageSize.value = data.page_size;
    totalPages.value = data.total_pages;
  } catch (err) {
    error.value = getBackendErrorMessage(err) || t("feedbackAdmin.loadFailed");
  } finally {
    isLoading.value = false;
  }
}

function isExpanded(id: number) {
  return expandedIds.value.includes(id);
}

async function toggleExpanded(item: Feedback) {
  if (isExpanded(item.id)) {
    expandedIds.value = expandedIds.value.filter((value) => value !== item.id);
    return;
  }

  expandedIds.value = [...expandedIds.value, item.id];
  await loadScreenshotPreviews(item);
}

function startEdit(item: Feedback) {
  editingId.value = item.id;
  draftStatus.value = item.status;
  draftNote.value = item.admin_note ?? "";
}

function cancelEdit() {
  editingId.value = null;
  draftNote.value = "";
}

async function saveEdit(item: Feedback) {
  try {
    const updated = await updateFeedback(item.id, {
      status: draftStatus.value,
      admin_note: draftNote.value || null,
    });
    items.value = items.value.map((entry) => (entry.id === updated.id ? updated : entry));
    editingId.value = null;
    toasts.push({ message: t("feedbackAdmin.saved"), tone: "success" });
  } catch (err) {
    toasts.push({
      message: getBackendErrorMessage(err) || t("feedbackAdmin.saveFailed"),
      tone: "danger",
    });
  }
}

async function loadScreenshotPreviews(item: Feedback) {
  const failedCount = await loadScreenshotUrls(item.screenshot_asset_ids);
  if (failedCount > 0) {
    toasts.push({
      message: t("feedbackAdmin.screenshotFailed"),
      tone: "danger",
    });
  }
}

async function openScreenshot(assetId: number, title: string) {
  try {
    const objectUrl = await ensureScreenshotUrl(assetId);
    if (!objectUrl) return;
    mediaViewer.openViewer({
      src: objectUrl,
      alt: title,
    });
  } catch (err) {
    toasts.push({
      message: getBackendErrorMessage(err) || t("feedbackAdmin.screenshotFailed"),
      tone: "danger",
    });
  }
}

async function retryScreenshot(assetId: number) {
  if (!hasScreenshotFailed(assetId)) return;

  try {
    await ensureScreenshotUrl(assetId);
  } catch (err) {
    toasts.push({
      message: getBackendErrorMessage(err) || t("feedbackAdmin.screenshotFailed"),
      tone: "danger",
    });
  }
}

async function changePage(nextPage: number) {
  if (nextPage < 1 || nextPage > totalPages.value || nextPage === page.value) return;
  page.value = nextPage;
  await refresh();
}

async function applyFilter() {
  page.value = 1;
  await refresh();
}

onMounted(refresh);
</script>

<template>
  <AppPageShell :title="t('feedbackAdmin.title')" :show-back="false" :max-width="1040">
    <template #toolbar>
      <BaseCard class="toolbarCard">
        <div class="filters">
          <BaseSelect
            :model-value="statusFilter"
            :options="statusOptions"
            :label="t('feedbackAdmin.filters.status')"
            label-position="start"
            :width="176"
            max-width="32vw"
            @update:model-value="statusFilter = $event as FeedbackStatus | 'all'; applyFilter()"
          />
        </div>
      </BaseCard>
    </template>

    <BaseCard class="card">
      <div v-if="isLoading" class="state">{{ t("common.loading") }}</div>
      <div v-else-if="error" class="state error">{{ error }}</div>
      <div v-else-if="items.length === 0" class="empty">
        <div class="emptyTitle">{{ t("feedbackAdmin.empty.title") }}</div>
        <div class="emptyHint">{{ t("feedbackAdmin.empty.hint") }}</div>
      </div>

      <div v-else class="feedbackList">
        <RowListItem
          v-for="item in items"
          :key="item.id"
          class="feedbackItem"
          :data-status="item.status"
        >
          <div class="feedbackBody">
            <button
              class="summaryButton"
              type="button"
              :aria-expanded="isExpanded(item.id)"
              @mousedown.prevent
              @click="toggleExpanded(item)"
            >
              <div class="summaryTop">
                <div class="titleGroup">
                  <div class="titleText">{{ item.title }}</div>
                </div>

                <div class="summaryRight">
                  <div class="summaryMeta">
                    <span class="timeText">{{ formatLocalDateTime(item.created_at) }}</span>
                    <span class="statusPill" :data-tone="statusTone(item.status)">
                      {{ statusLabel(item.status) }}
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
                <div class="itemMeta">
                  <span>{{ feedbackTypeLabel(item.feedback_type) }}</span>
                  <span>{{ pageLabel(item.page) }}</span>
                  <span>{{ item.creator?.username || item.creator?.email || `#${item.creator_id}` }}</span>
                </div>

                <p class="description">{{ item.description }}</p>

                <div v-if="item.screenshot_asset_ids.length" class="screenshotGrid">
                  <button
                    v-for="assetId in item.screenshot_asset_ids"
                    :key="assetId"
                    class="screenshotTile"
                    type="button"
                    :aria-label="item.title"
                    @click="retryScreenshot(assetId)"
                    @dblclick="openScreenshot(assetId, item.title)"
                  >
                    <img
                      v-if="screenshotUrls[assetId]"
                      :src="screenshotUrls[assetId]"
                      :alt="item.title"
                    >
                    <span
                      v-else-if="hasScreenshotFailed(assetId)"
                      class="screenshotLoading error"
                    >
                      {{ t("feedbackAdmin.screenshotRetry") }}
                    </span>
                    <span v-else class="screenshotLoading">{{ t("common.loading") }}</span>
                  </button>
                </div>

                <div v-if="editingId === item.id" class="editPanel">
                  <label class="filterField">
                    <span>{{ t("feedbackAdmin.edit.status") }}</span>
                    <BaseSelect
                      :model-value="draftStatus"
                      :options="editStatusOptions"
                      @update:model-value="draftStatus = $event as FeedbackStatus"
                    />
                  </label>

                  <label class="noteField">
                    <span>{{ t("feedbackAdmin.edit.note") }}</span>
                    <textarea v-model="draftNote" rows="3" />
                  </label>

                  <div class="itemActions">
                    <BaseButton @click="cancelEdit">{{ t("common.cancel") }}</BaseButton>
                    <BaseButton variant="primary" @click="saveEdit(item)">
                      {{ t("common.save") }}
                    </BaseButton>
                  </div>
                </div>

                <div v-else class="itemBottom">
                  <p v-if="item.admin_note" class="adminNote">
                    <AppIcon :icon="CheckCircleIcon" :size="16" />
                    {{ item.admin_note }}
                  </p>
                  <BaseButton @click="startEdit(item)">
                    {{ t("feedbackAdmin.edit.action") }}
                  </BaseButton>
                </div>
              </div>
            </Transition>
          </div>
        </RowListItem>
      </div>

      <div v-if="totalPages > 1" class="pagination">
        <BaseButton :disabled="page <= 1" @click="changePage(page - 1)">
          {{ t("publicRooms.pagination.prev") }}
        </BaseButton>
        <span>{{ t("publicRooms.pagination.pageInfo", { page, totalPages, total }) }}</span>
        <BaseButton :disabled="page >= totalPages" @click="changePage(page + 1)">
          {{ t("publicRooms.pagination.next") }}
        </BaseButton>
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

.filterField,
.noteField {
  display: grid;
  gap: 6px;
}

.filterField span,
.noteField span {
  color: var(--c-text);
  font-size: 12px;
  font-weight: 650;
}

.noteField textarea {
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: var(--c-surface);
  color: var(--c-text);
  font: inherit;
}

.noteField textarea {
  resize: vertical;
  padding: 10px;
}

.filterField :deep(.fieldRoot) {
  gap: 5px;
}

.filterField :deep(.trigger) {
  min-height: 38px;
  height: 38px;
  border-radius: 10px;
  padding: 0 10px;
}

.filterField :deep(.triggerLabel) {
  font-size: 12px;
}

.state,
.empty {
  padding: 18px 6px;
  color: var(--c-text-muted);
}

.state.error {
  color: var(--c-danger);
}

.empty {
  text-align: center;
}

.emptyTitle {
  margin-bottom: 6px;
  color: var(--c-text);
  font-size: 14px;
}

.emptyHint {
  font-size: 12px;
}

.feedbackList {
  display: grid;
  gap: 10px;
}

.feedbackItem[data-status="resolved"] {
  border-color: color-mix(in srgb, #3aa675 20%, var(--c-border));
}

.feedbackItem[data-status="closed"] {
  border-color: color-mix(in srgb, var(--c-text-muted) 22%, var(--c-border));
}

.feedbackItem[data-status="reviewing"] {
  border-color: color-mix(in srgb, var(--c-primary) 22%, var(--c-border));
}

.feedbackBody {
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

.summaryTop {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.titleGroup {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.titleText {
  min-width: 0;
  font-size: 14px;
  font-weight: 650;
  color: var(--c-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.statusPill {
  flex: 0 0 auto;
  min-height: 26px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
  user-select: none;
}

.statusPill[data-tone="pending"] {
  background: color-mix(in srgb, var(--c-hover) 72%, var(--c-surface));
  color: var(--c-text-muted);
}

.statusPill[data-tone="reviewing"] {
  background: color-mix(in srgb, var(--c-primary) 14%, var(--c-surface));
  color: var(--c-primary);
}

.statusPill[data-tone="success"] {
  background: color-mix(in srgb, #3aa675 16%, var(--c-surface));
  color: #267454;
}

.statusPill[data-tone="closed"] {
  background: color-mix(in srgb, var(--c-text-muted) 14%, var(--c-surface));
  color: var(--c-text-muted);
}

.timeText,
.itemMeta,
.description,
.adminNote {
  color: var(--c-text-muted);
  font-size: 13px;
}

.timeText {
  font-size: 12px;
  white-space: nowrap;
}

.chevron {
  color: var(--c-text-muted);
  transition: transform 160ms ease;
}

.chevron.expanded {
  transform: rotate(180deg);
}

.detailPanel {
  margin-top: 14px;
  display: grid;
  gap: 14px;
}

.itemMeta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.description {
  margin: 0;
  line-height: 1.55;
  white-space: pre-wrap;
}

.screenshotGrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, 112px);
  gap: 10px;
}

.screenshotTile {
  width: 112px;
  height: 112px;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 84%, var(--c-bg));
  cursor: zoom-in;
}

.screenshotTile img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  user-select: none;
  -webkit-user-drag: none;
}

.screenshotTile:hover {
  border-color: color-mix(in srgb, var(--c-primary) 30%, var(--c-border));
}

.screenshotLoading {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  padding: 8px;
  color: var(--c-text-muted);
  font-size: 12px;
  text-align: center;
}

.screenshotLoading.error {
  color: var(--c-danger);
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

.editPanel {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--c-border);
  border-radius: 16px;
  background: color-mix(in srgb, var(--c-surface) 84%, var(--c-bg));
}

.itemActions,
.itemBottom,
.pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.itemBottom {
  justify-content: space-between;
}

.adminNote {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.pagination {
  margin-top: 16px;
  justify-content: center;
  color: var(--c-text-muted);
  font-size: 13px;
}

@media (max-width: 800px) {
  .card {
    padding: 16px;
  }

  .summaryTop,
  .itemBottom {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .summaryRight {
    width: 100%;
    justify-content: space-between;
    align-items: flex-start;
  }

  .summaryMeta {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .filters {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 10px;
  }

  .filters :deep(.selectRoot) {
    width: 100% !important;
    max-width: 100% !important;
  }

  .screenshotGrid {
    grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  }

  .screenshotTile {
    width: 100%;
    height: auto;
    aspect-ratio: 1;
  }
}

@media (max-width: 520px) {
  .card {
    padding: 8px;
  }

  .titleText {
    font-size: 13px;
  }

  .timeText,
  .itemMeta,
  .description,
  .adminNote {
    font-size: 12px;
  }

  .statusPill {
    min-height: 24px;
    padding: 0 9px;
    font-size: 11px;
  }
}
</style>
