<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { getQfaceUrl } from "@/features/chat/emoji";
import type { QfaceTabProps } from "./types";

defineProps<QfaceTabProps>();

const emit = defineEmits<{
  select: [emojiId: string];
}>();

const { t } = useI18n();
</script>

<template>
  <div class="emojiSections">
    <section v-if="recentQfaces.length > 0" class="emojiSection">
      <p class="emojiSectionLabel">
        {{ t("chat.emojiPanel.sections.recent") }}
      </p>
      <div class="emojiGrid emojiGridRecent">
        <button
          v-for="emoji in recentQfaces"
          :key="`recent-${emoji.id}`"
          class="emojiOption"
          type="button"
          :aria-label="emoji.label"
          @mousedown.prevent
          @click="emit('select', emoji.id)"
        >
          <img
            v-if="getQfaceUrl(emoji.id)"
            class="emojiOptionImage"
            :src="getQfaceUrl(emoji.id) || undefined"
            :alt="emoji.label"
          >
          <span class="emojiOptionTooltip" role="tooltip">{{ emoji.label }}</span>
        </button>
      </div>
    </section>

    <section class="emojiSection">
      <p class="emojiSectionLabel">
        {{ t("chat.emojiPanel.sections.allQface") }}
      </p>
      <div class="emojiGrid">
        <button
          v-for="emoji in allQfaces"
          :key="emoji.id"
          class="emojiOption"
          type="button"
          :aria-label="emoji.label"
          @mousedown.prevent
          @click="emit('select', emoji.id)"
        >
          <img
            v-if="getQfaceUrl(emoji.id)"
            class="emojiOptionImage"
            :src="getQfaceUrl(emoji.id) || undefined"
            :alt="emoji.label"
          >
          <span class="emojiOptionTooltip" role="tooltip">{{ emoji.label }}</span>
        </button>
      </div>
    </section>
  </div>
</template>
