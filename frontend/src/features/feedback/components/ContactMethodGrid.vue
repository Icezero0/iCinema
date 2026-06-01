<script setup lang="ts">
import { ArrowTopRightOnSquareIcon } from "@heroicons/vue/24/outline";
import type { ContactMethodItem } from "@/features/feedback/types";
import AppIcon from "@/ui/base/AppIcon.vue";

defineProps<{
  methods: ContactMethodItem[];
}>();
</script>

<template>
  <div class="methodGrid">
    <article
      v-for="method in methods"
      :key="method.key"
      class="methodCard"
    >
      <div class="methodIcon" aria-hidden="true">
        <AppIcon :icon="method.icon" :size="22" />
      </div>
      <div class="methodBody">
        <h3>{{ method.title }}</h3>
        <p>{{ method.value }}</p>
      </div>

      <div class="methodActions">
        <a
          class="methodOpenLink"
          :href="method.href"
          target="_blank"
          rel="noreferrer"
          :aria-label="method.action"
          :title="method.action"
        >
          <AppIcon :icon="ArrowTopRightOnSquareIcon" :size="18" />
          <span>{{ method.action }}</span>
        </a>
      </div>
    </article>
  </div>
</template>

<style scoped>
.methodGrid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.methodCard {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  min-height: 132px;
  padding: 16px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: var(--c-surface);
  color: inherit;
  text-decoration: none;
  transition: border-color 0.16s ease, background 0.16s ease,
    transform 0.16s ease, box-shadow 0.16s ease;
}

.methodCard:hover {
  border-color: color-mix(in srgb, var(--c-primary) 42%, var(--c-border));
  background: var(--c-hover);
  transform: translateY(-1px);
  box-shadow: 0 8px 22px color-mix(in srgb, var(--c-text) 8%, transparent);
}

.methodIcon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 42px;
  height: 42px;
  border-radius: var(--r-2);
  color: var(--c-primary);
  background: color-mix(in srgb, var(--c-primary) 12%, transparent);
}

.methodBody {
  display: grid;
  align-content: start;
  gap: 6px;
  min-width: 0;
}

.methodBody h3 {
  margin: 0;
  color: var(--c-text);
  font-size: 15px;
  line-height: 1.3;
}

.methodBody p {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--c-text-muted);
  font-size: 13px;
  line-height: 1.45;
}

.methodActions {
  grid-column: 2;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  align-self: end;
}

.methodOpenLink {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: var(--c-surface);
  color: var(--c-primary);
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.methodOpenLink:hover {
  border-color: color-mix(in srgb, var(--c-primary) 36%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 8%, var(--c-surface));
}

@media (max-width: 560px) {
  .methodCard {
    grid-template-columns: 1fr;
  }

  .methodActions {
    grid-column: auto;
    align-items: stretch;
    justify-content: flex-end;
  }

  .methodOpenLink {
    flex: 0 1 auto;
  }
}
</style>
