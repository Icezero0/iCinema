<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { chatEmojiCatalog, getChatEmojiUrl } from "@/features/chat/emoji";

const emit = defineEmits<{
  selectEmoji: [emojiId: string];
}>();

const { t } = useI18n();
const activeEmojiTab = ref<"qface" | "emoji" | "stickers">("qface");

function setEmojiTab(tab: "qface" | "emoji" | "stickers") {
  activeEmojiTab.value = tab;
}

function selectEmoji(emojiId: string) {
  emit("selectEmoji", emojiId);
}
</script>

<template>
  <div class="emojiPanel">
    <div class="emojiTabs" role="tablist" :aria-label="t('chat.emojiPanel.label')">
      <button
        class="emojiTab"
        :class="{ active: activeEmojiTab === 'qface' }"
        type="button"
        role="tab"
        :aria-selected="activeEmojiTab === 'qface'"
        @click="setEmojiTab('qface')"
      >
        {{ t("chat.emojiPanel.tabs.qface") }}
      </button>
      <button
        class="emojiTab"
        :class="{ active: activeEmojiTab === 'emoji' }"
        type="button"
        role="tab"
        :aria-selected="activeEmojiTab === 'emoji'"
        @click="setEmojiTab('emoji')"
      >
        {{ t("chat.emojiPanel.tabs.emoji") }}
      </button>
      <button
        class="emojiTab"
        :class="{ active: activeEmojiTab === 'stickers' }"
        type="button"
        role="tab"
        :aria-selected="activeEmojiTab === 'stickers'"
        @click="setEmojiTab('stickers')"
      >
        {{ t("chat.emojiPanel.tabs.stickers") }}
      </button>
    </div>

    <div class="emojiPanelBody">
      <div v-if="activeEmojiTab === 'qface'" class="emojiGrid">
        <button
          v-for="emoji in chatEmojiCatalog"
          :key="emoji.id"
          class="emojiOption"
          type="button"
          :aria-label="emoji.label"
          @click="selectEmoji(emoji.id)"
        >
          <img
            v-if="getChatEmojiUrl(emoji.id)"
            class="emojiOptionImage"
            :src="getChatEmojiUrl(emoji.id) || undefined"
            :alt="emoji.label"
          >
          <span class="emojiOptionLabel">{{ emoji.label }}</span>
        </button>
      </div>

      <div v-else class="emojiEmpty">
        {{ activeEmojiTab === "emoji"
          ? t("chat.emojiPanel.emptyEmoji")
          : t("chat.emojiPanel.emptyStickers") }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.emojiPanel {
  position: absolute;
  left: 0;
  bottom: calc(100% + 12px);
  width: min(320px, calc(100vw - 64px));
  border: 1px solid var(--c-border);
  border-radius: 16px;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--c-surface) 94%, white),
      color-mix(in srgb, var(--c-surface) 90%, var(--c-bg))
    );
  box-shadow: 0 18px 40px rgb(0 0 0 / 0.12);
  padding: 12px;
  z-index: 8;
}

.emojiTabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.emojiTab {
  height: 32px;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-surface) 92%, white);
  color: var(--c-text-muted);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    color 160ms ease,
    border-color 160ms ease,
    transform 160ms ease;
}

.emojiTab:hover {
  transform: translateY(-1px);
  color: var(--c-text);
}

.emojiTab.active {
  color: var(--c-primary);
  border-color: color-mix(in srgb, var(--c-primary) 24%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 10%, var(--c-surface));
}

.emojiPanelBody {
  margin-top: 10px;
  max-height: 244px;
  min-height: 172px;
  overflow: auto;
  padding-right: 4px;
}

.emojiPanelBody::-webkit-scrollbar {
  width: 8px;
}

.emojiPanelBody::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--c-text-muted) 34%, transparent);
  border-radius: 999px;
}

.emojiGrid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.emojiOption {
  min-height: 62px;
  padding: 8px 6px;
  border: 1px solid color-mix(in srgb, var(--c-border) 88%, white);
  border-radius: 12px;
  background: color-mix(in srgb, var(--c-surface) 88%, white);
  display: grid;
  gap: 6px;
  justify-items: center;
  align-content: start;
  cursor: pointer;
  transition:
    transform 160ms ease,
    background-color 160ms ease,
    border-color 160ms ease,
    box-shadow 180ms ease;
}

.emojiOption:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--c-primary) 20%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 6%, var(--c-surface));
  box-shadow: 0 8px 16px rgb(0 0 0 / 0.05);
}

.emojiOptionImage {
  width: 26px;
  height: 26px;
  object-fit: contain;
}

.emojiOptionLabel {
  font-size: 11px;
  line-height: 1.2;
  color: var(--c-text-muted);
  text-align: center;
  word-break: break-word;
}

.emojiEmpty {
  min-height: 172px;
  display: grid;
  place-items: center;
  border: 1px dashed color-mix(in srgb, var(--c-border) 88%, white);
  border-radius: 14px;
  color: var(--c-text-muted);
  font-size: 12px;
  text-align: center;
  padding: 18px;
}
</style>
