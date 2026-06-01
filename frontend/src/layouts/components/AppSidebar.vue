<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import {
  BellIcon,
  ClipboardDocumentCheckIcon,
  InboxStackIcon,
  HomeIcon,
  InformationCircleIcon,
  PlayCircleIcon,
  UserCircleIcon,
} from "@heroicons/vue/24/outline";
import AppIcon from "@/ui/base/AppIcon.vue";
import { useAuthStore } from "@/stores/auth.store";
import { useNotificationsStore } from "@/stores/notifications.store";

defineProps<{ open: boolean; mobile?: boolean }>();

const { t } = useI18n();
const auth = useAuthStore();
const notifications = useNotificationsStore();

const badgeText = computed(() => {
  const count = notifications.unreadCount;
  if (!count || count <= 0) return "";
  return count >= 100 ? "99+" : String(count);
});

const items = computed(() => [
  { to: "/", label: t("sidebar.home"), icon: HomeIcon },
  {
    to: "/public-rooms",
    label: t("sidebar.publicRooms"),
    icon: PlayCircleIcon,
  },
  {
    to: "/join-requests",
    label: t("sidebar.joinRequests"),
    icon: ClipboardDocumentCheckIcon,
  },
  {
    to: "/notifications",
    label: t("sidebar.notifications"),
    icon: BellIcon,
    badge: badgeText.value,
  },
  { to: "/profile", label: t("sidebar.profile"), icon: UserCircleIcon },
  ...(auth.canManageFeedback
    ? [
        {
          to: "/feedback-admin",
          label: t("sidebar.feedbackAdmin"),
          icon: InboxStackIcon,
        },
      ]
    : []),
  { to: "/contact", label: t("sidebar.contact"), icon: InformationCircleIcon },
]);
</script>

<template>
  <aside
    class="sidebar"
    :class="{ mobile: mobile }"
    :data-open="open"
  >
    <div class="sidebarInner" :data-open="open">
      <nav class="nav">
        <RouterLink
          v-for="item in items"
          :key="item.to"
          class="navLink"
          :to="item.to"
          exact-active-class="router-link-exact-active"
        >
          <span class="navLead">
            <AppIcon :icon="item.icon" :size="18" />
            <span class="navLabel">{{ item.label }}</span>
          </span>

          <span v-if="item.badge" class="navBadge">{{ item.badge }}</span>
        </RouterLink>
      </nav>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 248px;
  border-right: 1px solid var(--c-border);
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--c-surface) 94%, white),
      color-mix(in srgb, var(--c-surface) 90%, var(--c-bg))
    );
  padding: 18px 14px;
  overflow: hidden;
  transition:
    width 180ms ease,
    padding 180ms ease,
    border-color 180ms ease,
    transform 180ms ease;
  position: relative;
  z-index: 40;
}

.sidebar[data-open="false"] {
  width: 0;
  padding: 0;
  border-right: none;
}

.sidebarInner {
  width: 220px;
  height: 100%;
  display: grid;
  align-content: start;
  transition:
    transform 150ms ease,
    opacity 120ms ease;
  transform: translateX(0);
  opacity: 1;
}

.sidebarInner[data-open="false"] {
  transform: translateX(-10px);
  opacity: 0;
}

.sidebar.mobile {
  position: fixed;
  top: 56px;
  bottom: 0;
  left: 0;
  width: min(280px, calc(100vw - 24px));
  border-right: 1px solid color-mix(in srgb, var(--c-border) 88%, white);
  box-shadow: 0 18px 44px rgb(0 0 0 / 0.16);
}

.sidebar.mobile[data-open="false"] {
  width: min(280px, calc(100vw - 24px));
  padding: 18px 14px;
  border-right: 1px solid color-mix(in srgb, var(--c-border) 88%, white);
  transform: translateX(calc(-100% - 12px));
}

.sidebar.mobile .sidebarInner[data-open="false"] {
  transform: translateX(0);
}

.nav {
  display: grid;
  gap: 8px;
}

.navLink {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 38px;
  padding: 0 12px;
  border-radius: 14px;
  color: var(--c-text);
  text-decoration: none;
  position: relative;
  overflow: hidden;
  transition:
    background 160ms ease,
    color 160ms ease,
    border-color 160ms ease,
    transform 160ms ease;
}

.navLink::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--c-primary) 10%, transparent),
    transparent 72%
  );
  opacity: 0;
  transition: opacity 160ms ease;
}

.navLead {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.navLabel {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.navBadge {
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-danger) 92%, white);
  color: white;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.navLink:hover {
  background: color-mix(in srgb, var(--c-hover) 78%, var(--c-surface));
  transform: translateX(2px);
}

.navLink:hover::before {
  opacity: 1;
}

.navLink.router-link-exact-active {
  background:
    linear-gradient(
      90deg,
      color-mix(in srgb, var(--c-primary) 14%, var(--c-surface)),
      color-mix(in srgb, var(--c-primary) 4%, var(--c-surface))
    );
  color: var(--c-text);
  border: 1px solid color-mix(in srgb, var(--c-primary) 22%, var(--c-border));
}

.navLink.router-link-exact-active::before {
  opacity: 0;
}

@media (max-width: 640px) {
  .sidebar.mobile {
    width: min(300px, calc(100vw - 16px));
  }

  .sidebar.mobile[data-open="false"] {
    width: min(300px, calc(100vw - 16px));
  }
}
</style>
