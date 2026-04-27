import type { Component } from "vue";
import type { StickerWithDisplayUrl } from "@/stores/stickers.store";
import type {
  QfaceDefinition,
  UnicodeEmojiDefinition,
} from "@/features/chat/emoji";

export type EmojiPickerTabKey = "qface" | "unicode_emoji" | "stickers";

export type ChatEmojiPickerSelection =
  | { kind: "qface"; emojiId: string }
  | { kind: "unicode_emoji"; value: string }
  | { kind: "sticker"; stickerId: number; url: string; alt: string };

export type EmojiPickerTabItem = {
  key: EmojiPickerTabKey;
  label: string;
  icon: Component;
};

export type UnicodeEmojiSection = {
  key: string;
  label: string;
  items: UnicodeEmojiDefinition[];
};

export type StickerActionItem = {
  key: string;
  label: string;
  icon: Component;
  disabled: boolean;
};

export type QfaceTabProps = {
  recentQfaces: QfaceDefinition[];
  allQfaces: QfaceDefinition[];
};

export type UnicodeEmojiTabProps = {
  recentEmojis: UnicodeEmojiDefinition[];
  sections: UnicodeEmojiSection[];
};

export type StickerTabProps = {
  stickerLibrary: StickerWithDisplayUrl[];
  actionItems: StickerActionItem[];
  isEditing?: boolean;
  isLoading?: boolean;
  error?: string | null;
  loadingLabel?: string;
  emptyLabel: string;
};
