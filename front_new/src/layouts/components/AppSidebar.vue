<script setup lang="ts">
import { useI18n } from "vue-i18n";

defineProps<{ open: boolean }>();

const { t } = useI18n();
</script>

<template>
  <aside class="sidebar" :data-open="open">
    <div class="sidebarInner" :data-open="open">
      <nav class="nav">
        <RouterLink class="navLink" to="/" exact-active-class="router-link-exact-active">
          {{ t("sidebar.home") }}
        </RouterLink>

        <RouterLink
          class="navLink"
          to="/public-rooms"
          exact-active-class="router-link-exact-active"
        >
          {{ t("sidebar.publicRooms") }}
        </RouterLink>

        <RouterLink
          class="navLink"
          to="/notifications"
          exact-active-class="router-link-exact-active"
        >
          {{ t("sidebar.notifications") }}
        </RouterLink>

      <RouterLink
        class="navLink"
        to="/profile"
        exact-active-class="router-link-exact-active"
      >
        {{ t("sidebar.profile") }}
      </RouterLink>

      <RouterLink
        class="navLink"
        to="/join-requests"
        exact-active-class="router-link-exact-active"
      >
        {{ t("sidebar.joinRequests") }}
      </RouterLink>
    </nav>
  </div>
</aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  border-right: 1px solid var(--c-border);
  background: var(--c-surface);
  padding: var(--s-3);
  overflow: hidden;
  transition:
    width 150ms ease,
    padding 150ms ease,
    border-color 150ms ease;
}

.sidebar[data-open="false"] {
  width: 0;
  padding: 0;
  border-right: none;
}

.sidebarInner {
  width: 220px;
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

.nav {
  display: grid;
  gap: var(--s-2);
}

.navLink {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0 12px;
  border-radius: 12px;
  color: var(--c-text);
  text-decoration: none;
  white-space: nowrap;
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
</style>
