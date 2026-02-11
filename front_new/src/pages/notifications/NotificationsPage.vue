<script setup lang="ts">
import { computed, onMounted, watch, ref, nextTick, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { CheckIcon, XMarkIcon, ArrowLeftIcon } from "@heroicons/vue/24/outline";

import AppIcon from "@/ui/base/AppIcon.vue";
import BaseCard from "@/ui/base/BaseCard.vue";
import BaseIconButton from "@/ui/base/BaseIconButton.vue";
import BaseButton from "@/ui/base/BaseButton.vue";
import RowListItem from "@/ui/base/RowListItem.vue";

import { useNotificationsStore } from "@/stores/notifications.store";
import {
  parseNotificationContent,
  type Notification,
} from "@/infra/api/notifications.api";

import { useEntitiesStore } from "@/stores/entities.store";

const { t } = useI18n();
const router = useRouter();
const noti = useNotificationsStore();
const entities = useEntitiesStore();

const sentinelRef = ref<HTMLElement | null>(null);
let io: IntersectionObserver | null = null;

onMounted(async () => {
  await noti.refreshFirstPage(20);
  await nextTick();

  io = new IntersectionObserver(
    (entries) => {
      const e = entries[0];
      if (!e?.isIntersecting) return;
      noti.loadMore();
    },
    {
      root: null,
      rootMargin: "200px",
      threshold: 0,
    }
  );

  if (sentinelRef.value) {
    io.observe(sentinelRef.value);
  }
});

onBeforeUnmount(() => {
  io?.disconnect();
});

watch(
  () => noti.items,
  (items) => {
    const senderIds = items.map((n) => n.sender_id);
    const roomIds = items
      .map((n) => parseNotificationContent(n.content)?.room_id)
      .filter((v): v is number => typeof v === "number");

    entities.ensureUsers(senderIds);
    entities.ensureRooms(roomIds);
  },
  { immediate: true },
);

const items = computed(() => noti.items);
const isLoading = computed(() => noti.isLoading);
const error = computed(() => noti.error);

function goHome() {
  router.push("/");
}

function formatTime(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function getSenderName(n: Notification) {
  const id = n.sender_id;
  if (typeof id !== "number") return "-";
  return entities.usersById[id]?.username ?? `#${id}`;
}

function getAvatarUrl(n: Notification): string | undefined {
  const id = n.sender_id;
  if (typeof id !== "number") return undefined;

  const user = entities.usersById[id];
  if (!user?.avatar_path) return undefined;

  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

  return user.avatar_path.startsWith("http")
    ? user.avatar_path
    : `${apiBase}${user.avatar_path}`;
}

function getRoomName(n: Notification) {
  const parsed = parseNotificationContent(n.content);
  const roomId = parsed?.room_id;

  if (typeof roomId !== "number") return "-";

  return entities.roomsById[roomId]?.name ?? `#${roomId}`;
}

async function accept(n: Notification) {
  await noti.respond(n.id, "accept");
}

async function reject(n: Notification) {
  await noti.respond(n.id, "reject");
}
</script>

<template>
  <div class="page">
    <BaseCard class="card">
      <div class="top">
        <div class="leftTop">
          <BaseButton variant="default" @click="goHome" aria-label="Back">
            <span class="backBtn">
              <AppIcon :icon="ArrowLeftIcon" :size="18" />
            </span>
          </BaseButton>

          <h1 class="title">{{ t("notifications.title") }}</h1>
        </div>
      </div>

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

      <!-- Animated list -->
      <TransitionGroup v-else name="noti" tag="div" class="list">
        <RowListItem v-for="n in items" :key="n.id">
          <template #left>
            <img
              v-if="getAvatarUrl(n)"
              :src="getAvatarUrl(n)!"
              class="avatar"
              alt="avatar"
            />
            <div v-else class="avatarPlaceholder" />
          </template>

          <div class="textBlock">
            <div class="username">{{ getSenderName(n) }}</div>
            <div class="message">
              {{ t("notifications.inviteYouToJoin", { room: getRoomName(n) }) }}
            </div>
            <div class="metaLine">{{ formatTime(n.created_at) }}</div>
          </div>

          <template #right>
            <BaseIconButton aria-label="Reject" @click="reject(n)">
              <AppIcon :icon="XMarkIcon" :size="18" />
            </BaseIconButton>

            <BaseIconButton aria-label="Accept" @click="accept(n)">
              <AppIcon :icon="CheckIcon" :size="18" />
            </BaseIconButton>
          </template>
        </RowListItem>
      </TransitionGroup>
      <div ref="sentinelRef" class="sentinel" />
    </BaseCard>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  display: grid;
  place-items: start center;
  padding: 28px 16px;
  background: var(--c-bg);
  color: var(--c-text);
}

.card {
  width: min(760px, 100%);
  padding: 18px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  border-radius: 16px;
  box-shadow: var(--shadow-lg, 0 10px 30px rgb(0 0 0 / 0.06));
}

.top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.leftTop {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.title {
  margin: 0;
  font-size: 18px;
  letter-spacing: 0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.backBtn {
  display: inline-flex;
  align-items: center;
}

/* states */
.state {
  padding: 18px 6px;
  color: var(--c-text-muted);
}
.state.error {
  color: var(--c-danger);
}

/* empty */
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

/* list */
.list {
  display: grid;
  gap: 10px;
  position: relative; /* for leave absolute positioning */
}

/* avatar: not selectable + not draggable */
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid var(--c-border);
  flex: 0 0 auto;

  user-select: none;
  -webkit-user-drag: none;
  pointer-events: none;
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

/* text */
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
  .page {
    padding: 18px 12px;
  }
  .card {
    padding: 14px;
  }
}

.sentinel {
  height: 1px;
}
</style>
