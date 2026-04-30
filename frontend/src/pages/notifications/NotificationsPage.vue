<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ChevronDownIcon, EnvelopeOpenIcon } from "@heroicons/vue/24/outline";
import type { Notification } from "@/infra/api/notifications.api";
import { useNotificationsStore } from "@/stores/notifications.store";
import { formatLocalDateTime } from "@/utils/datetime";

const { t } = useI18n();
const notifications = useNotificationsStore();

const filter = ref<"all" | "unread" | "read">("unread");
const expandedIds = ref<number[]>([]);
const bodyRefs = new Map<number, HTMLElement>();
const truncatedIds = ref<number[]>([]);

const filterOptions = computed(() => [
  { value: "all", label: t("notifications.filters.all") },
  { value: "unread", label: t("notifications.filters.unread") },
  { value: "read", label: t("notifications.filters.read") },
]);

const items = computed(() => {
  if (filter.value === "unread") {
    return notifications.items.filter((item) => !item.is_read);
  }

  if (filter.value === "read") {
    return notifications.items.filter((item) => item.is_read);
  }

  return notifications.items;
});
const isLoading = computed(() => notifications.isLoading);
const error = computed(() => notifications.error);

function currentIsReadFilter() {
  if (filter.value === "all") return null;
  return filter.value === "read";
}

async function fetchNotifications() {
  await notifications.refreshPage({
    page: 1,
    pageSize: 20,
    isRead: currentIsReadFilter(),
  });
}

function actorName(item: Notification) {
  return item.actor?.username || item.actor?.email || t("notifications.systemTitle");
}

function notificationTitle(item: Notification) {
  if (item.related_type === "room_join_request") {
    return actorName(item);
  }

  if (item.notification_type === "workflow") {
    return t("notifications.workflowTitle");
  }

  return t("notifications.systemTitle");
}

function notificationBody(item: Notification) {
  if (item.related_type === "room_join_request") {
    return t("notifications.placeholderJoinRequest");
  }

  if (item.notification_type === "workflow") {
    return t("notifications.placeholderWorkflow");
  }

  return t("notifications.placeholderGeneric");
}

function isExpanded(id: number) {
  return expandedIds.value.includes(id);
}

function isTruncated(id: number) {
  return truncatedIds.value.includes(id);
}

function toggleExpanded(id: number) {
  expandedIds.value = isExpanded(id)
    ? expandedIds.value.filter((value) => value !== id)
    : [...expandedIds.value, id];
}

function setBodyRef(id: number, el: unknown) {
  if (el instanceof HTMLElement) {
    bodyRefs.set(id, el);
    return;
  }

  bodyRefs.delete(id);
}

async function measureTruncation() {
  await nextTick();

  const nextIds = items.value
    .filter((item) => {
      const el = bodyRefs.get(item.id);
      if (!el) return false;
      return el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight + 1;
    })
    .map((item) => item.id);

  truncatedIds.value = nextIds;
  expandedIds.value = expandedIds.value.filter((id) => nextIds.includes(id));
}

async function handleOpen(item: Notification) {
  if (!item.is_read) {
    await notifications.markAsRead(item.id);
  }

  if (isTruncated(item.id)) {
    toggleExpanded(item.id);
  }
}

async function handleMarkAllRead() {
  await notifications.markAllAsRead();
}

onMounted(async () => {
  await Promise.all([fetchNotifications(), notifications.fetchUnreadCount()]);
  await measureTruncation();
  window.addEventListener("resize", measureTruncation);
});

watch(filter, () => {
  expandedIds.value = [];
  void fetchNotifications();
});

watch(items, () => {
  void measureTruncation();
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", measureTruncation);
});
</script>

<template>
  <AppPageShell
    :title="t('notifications.title')"
    :back-text="t('common.backHome')"
    :max-width="980"
  >
    <template #toolbar>
      <BaseCard class="toolbarCard">
        <div class="toolbar">
          <BaseSelect
            v-model="filter"
            :options="filterOptions"
            :label="t('notifications.filters.label')"
            label-position="start"
            :width="160"
            max-width="28vw"
          />

          <button
            class="markAllBtn"
            type="button"
            :aria-label="t('notifications.markAllRead')"
            :disabled="notifications.unreadCount === 0"
            @click="handleMarkAllRead"
          >
            <AppIcon :icon="EnvelopeOpenIcon" :size="16" />
            {{ t("notifications.markAllRead") }}
          </button>
        </div>
      </BaseCard>
    </template>

    <BaseCard class="card">
      <div v-if="isLoading" class="state">{{ t("common.loading") }}</div>
      <div v-else-if="error" class="state error">{{ error }}</div>
      <div v-else-if="items.length === 0" class="empty">
        <div class="emptyTitle">{{ t("notifications.empty.title") }}</div>
        <div class="emptyHint">{{ t("notifications.empty.hint") }}</div>
      </div>

      <TransitionGroup v-else tag="div" class="list" name="noti">
        <RowListItem
          v-for="item in items"
          :key="item.id"
          class="notificationItem"
          :data-unread="String(!item.is_read)"
        >
          <button
            class="summaryButton"
            type="button"
            :aria-expanded="isExpanded(item.id)"
            @mousedown.prevent
            @click="handleOpen(item)"
          >
            <div class="summaryTop">
              <div class="titleGroup">
                <span v-if="!item.is_read" class="unreadDot" aria-hidden="true" />
                <div class="titleText">{{ notificationTitle(item) }}</div>
              </div>

              <div class="summaryMeta">
                <span class="timeText">{{ formatLocalDateTime(item.created_at) }}</span>
                <AppIcon
                  v-if="isTruncated(item.id)"
                  class="chevron"
                  :class="{ expanded: isExpanded(item.id) }"
                  :icon="ChevronDownIcon"
                  :size="18"
                />
              </div>
            </div>

            <div
              :ref="(el) => setBodyRef(item.id, el)"
              class="bodyText"
              :class="{ expanded: isExpanded(item.id) }"
            >
              {{ notificationBody(item) }}
            </div>
          </button>
        </RowListItem>
      </TransitionGroup>
    </BaseCard>
  </AppPageShell>
</template>

<style scoped>
.toolbarCard {
  padding: 14px 18px;
}

.card {
  padding: 18px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.markAllBtn {
  margin-left: auto;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  background: transparent;
  color: var(--c-text);
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  transition: background 0.15s ease, border-color 0.15s ease, opacity 0.15s ease;
}

.markAllBtn:hover:not(:disabled) {
  background: var(--c-hover);
}

.markAllBtn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.state {
  padding: 18px 6px;
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

.notificationItem[data-unread="true"] {
  border-color: color-mix(in srgb, var(--c-primary) 18%, var(--c-border));
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
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.unreadDot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--c-danger);
  flex: 0 0 auto;
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

.summaryMeta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}

.timeText {
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

.bodyText {
  margin-top: 4px;
  min-height: 18px;
  max-height: 18px;
  overflow: hidden;
  font-size: 13px;
  line-height: 1.45;
  color: var(--c-text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.bodyText.expanded {
  max-height: none;
  display: block;
  white-space: normal;
}

@media (max-width: 800px) {
  .toolbar {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: end;
  }

  .summaryTop {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .summaryMeta {
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 520px) {
  .card {
    padding: 12px;
  }

  .toolbar {
    grid-template-columns: 1fr;
  }

  .markAllBtn {
    margin-left: 0;
    width: 100%;
  }

  .titleText {
    font-size: 13px;
  }

  .timeText,
  .bodyText {
    font-size: 12px;
  }
}
</style>

<style>
.noti-move {
  transition: transform 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.noti-leave-active {
  position: absolute;
  left: 0;
  right: 0;
  pointer-events: none;
  z-index: 1;
  transition: opacity 160ms ease, transform 160ms ease;
}

.noti-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
