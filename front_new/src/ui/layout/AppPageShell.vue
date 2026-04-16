<script setup lang="ts">
import { useRouter } from "vue-router";
import { ArrowLeftIcon } from "@heroicons/vue/24/outline";
import AppIcon from "@/ui/base/AppIcon.vue";

const props = withDefaults(
  defineProps<{
    title: string;
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
            class="backBtn"
            :aria-label="backText || 'Back'"
            @click="goBack"
          >
            <AppIcon :icon="ArrowLeftIcon" :size="18" />
          </BaseIconButton>

          <h1 class="title">{{ title }}</h1>
        </div>
      </div>

      <slot />
    </section>
  </BaseLayout>
</template>

<style scoped>
.shell {
  display: grid;
  gap: 18px;
}

.titleRow {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.title {
  margin: 0;
  font-size: 26px;
  line-height: 1.1;
  color: var(--c-text);
  min-width: 0;
}
</style>
