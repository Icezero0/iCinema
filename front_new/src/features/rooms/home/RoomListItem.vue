<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { Room } from "@/infra/api/rooms.api";

const { t } = useI18n();

withDefaults(
  defineProps<{
    room: Room;
    metaText?: string;
    actionLabel: string;
    actionVariant?: "default" | "primary";
    actionLoading?: boolean;
    actionDisabled?: boolean;
  }>(),
  {
    actionVariant: "default",
    actionLoading: false,
    actionDisabled: false,
  },
);

defineEmits<{
  (e: "action"): void;
}>();
</script>

<template>
  <RowListItem>
    <div class="contentBlock">
      <div class="topLine">
        <div class="title">{{ room.name }}</div>
        <span class="badge" :data-public="String(!!room.is_public)">
          {{ room.is_public ? t("room.fields.public") : t("room.fields.private") }}
        </span>
      </div>

      <div class="meta">
        <span>#{{ room.id }}</span>
        <span v-if="metaText">
          {{ metaText }}
        </span>
        <span v-else>
          {{
            room.config
              ? t("home.roomList.configured")
              : t("home.roomList.defaultSettings")
          }}
        </span>
      </div>
    </div>

    <template #right>
      <BaseButton
        :variant="actionVariant"
        :loading="actionLoading"
        :disabled="actionDisabled"
        @click="$emit('action')"
      >
        {{ actionLabel }}
      </BaseButton>
    </template>
  </RowListItem>
</template>

<style scoped>
.contentBlock {
  min-width: 0;
}

.topLine {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.title {
  min-width: 0;
  font-size: 14px;
  font-weight: 650;
  color: var(--c-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg));
  color: var(--c-text-muted);
  font-size: 12px;
  white-space: nowrap;
  flex: 0 0 auto;
}

.badge[data-public="true"] {
  color: var(--c-text);
  border-color: color-mix(in srgb, var(--c-primary) 32%, var(--c-border));
}

.meta {
  margin-top: 6px;
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--c-text-muted);
}

@media (max-width: 640px) {
  .topLine {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }

  .meta {
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>
