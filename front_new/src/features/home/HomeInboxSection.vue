<script setup lang="ts">
defineProps<{
  title: string;
  subtitle: string;
  notificationsTitle: string;
  notificationsHint: string;
  joinRequestsTitle: string;
  joinRequestsHint: string;
  unreadCount: number;
  viewNotificationsText: string;
  viewJoinRequestsText: string;
}>();

defineEmits<{
  (e: "openNotifications"): void;
  (e: "openJoinRequests"): void;
}>();
</script>

<template>
  <BaseCard class="card">
    <div class="header">
      <div class="title">{{ title }}</div>
      <div class="subtitle">{{ subtitle }}</div>
    </div>

    <div class="list">
      <div class="item">
        <div class="meta">
          <div class="itemTitle">{{ notificationsTitle }}</div>
          <div class="itemHint">{{ notificationsHint }}</div>
        </div>

        <div class="right">
          <span class="count">{{ unreadCount }}</span>
          <BaseButton @click="$emit('openNotifications')">
            {{ viewNotificationsText }}
          </BaseButton>
        </div>
      </div>

      <div class="item">
        <div class="meta">
          <div class="itemTitle">{{ joinRequestsTitle }}</div>
          <div class="itemHint">{{ joinRequestsHint }}</div>
        </div>

        <div class="right">
          <BaseButton @click="$emit('openJoinRequests')">
            {{ viewJoinRequestsText }}
          </BaseButton>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<style scoped>
.card {
  padding: 18px;
}

.header {
  margin-bottom: 14px;
}

.title {
  font-size: 18px;
  font-weight: 650;
  color: var(--c-text);
}

.subtitle {
  margin-top: 6px;
  font-size: 13px;
  color: var(--c-text-muted);
}

.list {
  display: grid;
  gap: 10px;
}

.item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 76%, var(--c-bg));
}

.meta {
  min-width: 0;
}

.itemTitle {
  font-size: 14px;
  font-weight: 650;
  color: var(--c-text);
}

.itemHint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--c-text-muted);
  line-height: 1.5;
}

.right {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}

.count {
  min-width: 30px;
  height: 30px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-primary) 16%, var(--c-surface));
  color: var(--c-text);
  font-size: 12px;
  font-weight: 700;
}

@media (max-width: 640px) {
  .item {
    flex-direction: column;
    align-items: flex-start;
  }

  .right {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
