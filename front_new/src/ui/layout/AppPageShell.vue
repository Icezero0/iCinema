<script setup lang="ts">
import { useSlots } from "vue";
import { useRouter } from "vue-router";
import { ArrowLeftIcon } from "@heroicons/vue/24/outline";
import AppIcon from "@/ui/base/AppIcon.vue";

const slots = useSlots();

const props = withDefaults(
  defineProps<{
    title: string;
    subtitle?: string;
    maxWidth?: number;
    backTo?: string;
    backText?: string;
    showBack?: boolean;
    backBehavior?: "route" | "emit";
  }>(),
  {
    maxWidth: 960,
    backTo: "/",
    backText: "",
    showBack: true,
    backBehavior: "route",
  },
);

const emit = defineEmits<{
  (e: "back"): void;
}>();

const router = useRouter();

function goBack() {
  if (props.backBehavior === "emit") {
    emit("back");
    return;
  }

  router.push(props.backTo);
}
</script>

<template>
  <BaseLayout :max-width="maxWidth">
    <section class="shell">
      <div class="header">
        <div class="titleRow">
          <BaseIconButton
            v-if="showBack"
            :aria-label="backText || 'Back'"
            @click="goBack"
          >
            <AppIcon :icon="ArrowLeftIcon" :size="18" />
          </BaseIconButton>

          <div class="titleBlock">
            <h1 class="title">{{ title }}</h1>
            <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
          </div>
        </div>

        <div v-if="slots.actions" class="actions">
          <slot name="actions" />
        </div>
      </div>

      <div v-if="slots.toolbar" class="toolbar">
        <slot name="toolbar" />
      </div>

      <div class="body">
        <slot />
      </div>
    </section>
  </BaseLayout>
</template>

<style scoped>
.shell {
  display: grid;
  gap: 18px;
}

.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.titleRow {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.titleBlock {
  min-width: 0;
  display: grid;
  gap: 6px;
}

.title {
  margin: 0;
  font-size: 26px;
  line-height: 1.1;
  color: var(--c-text);
  min-width: 0;
}

.subtitle {
  margin: 0;
  max-width: 76ch;
  font-size: 13px;
  line-height: 1.55;
  color: var(--c-text-muted);
}

.actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
}

.toolbar,
.body {
  min-width: 0;
}

@media (max-width: 720px) {
  .header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .title {
    font-size: 24px;
  }
}
</style>
