<script setup lang="ts">
import { FaceSmileIcon, HeartIcon } from "@heroicons/vue/24/outline";
import { computed, onBeforeUnmount, onMounted, ref, type Component, type CSSProperties } from "vue";
import { useI18n } from "vue-i18n";
import { useEmojiStore } from "@/stores/emoji.store";
import { useUnicodeEmojiStore } from "@/stores/unicode_emoji.store";
import { getChatEmojiUrl, type UnicodeEmojiDefinition } from "@/features/chat/emoji";
import QfacePenguinIcon from "@/ui/icons/QfacePenguinIcon.vue";
import AppTabs from "@/ui/layout/AppTabs.vue";

const emit = defineEmits<{
  selectEmoji: [selection: { kind: "qface"; emojiId: string } | { kind: "unicode_emoji"; value: string }];
}>();
defineProps<{
  floatingStyle?: CSSProperties;
}>();

const { locale, t } = useI18n();
const emojiStore = useEmojiStore();
const unicodeEmojiStore = useUnicodeEmojiStore();
const activeEmojiTab = ref<"qface" | "unicode_emoji" | "stickers">("qface");
const isCompactViewport = ref(false);
let viewportMediaQuery: MediaQueryList | null = null;
let removeViewportListener: (() => void) | null = null;
const qfaceCatalog = computed(() => emojiStore.allEmojis);
const unicodeEmojiCatalog = computed(() => unicodeEmojiStore.allUnicodeEmojis);
const recentDisplayLimit = computed(() => (isCompactViewport.value ? 8 : 10));
const recentQface = computed(() => emojiStore.recentEmojis.slice(0, recentDisplayLimit.value));
const recentUnicodeEmoji = computed(() => (
  unicodeEmojiStore.recentUnicodeEmojis.slice(0, recentDisplayLimit.value)
));
const unicodeEmojiCategoryOrder = [
  "faces",
  "gestures",
  "hearts",
  "symbols",
  "objects",
  "nature",
] as const;
const unicodeEmojiSections = computed(() => {
  const groups = new Map<typeof unicodeEmojiCategoryOrder[number], UnicodeEmojiDefinition[]>();

  for (const emoji of unicodeEmojiCatalog.value) {
    const list = groups.get(emoji.category) ?? [];
    list.push(emoji);
    groups.set(emoji.category, list);
  }

  return unicodeEmojiCategoryOrder
    .map((category) => ({
      key: category,
      label: t(`chat.emojiPanel.sections.unicodeEmojiCategories.${category}`),
      items: groups.get(category) ?? [],
    }))
    .filter((section) => section.items.length > 0);
});
const tabItems = computed<
  Array<{ key: "qface" | "unicode_emoji" | "stickers"; label: string; icon: Component }>
>(() => [
  {
    key: "qface",
    label: t("chat.emojiPanel.tabs.qface"),
    icon: QfacePenguinIcon,
  },
  {
    key: "unicode_emoji",
    label: t("chat.emojiPanel.tabs.unicodeEmoji"),
    icon: FaceSmileIcon,
  },
  {
    key: "stickers",
    label: t("chat.emojiPanel.tabs.stickers"),
    icon: HeartIcon,
  },
]);

onMounted(() => {
  emojiStore.hydrateAssetCache();

  if (typeof window === "undefined") return;

  viewportMediaQuery = window.matchMedia("(max-width: 520px)");
  const syncViewport = (event?: MediaQueryList | MediaQueryListEvent) => {
    isCompactViewport.value = event?.matches ?? viewportMediaQuery?.matches ?? false;
  };

  syncViewport(viewportMediaQuery);
  viewportMediaQuery.addEventListener("change", syncViewport);
  removeViewportListener = () => {
    viewportMediaQuery?.removeEventListener("change", syncViewport);
    removeViewportListener = null;
    viewportMediaQuery = null;
  };
});

onBeforeUnmount(() => {
  removeViewportListener?.();
});

function selectEmoji(emojiId: string) {
  emojiStore.markEmojiUsed(emojiId);
  emit("selectEmoji", { kind: "qface", emojiId });
}

function selectUnicodeEmoji(emojiId: string) {
  const emoji = unicodeEmojiStore.getUnicodeEmojiById(emojiId);
  if (!emoji) return;

  unicodeEmojiStore.markUnicodeEmojiUsed(emojiId);
  emit("selectEmoji", { kind: "unicode_emoji", value: emoji.char });
}

function getUnicodeEmojiLabel(emoji: UnicodeEmojiDefinition) {
  return locale.value.toLowerCase().startsWith("zh") ? emoji.labelZh : emoji.labelEn;
}
</script>

<template>
  <div class="emojiPanel" :style="floatingStyle" data-emoji-panel-root="true">
    <AppTabs
      v-model="activeEmojiTab"
      class="emojiTabs"
      :items="tabItems"
      :aria-label="t('chat.emojiPanel.label')"
    />

    <div class="emojiPanelBody">
      <div v-if="activeEmojiTab === 'qface'" class="emojiSections">
        <section v-if="recentQface.length > 0" class="emojiSection">
          <p class="emojiSectionLabel">
            {{ t("chat.emojiPanel.sections.recent") }}
          </p>
          <div class="emojiGrid emojiGridRecent">
            <button
              v-for="emoji in recentQface"
              :key="`recent-${emoji.id}`"
              class="emojiOption"
              type="button"
              :aria-label="emoji.label"
              @mousedown.prevent
              @click="selectEmoji(emoji.id)"
            >
              <img
                v-if="getChatEmojiUrl(emoji.id)"
                class="emojiOptionImage"
                :src="getChatEmojiUrl(emoji.id) || undefined"
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
              v-for="emoji in qfaceCatalog"
              :key="emoji.id"
              class="emojiOption"
              type="button"
              :aria-label="emoji.label"
              @mousedown.prevent
              @click="selectEmoji(emoji.id)"
            >
              <img
                v-if="getChatEmojiUrl(emoji.id)"
                class="emojiOptionImage"
                :src="getChatEmojiUrl(emoji.id) || undefined"
                :alt="emoji.label"
              >
              <span class="emojiOptionTooltip" role="tooltip">{{ emoji.label }}</span>
            </button>
          </div>
        </section>
      </div>

      <div v-else-if="activeEmojiTab === 'unicode_emoji'" class="emojiSections">
        <section v-if="recentUnicodeEmoji.length > 0" class="emojiSection">
          <p class="emojiSectionLabel">
            {{ t("chat.emojiPanel.sections.recent") }}
          </p>
          <div class="emojiGrid emojiGridUnicode">
            <button
              v-for="emoji in recentUnicodeEmoji"
              :key="`unicode-emoji-recent-${emoji.id}`"
              class="emojiOption unicodeEmojiOption"
              type="button"
              :aria-label="getUnicodeEmojiLabel(emoji)"
              @mousedown.prevent
              @click="selectUnicodeEmoji(emoji.id)"
            >
              <span class="unicodeEmojiGlyph">{{ emoji.char }}</span>
              <span class="emojiOptionTooltip" role="tooltip">{{ getUnicodeEmojiLabel(emoji) }}</span>
            </button>
          </div>
        </section>

        <section
          v-for="section in unicodeEmojiSections"
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
              @click="selectUnicodeEmoji(emoji.id)"
            >
              <span class="unicodeEmojiGlyph">{{ emoji.char }}</span>
              <span class="emojiOptionTooltip" role="tooltip">{{ getUnicodeEmojiLabel(emoji) }}</span>
            </button>
          </div>
        </section>
      </div>

      <div v-else class="emojiEmpty">
        {{ activeEmojiTab === "unicode_emoji"
          ? t("chat.emojiPanel.emptyUnicodeEmoji")
          : t("chat.emojiPanel.emptyStickers") }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.emojiPanel {
  position: fixed;
  left: 0;
  top: 0;
  transform: translate(-50%, calc(-100% - 12px));
  width: min(320px, calc(100% - 8px), calc(100vw - 64px));
  border: 1px solid var(--c-border);
  border-radius: 16px;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--c-surface) 94%, white),
      color-mix(in srgb, var(--c-surface) 90%, var(--c-bg))
    );
  box-shadow: 0 18px 40px rgb(0 0 0 / 0.12);
  overflow: hidden;
  z-index: 8;
}

.emojiTabs {
  padding-top: 8px;
}

.emojiTabs:deep(.tabs) {
  padding-inline: 8px;
}

.emojiPanelBody {
  margin-top: 0;
  max-height: 244px;
  min-height: 172px;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 10px 12px 12px;
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
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
}

.emojiSections {
  display: grid;
  gap: 12px;
}

.emojiSection {
  display: grid;
  gap: 8px;
}

.emojiSectionLabel {
  margin: 0;
  padding-inline: 2px;
  color: var(--c-text-muted);
  font-size: 11px;
  line-height: 1.2;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.emojiGridRecent {
  min-height: 44px;
}

.emojiOption {
  min-height: 42px;
  padding: 6px;
  border: 1px solid color-mix(in srgb, var(--c-border) 88%, white);
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-surface) 88%, white);
  display: grid;
  place-items: center;
  cursor: pointer;
  position: relative;
  isolation: isolate;
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
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.unicodeEmojiOption {
  font-size: 21px;
  line-height: 1;
}

.unicodeEmojiGlyph {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transform: translateY(1px);
}

.emojiOptionTooltip {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 6px);
  transform: translate(-50%, 0);
  display: none;
  width: max-content;
  max-width: min(132px, calc(100vw - 56px));
  padding: 4px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-bg) 18%, black);
  color: color-mix(in srgb, white 94%, var(--c-surface));
  border: 1px solid color-mix(in srgb, white 18%, transparent);
  font-size: 11px;
  line-height: 1.2;
  white-space: normal;
  text-align: center;
  pointer-events: none;
  box-shadow: 0 10px 24px rgb(0 0 0 / 0.28);
}

.emojiOption:hover .emojiOptionTooltip,
.emojiOption:focus-visible .emojiOptionTooltip {
  display: block;
}

.emojiGrid > .emojiOption:nth-child(5n) .emojiOptionTooltip {
  left: auto;
  right: 0;
  transform: none;
}

.emojiGrid > .emojiOption:nth-child(5n - 4) .emojiOptionTooltip {
  left: 0;
  right: auto;
  transform: none;
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

@media (max-width: 520px) {
  .emojiPanel {
    width: min(320px, calc(100vw - 28px));
  }

  .emojiGrid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .emojiGrid > .emojiOption:nth-child(5n) .emojiOptionTooltip,
  .emojiGrid > .emojiOption:nth-child(5n - 4) .emojiOptionTooltip {
    left: 50%;
    right: auto;
    transform: translate(-50%, 0);
  }

  .emojiGrid > .emojiOption:nth-child(4n) .emojiOptionTooltip {
    left: auto;
    right: 0;
    transform: none;
  }

  .emojiGrid > .emojiOption:nth-child(4n - 3) .emojiOptionTooltip {
    left: 0;
    right: auto;
    transform: none;
  }
}
</style>
