<script setup lang="ts">
import {
  CheckIcon,
  FaceSmileIcon,
  HeartIcon,
  PencilSquareIcon,
  PlusIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";
import { computed, onBeforeUnmount, onMounted, ref, watch, type CSSProperties } from "vue";
import { useI18n } from "vue-i18n";
import type { UnicodeEmojiDefinition } from "@/features/chat/emoji";
import { resolveMediaUrl } from "@/infra/media";
import { useQfaceStore } from "@/stores/qface.store";
import { useUnicodeEmojiStore } from "@/stores/unicode_emoji.store";
import { useStickersStore } from "@/stores/stickers.store";
import QfacePenguinIcon from "@/ui/icons/QfacePenguinIcon.vue";
import BaseConfirmDialog from "@/ui/base/BaseConfirmDialog.vue";
import AppTabs from "@/ui/layout/AppTabs.vue";
import ChatQfaceTab from "./emoji-picker/ChatQfaceTab.vue";
import ChatStickerTab from "./emoji-picker/ChatStickerTab.vue";
import ChatUnicodeEmojiTab from "./emoji-picker/ChatUnicodeEmojiTab.vue";
import type {
  ChatEmojiPickerSelection,
  EmojiPickerTabItem,
  EmojiPickerTabKey,
  StickerActionItem,
  UnicodeEmojiSection,
} from "./emoji-picker/types";

const emit = defineEmits<{
  selectEmoji: [selection: ChatEmojiPickerSelection];
}>();
defineProps<{
  floatingStyle?: CSSProperties;
}>();

const { t } = useI18n();
const qfaceStore = useQfaceStore();
const unicodeEmojiStore = useUnicodeEmojiStore();
const stickersStore = useStickersStore();
const activeEmojiTab = ref<EmojiPickerTabKey>("qface");
const isCompactViewport = ref(false);
const hasRequestedStickerLibrary = ref(false);
const emojiPanelBodyRef = ref<HTMLElement | null>(null);
const tabScrollTop = ref<Record<EmojiPickerTabKey, number>>({
  qface: 0,
  unicode_emoji: 0,
  stickers: 0,
});
const stickerUploadInputRef = ref<HTMLInputElement | null>(null);
const stickerEditMode = ref(false);
const stickerEditDraftIds = ref<number[]>([]);
const stickerCancelConfirmOpen = ref(false);
let viewportMediaQuery: MediaQueryList | null = null;
let removeViewportListener: (() => void) | null = null;
let restoreScrollFrame = 0;
const qfaceCatalog = computed(() => qfaceStore.allQfaces);
const unicodeEmojiCatalog = computed(() => unicodeEmojiStore.allUnicodeEmojis);
const stickerLibrary = computed(() => stickersStore.library);
const stickerEditDraftLibrary = computed(() => (
  stickerEditDraftIds.value
    .map((id) => stickersStore.getSticker(id))
    .filter((sticker): sticker is NonNullable<ReturnType<typeof stickersStore.getSticker>> => Boolean(sticker))
    .map((sticker) => ({
      ...sticker,
      display_url: stickersStore.getStickerDisplayUrl(sticker.id) ?? undefined,
    }))
));
const displayedStickerLibrary = computed(() => (
  stickerEditMode.value ? stickerEditDraftLibrary.value : stickerLibrary.value
));
const stickerEditDirty = computed(() => {
  const sourceIds = stickersStore.libraryIds;
  const draftIds = stickerEditDraftIds.value;
  if (sourceIds.length !== draftIds.length) return true;
  return sourceIds.some((id, index) => id !== draftIds[index]);
});
const recentDisplayLimit = computed(() => (isCompactViewport.value ? 8 : 10));
const recentQfaces = computed(() => qfaceStore.recentQfaces.slice(0, recentDisplayLimit.value));
const recentUnicodeEmoji = computed(() => (
  unicodeEmojiStore.recentUnicodeEmojis.slice(0, recentDisplayLimit.value)
));
const stickerActionItems = computed<StickerActionItem[]>(() => (
  stickerEditMode.value
    ? [
      {
        key: "save",
        label: t("chat.emojiPanel.sections.stickerActions.save"),
        icon: CheckIcon,
        disabled: stickersStore.isSyncingLibrary,
      },
      {
        key: "cancel",
        label: t("chat.emojiPanel.sections.stickerActions.cancel"),
        icon: XMarkIcon,
        disabled: stickersStore.isSyncingLibrary,
      },
    ]
    : [
      {
        key: "upload",
        label: t("chat.emojiPanel.sections.stickerActions.upload"),
        icon: PlusIcon,
        disabled: stickersStore.isUploading,
      },
      {
        key: "edit",
        label: t("chat.emojiPanel.sections.stickerActions.edit"),
        icon: PencilSquareIcon,
        disabled: stickersStore.isLoading,
      },
    ]
));
const unicodeEmojiCategoryOrder = [
  "faces",
  "gestures",
  "hearts",
  "symbols",
  "objects",
  "nature",
  "animals",
] as const;
const unicodeEmojiSections = computed<UnicodeEmojiSection[]>(() => {
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
const tabItems = computed<EmojiPickerTabItem[]>(() => [
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
  qfaceStore.hydrateAssetCache();

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
  stickersStore.setLibraryEditing(false);
  removeViewportListener?.();
  if (restoreScrollFrame) {
    cancelAnimationFrame(restoreScrollFrame);
  }
});

watch(activeEmojiTab, async (tab) => {
  if (restoreScrollFrame) {
    cancelAnimationFrame(restoreScrollFrame);
  }

  restoreScrollFrame = window.requestAnimationFrame(() => {
    restoreScrollFrame = 0;
    if (emojiPanelBodyRef.value) {
      emojiPanelBodyRef.value.scrollTop = tabScrollTop.value[tab] ?? 0;
    }
  });

  if (tab !== "stickers" || hasRequestedStickerLibrary.value) return;

  hasRequestedStickerLibrary.value = true;

  try {
    await stickersStore.refreshLibrary({ all: true });
  } catch {
    // stickers.store keeps the latest error state for the panel
  }
});

function rememberActiveTabScroll() {
  if (!emojiPanelBodyRef.value) return;
  tabScrollTop.value[activeEmojiTab.value] = emojiPanelBodyRef.value.scrollTop;
}

function selectQface(qfaceId: string) {
  qfaceStore.markQfaceUsed(qfaceId);
  emit("selectEmoji", { kind: "qface", emojiId: qfaceId });
}

function selectUnicodeEmoji(emojiId: string) {
  const emoji = unicodeEmojiStore.getUnicodeEmojiById(emojiId);
  if (!emoji) return;

  unicodeEmojiStore.markUnicodeEmojiUsed(emojiId);
  emit("selectEmoji", { kind: "unicode_emoji", value: emoji.char });
}

function selectSticker(stickerId: number) {
  const sticker = stickersStore.getSticker(stickerId);
  if (!sticker?.url) return;

  stickersStore.rememberRecentSticker(stickerId);
  emit("selectEmoji", {
    kind: "sticker",
    stickerId,
    url: stickersStore.getStickerDisplayUrl(stickerId) || resolveMediaUrl(sticker.url),
    alt: `Sticker ${stickerId}`,
  });
}

function triggerStickerUpload() {
  if (stickersStore.isUploading) return;
  stickerUploadInputRef.value?.click();
}

function enterStickerEditMode() {
  stickerEditDraftIds.value = stickersStore.libraryIds.filter((id) => stickersStore.getSticker(id));
  stickerEditMode.value = true;
  stickersStore.setLibraryEditing(true);
}

function exitStickerEditMode() {
  stickerEditMode.value = false;
  stickersStore.setLibraryEditing(false);
  stickerEditDraftIds.value = [];
  stickerCancelConfirmOpen.value = false;
}

async function saveStickerEditMode() {
  if (!stickerEditDirty.value) {
    exitStickerEditMode();
    return;
  }

  try {
    await stickersStore.syncLibrary(stickerEditDraftIds.value);
    exitStickerEditMode();
  } catch {
    // stickers.store keeps the latest error state for the panel
  }
}

function requestCancelStickerEditMode() {
  if (!stickerEditDirty.value) {
    exitStickerEditMode();
    return;
  }

  stickerCancelConfirmOpen.value = true;
}

function removeStickerFromDraft(stickerId: number) {
  stickerEditDraftIds.value = stickerEditDraftIds.value.filter((id) => id !== stickerId);
}

function reorderStickerDraft(stickerIds: number[]) {
  const knownIds = new Set(stickerEditDraftIds.value);
  const nextIds = stickerIds.filter((id) => knownIds.has(id));
  if (nextIds.length !== stickerEditDraftIds.value.length) return;

  stickerEditDraftIds.value = nextIds;
}

async function handleStickerUploadChange(event: Event) {
  const input = event.target as HTMLInputElement | null;
  const [file] = Array.from(input?.files ?? []);

  if (!file) {
    if (input) {
      input.value = "";
    }
    return;
  }

  try {
    await stickersStore.uploadSticker(file);
  } catch {
    // stickers.store keeps the latest error state for the panel
  } finally {
    if (input) {
      input.value = "";
    }
  }
}

function handleStickerAction(actionKey: string) {
  if (actionKey === "upload") {
    triggerStickerUpload();
  } else if (actionKey === "edit") {
    enterStickerEditMode();
  } else if (actionKey === "save") {
    void saveStickerEditMode();
  } else if (actionKey === "cancel") {
    requestCancelStickerEditMode();
  }
}
</script>

<template>
  <div class="emojiPanel" :style="floatingStyle" data-emoji-panel-root="true">
    <input
      ref="stickerUploadInputRef"
      class="srOnlyInput"
      type="file"
      accept="image/*"
      @change="handleStickerUploadChange"
    >

    <AppTabs
      v-model="activeEmojiTab"
      class="emojiTabs"
      :items="tabItems"
      :aria-label="t('chat.emojiPanel.label')"
    />

    <div
      ref="emojiPanelBodyRef"
      class="emojiPanelBody"
      @scroll.passive="rememberActiveTabScroll"
    >
      <ChatQfaceTab
        v-if="activeEmojiTab === 'qface'"
        :recent-qfaces="recentQfaces"
        :all-qfaces="qfaceCatalog"
        @select="selectQface"
      />

      <ChatUnicodeEmojiTab
        v-else-if="activeEmojiTab === 'unicode_emoji'"
        :recent-emojis="recentUnicodeEmoji"
        :sections="unicodeEmojiSections"
        @select="selectUnicodeEmoji"
      />

      <ChatStickerTab
        v-else
        :sticker-library="displayedStickerLibrary"
        :action-items="stickerActionItems"
        :is-editing="stickerEditMode"
        :is-loading="stickersStore.isLoading"
        :error="stickersStore.error"
        :loading-label="t('common.loading')"
        :empty-label="t('chat.emojiPanel.emptyStickers')"
        @action="handleStickerAction"
        @select="selectSticker"
        @remove="removeStickerFromDraft"
        @reorder="reorderStickerDraft"
      />
    </div>

    <BaseConfirmDialog
      v-model="stickerCancelConfirmOpen"
      :title="t('chat.emojiPanel.sections.stickerActions.unsavedTitle')"
      :message="t('chat.emojiPanel.sections.stickerActions.unsavedMessage')"
      :confirm-text="t('chat.emojiPanel.sections.stickerActions.discard')"
      :cancel-text="t('chat.emojiPanel.sections.stickerActions.keepEditing')"
      variant="danger"
      @confirm="exitStickerEditMode"
    />
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

.srOnlyInput {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.emojiPanelBody {
  margin-top: 0;
  max-height: 244px;
  min-height: 172px;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  padding: 10px 12px 12px;
}

.emojiPanelBody::-webkit-scrollbar {
  width: 8px;
}

.emojiPanelBody::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--c-text-muted) 34%, transparent);
  border-radius: 999px;
}

:deep(.emojiGrid) {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
}

:deep(.emojiSections) {
  display: grid;
  gap: 12px;
}

:deep(.emojiSection) {
  display: grid;
  gap: 8px;
}

:deep(.emojiSectionLabel) {
  margin: 0;
  padding-inline: 2px;
  color: var(--c-text-muted);
  font-size: 11px;
  line-height: 1.2;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

:deep(.emojiGridRecent) {
  min-height: 44px;
}

:deep(.emojiOption) {
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

:deep(.emojiOption:hover) {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--c-primary) 20%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 6%, var(--c-surface));
  box-shadow: 0 8px 16px rgb(0 0 0 / 0.05);
}

:deep(.emojiOption:disabled) {
  opacity: 0.56;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

:deep(.emojiOption:disabled:hover) {
  border-color: color-mix(in srgb, var(--c-border) 88%, white);
  background: color-mix(in srgb, var(--c-surface) 88%, white);
}

:deep(.emojiOptionImage) {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

:deep(.unicodeEmojiOption) {
  font-size: 21px;
  line-height: 1;
}

:deep(.unicodeEmojiGlyph) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transform: translateY(1px);
}

:deep(.emojiOptionTooltip) {
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

:deep(.emojiOption:hover .emojiOptionTooltip),
:deep(.emojiOption:focus-visible .emojiOptionTooltip) {
  display: block;
}

:deep(.emojiGrid > .emojiOption:nth-child(5n) .emojiOptionTooltip) {
  left: auto;
  right: 0;
  transform: none;
}

:deep(.emojiGrid > .emojiOption:nth-child(5n - 4) .emojiOptionTooltip) {
  left: 0;
  right: auto;
  transform: none;
}

:deep(.emojiEmpty) {
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

:deep(.stickerSections) {
  gap: 10px;
}

:deep(.stickerActionGrid) {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 5px;
}

:deep(.stickerActionOption) {
  min-height: 38px;
  padding: 4px;
  border-radius: 9px;
  color: var(--c-text-muted);
}

:deep(.stickerActionOption:hover:not(:disabled)) {
  color: var(--c-text);
}

:deep(.stickerActionOption:disabled) {
  color: color-mix(in srgb, var(--c-text-muted) 62%, transparent);
}

:deep(.stickerActionIcon) {
  width: 16px;
  height: 16px;
  color: currentColor;
}

:deep(.stickerGrid) {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

:deep(.stickerOption) {
  min-height: 58px;
  padding: 6px;
}

:deep(.stickerOptionImage) {
  width: 100%;
  max-width: 46px;
  height: auto;
  max-height: 46px;
  object-fit: contain;
}

:deep(.stickerEmpty) {
  min-height: 96px;
}

@media (max-width: 520px) {
  .emojiPanel {
    width: min(320px, calc(100vw - 28px));
  }

  :deep(.emojiGrid) {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  :deep(.emojiGrid > .emojiOption:nth-child(5n) .emojiOptionTooltip),
  :deep(.emojiGrid > .emojiOption:nth-child(5n - 4) .emojiOptionTooltip) {
    left: 50%;
    right: auto;
    transform: translate(-50%, 0);
  }

  :deep(.emojiGrid > .emojiOption:nth-child(4n) .emojiOptionTooltip) {
    left: auto;
    right: 0;
    transform: none;
  }

  :deep(.emojiGrid > .emojiOption:nth-child(4n - 3) .emojiOptionTooltip) {
    left: 0;
    right: auto;
    transform: none;
  }

  :deep(.stickerGrid) {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
