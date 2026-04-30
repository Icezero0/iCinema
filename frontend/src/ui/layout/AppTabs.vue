<script setup lang="ts">
import { computed, type Component } from "vue";

type AppTabItem = {
  key: string;
  label: string;
  badge?: string;
  icon?: Component;
};

const props = withDefaults(
  defineProps<{
    items: AppTabItem[];
    modelValue: string;
    stretch?: boolean;
  }>(),
  {
    stretch: true,
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const gridStyle = computed(() => {
  if (!props.stretch) {
    return {};
  }

  return {
    gridTemplateColumns: `repeat(${Math.max(props.items.length, 1)}, minmax(0, 1fr))`,
  };
});

function selectTab(key: string) {
  emit("update:modelValue", key);
}
</script>

<template>
  <div class="tabs" :style="gridStyle">
    <button
      v-for="item in items"
      :key="item.key"
      class="tab"
      :class="{ active: modelValue === item.key }"
      type="button"
      @click="selectTab(item.key)"
    >
      <component :is="item.icon" v-if="item.icon" class="tabIcon" aria-hidden="true" />
      <span v-if="item.icon" class="srOnly">{{ item.label }}</span>
      <span v-else>{{ item.label }}</span>
      <span v-if="item.badge" class="badge">{{ item.badge }}</span>
    </button>
  </div>
</template>

<style scoped>
.tabs {
  display: grid;
  align-items: end;
  gap: 6px;
  padding: 0 10px;
  border-bottom: 1px solid var(--c-border);
  margin-top: -1px;
}

.tab {
  height: 42px;
  width: 100%;
  min-width: 0;
  padding: 0 12px;
  border-radius: 14px 14px 0 0;
  border: 1px solid transparent;
  border-bottom: none;
  background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg));
  color: var(--c-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  position: relative;
  transform: translateY(1px);
  white-space: nowrap;
  transition:
    background-color 180ms ease,
    border-color 180ms ease,
    color 180ms ease,
    box-shadow 220ms ease,
    transform 220ms ease;
}

.tabIcon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
}

.tab:hover {
  background: color-mix(in srgb, var(--c-surface) 84%, white);
  color: var(--c-text);
  transform: translateY(-1px);
}

.tab.active {
  background: var(--c-surface);
  border-color: color-mix(in srgb, var(--c-primary) 30%, var(--c-border));
  color: var(--c-text);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, white 75%, transparent),
    0 -1px 0 color-mix(in srgb, var(--c-primary) 18%, transparent);
  transform: translateY(0) scale(1.01);
}

.tab::after {
  content: "";
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background: transparent;
}

.tab.active::after {
  background: color-mix(in srgb, var(--c-primary) 68%, white);
  transition: background-color 180ms ease;
}

.badge {
  min-width: 14px;
  height: 14px;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--c-danger);
  color: white;
  font-size: 9px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  top: 6px;
  right: 8px;
  pointer-events: none;
}

.srOnly {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
