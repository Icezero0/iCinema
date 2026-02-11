<script setup lang="ts">
import { computed } from "vue";
import { useAuthStore } from "@/stores/auth.store";
import AppIcon from "@/ui/base/AppIcon.vue";
import { Bars3Icon, BellIcon } from "@heroicons/vue/24/outline";
import AccountMenuPopover from "@/layouts/components/AccountMenuPopover.vue";
import LocaleMenuButton from "@/components/LocaleMenuButton.vue";

const props = defineProps<{ sidebarOpen: boolean }>();
const emit = defineEmits<{ (e: "update:sidebarOpen", v: boolean): void }>();

const auth = useAuthStore();

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const userEmail = computed(() => auth.me?.email || "null@example.com");
const userName = computed(() => auth.me?.username || "User");
const avatarPath = computed(
  () => auth.me?.avatar_path || "/avatars/default.jpg",
);

const avatarUrl = computed(() => {
  if (!avatarPath.value) return "";
  return avatarPath.value.startsWith("http")
    ? avatarPath.value
    : `${apiBase}${avatarPath.value}`;
});

function toggleSidebar() {
  emit("update:sidebarOpen", !props.sidebarOpen);
}
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
      <BaseIconButton aria-label="Messages">
        <AppIcon :icon="BellIcon" :size="20" />
      </BaseIconButton>
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
