<script setup lang="ts">
import { FilmIcon } from "@heroicons/vue/24/outline";
import AppIcon from "@/ui/base/AppIcon.vue";

defineProps<{
  title: string;
  hint: string;
}>();
</script>

<template>
  <div class="playerShell" role="presentation">
    <div class="playerSurface">
      <div class="playerEmptyState">
        <div class="emptyIcon">
          <AppIcon :icon="FilmIcon" :size="28" />
        </div>
        <div class="emptyText">
          <div class="emptyTitle">{{ title }}</div>
          <div class="emptyHint">{{ hint }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.playerShell {
  width: 100%;
  border-radius: 22px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 16%, var(--c-border));
  background:
    linear-gradient(145deg, rgb(17 23 31), rgb(37 50 68)),
    radial-gradient(circle at top left, rgb(255 255 255 / 0.06), transparent 30%);
  box-shadow: 0 20px 60px rgb(0 0 0 / 0.18);
}

.playerSurface {
  width: 100%;
  aspect-ratio: 16 / 9;
  display: grid;
  place-items: center;
}

.playerEmptyState {
  width: min(360px, calc(100% - 48px));
  display: grid;
  justify-items: center;
  gap: 12px;
  text-align: center;
  color: white;
}

.emptyIcon {
  width: 54px;
  height: 54px;
  border-radius: 18px;
  border: 1px solid rgb(255 255 255 / 0.14);
  background: rgb(255 255 255 / 0.08);
  display: grid;
  place-items: center;
  color: rgb(232 239 248 / 0.92);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.08);
}

.emptyText {
  display: grid;
  gap: 7px;
}

.emptyTitle {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0;
}

.emptyHint {
  font-size: 13px;
  line-height: 1.5;
  color: rgb(226 233 242 / 0.78);
}

@media (max-width: 640px) {
  .playerEmptyState {
    width: min(300px, calc(100% - 32px));
    gap: 10px;
  }

  .emptyIcon {
    width: 48px;
    height: 48px;
    border-radius: 16px;
  }

  .emptyTitle {
    font-size: 18px;
  }

  .emptyHint {
    font-size: 12px;
  }
}
</style>
