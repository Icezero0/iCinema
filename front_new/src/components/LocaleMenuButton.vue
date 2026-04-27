<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { GlobeAltIcon, CheckIcon } from "@heroicons/vue/24/outline";

import AppIcon from "@/ui/base/AppIcon.vue";
import {
  getLocale,
  setLocale,
  LOCALE_OPTIONS,
  type Locale,
} from "@/infra/i18n";

/**
 * size: 传递给 AppIcon，用于控制图标尺寸
 * 例如：20（Header 用）、18（Login 用）
 */
const props = defineProps<{
  size?: number;
}>();

const open = ref(false);
const rootRef = ref<HTMLElement | null>(null);

const locale = computed(() => getLocale());

function toggle() {
  open.value = !open.value;
}
function close() {
  open.value = false;
}
function pick(l: Locale) {
  if (locale.value !== l) setLocale(l);
  close();
}

function onDocPointerDown(e: PointerEvent) {
  if (!open.value) return;
  const el = rootRef.value;
  if (!el) return;
  const target = e.target as Node | null;
  if (target && !el.contains(target)) close();
}

function onKeyDown(e: KeyboardEvent) {
  if (!open.value) return;
  if (e.key === "Escape") close();
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocPointerDown);
  document.addEventListener("keydown", onKeyDown);
});
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onDocPointerDown);
  document.removeEventListener("keydown", onKeyDown);
});
</script>

<template>
  <div class="locale" ref="rootRef">
    <BaseIconButton aria-label="Language" @click="toggle">
      <AppIcon :icon="GlobeAltIcon" :size="props.size ?? 20" />
    </BaseIconButton>

    <Transition name="menu-fade">
      <div v-show="open" class="menu" role="menu" aria-label="Language menu">
        <BaseMenuItem
          v-for="opt in LOCALE_OPTIONS"
          :key="opt.value"
          role="menuitemradio"
          :active="locale === opt.value"
          :rightIcon="locale === opt.value ? CheckIcon : undefined"
          @click="pick(opt.value as Locale)"
        >
          {{ opt.label }}
        </BaseMenuItem>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.locale {
  position: relative;
  display: inline-flex;
}

/* 菜单本体保持 DS 风格 */
.menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: max-content;
  min-width: 120px;
  max-width: min(180px, calc(100vw - 16px));

  border: 1px solid var(--c-border);
  background: var(--c-surface);
  border-radius: 14px;
  padding: 6px;
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.12);

  transform-origin: top right;
  z-index: 60;
}

/* 淡入淡出 + 轻微上浮 */
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 120ms ease, transform 120ms ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.menu-fade-enter-to,
.menu-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}

@media (prefers-reduced-motion: reduce) {
  .menu-fade-enter-active,
  .menu-fade-leave-active {
    transition: none;
  }
}
</style>
