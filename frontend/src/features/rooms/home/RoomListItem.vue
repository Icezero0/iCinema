<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { Room } from "@/infra/api/rooms.api";
import { computed } from "vue";
import BasePill from "@/ui/base/BasePill.vue";
import { resolveMediaUrl } from "@/infra/media";

const { t } = useI18n();

const props = withDefaults(
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

const ownerAvatarUrl = computed(() => resolveMediaUrl(props.room.owner_avatar_url));

defineEmits<{
  (e: "action"): void;
}>();
</script>

<template>
  <RowListItem>
    <div class="contentBlock">
      <div class="topLine">
        <div class="title">{{ room.name }}</div>
        <BasePill
          size="sm"
          :tone="room.visibility === 'public' ? 'accent' : 'muted'"
          class="visibilityPill"
        >
          {{
            room.visibility === "public"
              ? t("room.fields.public")
              : t("room.fields.private")
          }}
        </BasePill>
      </div>

      <div class="meta">
        <BaseAvatar
          class="ownerAvatar"
          size="xs"
          :src="ownerAvatarUrl"
          :name="room.owner_name || undefined"
        />
        <span class="ownerName">
          {{ room.owner_name || t("home.roomList.defaultSettings") }}
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
  cursor: text;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.visibilityPill {
  flex: 0 0 auto;
  cursor: default;
}

.meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--c-text-muted);
}

.ownerAvatar {
  flex: 0 0 auto;
  cursor: default;
  user-select: none;
  -webkit-user-select: none;
}

.ownerName {
  min-width: 0;
  cursor: text;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
