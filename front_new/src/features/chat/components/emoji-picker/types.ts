import type { Component } from "vue";
import type { StickerResponse } from "@/infra/api/media.api";
import type {
  ChatEmojiDefinition,
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
  recentEmojis: ChatEmojiDefinition[];
  allEmojis: ChatEmojiDefinition[];
};

export type UnicodeEmojiTabProps = {
  recentEmojis: UnicodeEmojiDefinition[];
  sections: UnicodeEmojiSection[];
};

export type StickerTabProps = {
  stickerLibrary: StickerResponse[];
  actionItems: StickerActionItem[];
  isLoading?: boolean;
  error?: string | null;
  loadingLabel?: string;
  emptyLabel: string;
};
