<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import BaseCard from "@/ui/base/BaseCard.vue";
import RowListItem from "@/ui/base/RowListItem.vue";

import { useNotificationsStore } from "@/stores/notifications.store";
import type { Notification } from "@/infra/api/notifications.api";

const { t } = useI18n();
const noti = useNotificationsStore();

onMounted(() => {
  noti.refreshFirstPage(20);
});

const items = computed(() => noti.items);
const isLoading = computed(() => noti.isLoading);
const error = computed(() => noti.error);

function formatTime(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function getActorName(n: Notification) {
  return n.actor?.username || n.actor?.email || "-";
}

function getMessageText(n: Notification) {
  if (n.related_type === "room_join_request") {
    return t("notifications.placeholderJoinRequest");
  }

  if (n.notification_type === "workflow") {
    return t("notifications.placeholderWorkflow");
  }

  return t("notifications.placeholderGeneric");
}
</script>

<template>
  <AppPageShell
    :title="t('notifications.title')"
    :back-text="t('common.backHome')"
    :max-width="980"
  >
    <BaseCard class="card">
      <div v-if="isLoading" class="state">
        {{ t("common.loading") }}
      </div>

      <div v-else-if="error" class="state error">
        {{ error }}
      </div>

      <div v-else-if="items.length === 0" class="empty">
        <div class="emptyTitle">{{ t("notifications.empty.title") }}</div>
        <div class="emptyHint">{{ t("notifications.empty.hint") }}</div>
      </div>

      <div v-else class="list">
        <RowListItem v-for="n in items" :key="n.id">
          <template #left>
            <div class="avatarPlaceholder" />
          </template>

          <div class="textBlock">
            <div class="username">{{ getActorName(n) }}</div>
            <div class="message">{{ getMessageText(n) }}</div>
            <div class="metaLine">{{ formatTime(n.created_at) }}</div>
          </div>
        </RowListItem>
      </div>
    </BaseCard>
  </AppPageShell>
</template>

<style scoped>
.card {
  padding: 18px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  border-radius: 16px;
  box-shadow: var(--shadow-lg, 0 10px 30px rgb(0 0 0 / 0.06));
}

.state {
  padding: 18px 6px;
  color: var(--c-text-muted);
}

.state.error {
  color: var(--c-danger);
}

.empty {
  padding: 34px 10px;
  text-align: center;
  border: 1px dashed var(--c-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 70%, var(--c-bg));
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

.avatarPlaceholder {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: var(--c-hover);
  border: 1px solid var(--c-border);
  flex: 0 0 auto;
  user-select: none;
  pointer-events: none;
}

.textBlock {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  cursor: default;
  user-select: text;
}

.textBlock * {
  cursor: default;
  user-select: text;
}

.username {
  font-size: 14px;
  font-weight: 650;
  color: var(--c-text);
  line-height: 1.2;
}

.message {
  font-size: 13px;
  color: var(--c-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metaLine {
  font-size: 12px;
  color: var(--c-text-muted);
}
@media (max-width: 640px) {
  .card {
    padding: 14px;
  }
}
</style>
