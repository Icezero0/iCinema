<script setup lang="ts">
import { computed, ref, onBeforeUnmount, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth.store";
import { useI18n } from "vue-i18n";
import { getTheme, setTheme, type Theme } from "@/infra/theme";
import { CheckIcon } from "@heroicons/vue/24/outline";

import {
  PencilSquareIcon,
  MoonIcon,
  ArrowRightOnRectangleIcon,
  ChevronRightIcon,
} from "@heroicons/vue/24/outline";

const props = defineProps<{
  avatarUrl?: string;
  userName: string;
  email?: string;
}>();

const { t } = useI18n();

const auth = useAuthStore();
const router = useRouter();

const open = ref(false);
let closeTimer: number | null = null;

const themeOpen = ref(false);

const currentTheme = ref<Theme>(getTheme());

function toggleThemeMenu() {
  themeOpen.value = !themeOpen.value;
}

function pickTheme(t: Theme) {
  setTheme(t);
  currentTheme.value = t;
}

function openNow() {
  if (closeTimer) {
    window.clearTimeout(closeTimer);
    closeTimer = null;
  }
  open.value = true;
}

function closeLater() {
  if (closeTimer) window.clearTimeout(closeTimer);
  closeTimer = window.setTimeout(() => {
    open.value = false;
    themeOpen.value = false;
    closeTimer = null;
  }, 120);
}

function goProfile() {
  open.value = false;
  themeOpen.value = false;
  router.push("/profile");
}

function logout() {
  auth.logout();
  router.replace("/auth/login");
}

function onKeydown(e: KeyboardEvent) {
  if (e.key !== "Escape") return;
  if (themeOpen.value) themeOpen.value = false;
  else open.value = false;
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));

const hasEmail = computed(() => !!props.email);
</script>

<template>
  <div class="account" @mouseenter="openNow" @mouseleave="closeLater">
    <button class="trigger" type="button" aria-label="Account menu">
      <div class="avatarVisual" :class="{ open }">
        <BaseAvatar
          :src="avatarUrl"
          :name="userName"
          size="sm"
          shape="circle"
          :borderWidth="1"
        />
      </div>
    </button>

    <Transition name="fade">
      <div v-if="open" class="panel" role="menu" aria-label="Account panel">
        <BaseCard class="card">
          <div class="meta">
            <div class="name">{{ userName }}</div>
            <div v-if="hasEmail" class="email">{{ email }}</div>
          </div>

          <div class="divider" />

          <div class="actions">
            <BaseMenuItem :icon="PencilSquareIcon" @click="goProfile">
              {{ t("account.menu.editProfile") }}
            </BaseMenuItem>
            <BaseMenuItem
              :icon="MoonIcon"
              :rightIcon="ChevronRightIcon"
              @click="toggleThemeMenu"
            >
              {{ t("account.menu.theme") }}
            </BaseMenuItem>

            <div
              v-show="themeOpen"
              class="subMenu"
              role="group"
              aria-label="Theme submenu"
            >
              <BaseMenuItem
                :active="currentTheme === 'light'"
                :rightIcon="currentTheme === 'light' ? CheckIcon : undefined"
                @click="pickTheme('light')"
              >
                {{ t("account.menu.themeLight") }}
              </BaseMenuItem>

              <BaseMenuItem
                :active="currentTheme === 'dark'"
                :rightIcon="currentTheme === 'dark' ? CheckIcon : undefined"
                @click="pickTheme('dark')"
              >
                {{ t("account.menu.themeDark") }}
              </BaseMenuItem>
            </div>

            <div class="divider" />

            <BaseMenuItem
              danger
              :icon="ArrowRightOnRectangleIcon"
              @click="logout"
            >
              {{ t("account.menu.logout") }}
            </BaseMenuItem>
          </div>
        </BaseCard>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.account {
  position: relative;
  display: inline-flex;
  align-items: center;

  /* 用变量把“卡片宽度”统一管理，后面改一次即可 */
  --panel-w: 280px;
  --avatar-hit: 32px;
}

/* 固定触发区：不显示小手（避免空白处手型） */
.trigger {
  width: var(--avatar-hit);
  height: var(--avatar-hit);
  padding: 0;
  border: none;
  background: transparent;
  border-radius: 999px;
  cursor: default;
  position: relative;
}

/* panel 定位：作为 account 的子元素，鼠标移到 panel 上不会触发 account 的 mouseleave */
.panel {
  position: absolute;
  top: calc(100% + var(--s-2) + 5px);
  left: 0;
  transform: translateX(-57%);
  z-index: 40;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 300ms ease;
  will-change: opacity;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-enter-to,
.fade-leave-from {
  opacity: 1;
}

/* card 顶部留出空间给“悬浮头像” */
.card {
  width: var(--panel-w);
  padding: calc(var(--s-3) + 25px) var(--s-3) var(--s-3);
}

/* 视觉头像：默认覆盖在 trigger 中心 */
.avatarVisual {
  position: absolute;
  inset: 0;
  z-index: 50;

  display: grid;
  place-items: center;

  /* 允许命中：让移动后的头像也能 hover/click，并显示小手 */
  pointer-events: auto;
  cursor: default;

  transform: translate3d(0, 0, 0) scale(1);
  transform-origin: center;
  transition: transform 180ms ease;
}

/* 打开后：移动到 card 顶部中间 + 放大
   水平偏移： (panelW - hitW)/2
*/
.avatarVisual.open {
  transform: translate3d(
      calc((var(--panel-w) - var(--avatar-hit)) * -0.15),
      calc(100% + var(--s-2) - 20px),
      0
    )
    scale(3);
}

.subMenu {
  display: grid;
  gap: 2px;
  margin-top: 2px;
  padding-left: 26px;
}

/* 内容 */
.meta {
  display: grid;
  gap: 2px;
}
.name {
  font-weight: 600;
  color: var(--c-text);
  text-align: center;
  user-select: text;
  cursor: text;
}
.email {
  color: var(--c-text);
  font-size: 0.875rem;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  user-select: text;
  cursor: text;
}

.divider {
  height: 1px;
  background: var(--c-border);
  margin: var(--s-3) 0;
  opacity: 0.9;
}

.actions {
  display: grid;
  gap: 4px;
}
</style>
