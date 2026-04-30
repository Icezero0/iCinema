import { defineStore } from "pinia";
import {
  unicodeEmojiCatalog,
  type UnicodeEmojiDefinition,
} from "@/features/chat/emoji";
import { readPersistedState, writePersistedState } from "@/stores/persistence";

const STORAGE_KEY = "icinema:unicode-emoji-store";
const LEGACY_EMOJI_STORAGE_KEY = "icinema:emoji-store";
const MAX_RECENT_UNICODE_EMOJIS = 30;

type PersistedState = {
  recentUnicodeEmojiIds: string[];
};

type State = PersistedState & {
  catalog: UnicodeEmojiDefinition[];
};

function createEmptyPersistedState(): PersistedState {
  return {
    recentUnicodeEmojiIds: [],
  };
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function normalizePersistedState(raw: unknown): PersistedState {
  if (!raw || typeof raw !== "object") {
    return createEmptyPersistedState();
  }

  const value = raw as Record<string, unknown>;
  return {
    recentUnicodeEmojiIds: isStringArray(value.recentUnicodeEmojiIds)
      ? value.recentUnicodeEmojiIds
      : [],
  };
}

function readLegacyRecentUnicodeEmojiIds() {
  const legacy = readPersistedState<unknown>(LEGACY_EMOJI_STORAGE_KEY, null);
  if (!legacy || typeof legacy !== "object") return [];

  const value = legacy as Record<string, unknown>;
  return isStringArray(value.recentUnicodeIds) ? value.recentUnicodeIds : [];
}

function withRecentUnicodeEmojiId(ids: string[], emojiId: string) {
  return [emojiId, ...ids.filter((id) => id !== emojiId)].slice(
    0,
    MAX_RECENT_UNICODE_EMOJIS,
  );
}

export const useUnicodeEmojiStore = defineStore("unicode_emoji", {
  state: (): State => {
    const persisted = normalizePersistedState(
      readPersistedState<unknown>(STORAGE_KEY, null),
    );
    const legacyRecent = persisted.recentUnicodeEmojiIds.length > 0
      ? []
      : readLegacyRecentUnicodeEmojiIds();

    return {
      catalog: [...unicodeEmojiCatalog],
      recentUnicodeEmojiIds:
        persisted.recentUnicodeEmojiIds.length > 0
          ? persisted.recentUnicodeEmojiIds
          : legacyRecent,
    };
  },

  getters: {
    allUnicodeEmojis(state) {
      return state.catalog;
    },
    recentUnicodeEmojis(state): UnicodeEmojiDefinition[] {
      const map = new Map(state.catalog.map((emoji) => [emoji.id, emoji]));

      return state.recentUnicodeEmojiIds
        .map((id) => map.get(id))
        .filter((emoji): emoji is UnicodeEmojiDefinition => Boolean(emoji));
    },
    getUnicodeEmojiById(state) {
      const map = new Map(state.catalog.map((emoji) => [emoji.id, emoji]));

      return (emojiId: string | null | undefined) =>
        emojiId ? map.get(emojiId) ?? null : null;
    },
  },

  actions: {
    persist() {
      writePersistedState(STORAGE_KEY, {
        recentUnicodeEmojiIds: this.recentUnicodeEmojiIds,
      } satisfies PersistedState);
    },

    markUnicodeEmojiUsed(emojiId: string) {
      if (!emojiId) return;

      this.recentUnicodeEmojiIds = withRecentUnicodeEmojiId(
        this.recentUnicodeEmojiIds,
        emojiId,
      );
      this.persist();
    },

    clear() {
      this.recentUnicodeEmojiIds = [];
      this.persist();
    },
  },
});
