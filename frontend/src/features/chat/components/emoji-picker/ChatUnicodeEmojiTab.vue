<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { UnicodeEmojiDefinition } from "@/features/chat/emoji";
import type { UnicodeEmojiTabProps } from "./types";

defineProps<UnicodeEmojiTabProps>();

const emit = defineEmits<{
  select: [emojiId: string];
}>();

const { locale, t } = useI18n();

function getUnicodeEmojiLabel(emoji: UnicodeEmojiDefinition) {
  return locale.value.toLowerCase().startsWith("zh") ? emoji.labelZh : emoji.labelEn;
}
</script>

<template>
  <div class="emojiSections">
    <section v-if="recentEmojis.length > 0" class="emojiSection">
      <p class="emojiSectionLabel">
        {{ t("chat.emojiPanel.sections.recent") }}
      </p>
      <div class="emojiGrid emojiGridUnicode">
        <button
          v-for="emoji in recentEmojis"
          :key="`unicode-emoji-recent-${emoji.id}`"
          class="emojiOption unicodeEmojiOption"
          type="button"
          :aria-label="getUnicodeEmojiLabel(emoji)"
          @mousedown.prevent
          @click="emit('select', emoji.id)"
        >
          <span class="unicodeEmojiGlyph">{{ emoji.char }}</span>
          <span class="emojiOptionTooltip" role="tooltip">{{ getUnicodeEmojiLabel(emoji) }}</span>
        </button>
      </div>
    </section>

    <section
      v-for="section in sections"
      :key="section.key"
      class="emojiSection"
    >
      <p class="emojiSectionLabel">
        {{ section.label }}
      </p>
      <div class="emojiGrid emojiGridUnicode">
        <button
          v-for="emoji in section.items"
          :key="`unicode-emoji-${emoji.id}`"
          class="emojiOption unicodeEmojiOption"
          type="button"
          :aria-label="getUnicodeEmojiLabel(emoji)"
          @mousedown.prevent
          @click="emit('select', emoji.id)"
        >
          <span class="unicodeEmojiGlyph">{{ emoji.char }}</span>
          <span class="emojiOptionTooltip" role="tooltip">{{ getUnicodeEmojiLabel(emoji) }}</span>
        </button>
      </div>
    </section>
  </div>
</template>
