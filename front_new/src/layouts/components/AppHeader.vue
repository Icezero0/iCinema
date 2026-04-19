<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth.store";
import { useNotificationsStore } from "@/stores/notifications.store";
import { resolveMediaUrl } from "@/infra/media";

import AppIcon from "@/ui/base/AppIcon.vue";
import BaseIconButton from "@/ui/base/BaseIconButton.vue";
import {
  Bars3Icon,
  BellIcon,
  ClipboardDocumentCheckIcon,
} from "@heroicons/vue/24/outline";
import AccountMenuPopover from "@/layouts/components/AccountMenuPopover.vue";
import LocaleMenuButton from "@/components/LocaleMenuButton.vue";

const props = defineProps<{ sidebarOpen: boolean }>();
const emit = defineEmits<{ (e: "update:sidebarOpen", v: boolean): void }>();

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();
const notifications = useNotificationsStore();

const userEmail = computed(() => auth.me?.email || "null@example.com");
const userName = computed(() => auth.me?.username || "User");
const avatarPath = computed(() => auth.me?.avatar_url || "");
const avatarUrl = computed(() => resolveMediaUrl(avatarPath.value));

function toggleSidebar() {
  emit("update:sidebarOpen", !props.sidebarOpen);
}

function goNotifications() {
  router.push("/notifications");
}

function goJoinRequests() {
  router.push("/join-requests");
}

const badgeText = computed(() => {
  const n = notifications.unreadCount;
  if (!n || n <= 0) return "";
  if (n >= 100) return "99+";
  return String(n);
});

onMounted(() => {
  notifications.fetchUnreadCount();
});
</script>

<template>
  <header class="header">
    <div class="left">
      <BaseIconButton :aria-label="t('appShell.toggleNavigation')" @click="toggleSidebar">
        <AppIcon :icon="Bars3Icon" :size="22" />
      </BaseIconButton>
      <span class="brand">iCinema</span>
    </div>

    <div class="spacer" aria-hidden="true" />

    <div class="right">
      <AccountMenuPopover
        class="accountPopover"
        :avatar-url="avatarUrl"
        :user-name="userName"
        :email="userEmail"
      />

      <BaseIconButton :aria-label="t('joinRequests.title')" @click="goJoinRequests">
        <AppIcon :icon="ClipboardDocumentCheckIcon" :size="20" />
      </BaseIconButton>

      <div class="notiBtn">
        <BaseIconButton :aria-label="t('notifications.title')" @click="goNotifications">
          <AppIcon :icon="BellIcon" :size="20" />
        </BaseIconButton>

        <span v-if="badgeText" class="badge" aria-hidden="true">
          {{ badgeText }}
        </span>
      </div>

      <LocaleMenuButton :size="20" />
    </div>
  </header>
</template>

<style scoped>
.header {
  height: 56px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  padding: 0 var(--s-4);
  border-bottom: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 92%, var(--c-bg));
  position: relative;
  overflow: visible;
  z-index: 50;
  gap: 20px;
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.spacer {
  min-width: 0;
}

.brand {
  font-weight: 700;
  letter-spacing: 0.01em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 12rem;
}

.notiBtn {
  position: relative;
  display: inline-flex;
}

.badge {
  position: absolute;
  top: -6px;
  right: -6px;

  min-width: 18px;
  height: 18px;
  padding: 0 6px;

  display: inline-flex;
  align-items: center;
  justify-content: center;

  border-radius: 999px;
  border: 1px solid var(--c-surface);
  background: var(--c-danger);
  color: #fff;

  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.01em;
  user-select: none;
}

.accountPopover {
  margin-right: 2px;
}

@media (max-width: 860px) {
  .header {
    gap: 12px;
  }
}

@media (max-width: 640px) {
  .header {
    padding: 0 var(--s-2);
    grid-template-columns: auto 1fr auto;
  }

  .left,
  .right {
    gap: var(--s-1);
  }

  .brand {
    max-width: 6rem;
    font-size: 0.95rem;
  }
}
</style>
