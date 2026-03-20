<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth.store";
import { useNotificationsStore } from "@/stores/notifications.store";

import AppIcon from "@/ui/base/AppIcon.vue";
import BaseIconButton from "@/ui/base/BaseIconButton.vue";
import { Bars3Icon, BellIcon } from "@heroicons/vue/24/outline";
import AccountMenuPopover from "@/layouts/components/AccountMenuPopover.vue";
import LocaleMenuButton from "@/components/LocaleMenuButton.vue";

const props = defineProps<{ sidebarOpen: boolean }>();
const emit = defineEmits<{ (e: "update:sidebarOpen", v: boolean): void }>();

const router = useRouter();
const auth = useAuthStore();
const notifications = useNotificationsStore();

const apiOrigin = import.meta.env.VITE_API_ORIGIN ?? "http://localhost:8000";

const userEmail = computed(() => auth.me?.email || "null@example.com");
const userName = computed(() => auth.me?.username || "User");
const avatarPath = computed(() => auth.me?.avatar_url || "");

const avatarUrl = computed(() => {
  if (!avatarPath.value) return "";
  return avatarPath.value.startsWith("http")
    ? avatarPath.value
    : `${apiOrigin}${avatarPath.value}`;
});

function toggleSidebar() {
  emit("update:sidebarOpen", !props.sidebarOpen);
}

function goNotifications() {
  router.push("/notifications");
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
      <BaseIconButton aria-label="Toggle sidebar" @click="toggleSidebar">
        <AppIcon :icon="Bars3Icon" :size="22" />
      </BaseIconButton>
      <span class="brand">iCinema</span>
    </div>

    <div class="right">
      <AccountMenuPopover
        class="accountPopover"
        :avatar-url="avatarUrl"
        :user-name="userName"
        :email="userEmail"
      />

      <div class="notiBtn">
        <BaseIconButton aria-label="Notifications" @click="goNotifications">
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
  display: flex;
  align-items: center;
  justify-content: space-between;

  padding: 0 var(--s-4);
  border-bottom: 1px solid var(--c-border);
  background: var(--c-surface);
  position: relative;
  overflow: visible;
  z-index: 50;
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  min-width: 0;
}

.brand {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 12rem;
}

.accountPopover {
  margin-right: var(--s-1);
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

@media (max-width: 640px) {
  .header {
    padding: 0 var(--s-2);
  }

  .left,
  .right {
    gap: var(--s-1);
  }

  .accountPopover {
    margin-right: 0;
  }

  .brand {
    max-width: 7rem;
    font-size: 0.95rem;
  }
}
</style>