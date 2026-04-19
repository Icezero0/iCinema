import { defineStore } from "pinia";
import { getEmojis, getRecentEmojis, type EmojiResponse } from "@/infra/api/media.api";
import {
  chatEmojiCatalog,
  type ChatEmojiDefinition,
} from "@/features/chat/emoji";
import { useAssetsStore } from "@/stores/assets.store";
import { readPersistedState, writePersistedState } from "@/stores/persistence";

const STORAGE_KEY = "icinema:emoji-store";
const MAX_RECENT_EMOJIS = 30;

type PersistedState = {
  recentQfaceIds: string[];
};

type State = PersistedState & {
  catalog: ChatEmojiDefinition[];
  remoteCatalog: ChatEmojiDefinition[];
  isLoadingCatalog: boolean;
  isLoadingRecent: boolean;
  error: string | null;
};

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function createEmptyPersistedState(): PersistedState {
  return {
    recentQfaceIds: [],
  };
}

function normalizePersistedState(raw: unknown): PersistedState {
  const fallback = createEmptyPersistedState();
  if (!raw || typeof raw !== "object") return fallback;

  const value = raw as Record<string, unknown>;
  const legacyRecentEmojiIds = isStringArray(value.recentEmojiIds)
    ? value.recentEmojiIds
    : [];

  return {
    recentQfaceIds: isStringArray(value.recentQfaceIds)
      ? value.recentQfaceIds
      : legacyRecentEmojiIds,
  };
}

function extractErrorMessage(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (typeof error?.message === "string" && error.message) return error.message;

  return fallback;
}

function pickEmojiAssetUrl(emoji: EmojiResponse, preferredTypes: number[]) {
  for (const preferredType of preferredTypes) {
    const asset = emoji.assets.find((item) => item.type === preferredType);
    if (asset?.url) return asset.url;
  }

  return emoji.assets[0]?.url;
}

function mapEmojiResponse(emoji: EmojiResponse): ChatEmojiDefinition {
  return {
    id: emoji.id,
    label: emoji.describe?.trim() || emoji.id,
    staticUrl: pickEmojiAssetUrl(emoji, [0, 1]),
    animatedUrl: pickEmojiAssetUrl(emoji, [2, 3, 0, 1]),
  };
}

function withRecentEmojiId(ids: string[], emojiId: string) {
  return [emojiId, ...ids.filter((id) => id !== emojiId)].slice(
    0,
    MAX_RECENT_EMOJIS,
  );
}

export const useEmojiStore = defineStore("emoji", {
  state: (): State => {
    const persisted = normalizePersistedState(readPersistedState<unknown>(
      STORAGE_KEY,
      null,
    ));

    return {
      catalog: [...chatEmojiCatalog],
      remoteCatalog: [],
      recentQfaceIds: persisted.recentQfaceIds,
      isLoadingCatalog: false,
      isLoadingRecent: false,
      error: null,
    };
  },

  getters: {
    allEmojis(state) {
      return state.remoteCatalog.length > 0 ? state.remoteCatalog : state.catalog;
    },
    recentEmojis(state): ChatEmojiDefinition[] {
      const catalog = state.remoteCatalog.length > 0 ? state.remoteCatalog : state.catalog;
      const map = new Map(catalog.map((emoji) => [emoji.id, emoji]));

      return state.recentQfaceIds
        .map((id) => map.get(id))
        .filter((emoji): emoji is ChatEmojiDefinition => Boolean(emoji));
    },
    getEmojiById(state) {
      const activeCatalog = state.remoteCatalog.length > 0 ? state.remoteCatalog : state.catalog;
      const map = new Map(activeCatalog.map((emoji) => [emoji.id, emoji]));

      return (emojiId: string | null | undefined) =>
        emojiId ? map.get(emojiId) ?? null : null;
    },
  },

  actions: {
    persist() {
      writePersistedState(STORAGE_KEY, {
        recentQfaceIds: this.recentQfaceIds,
      } satisfies PersistedState);
    },

    hydrateAssetCache(definitions?: ChatEmojiDefinition[]) {
      const assets = useAssetsStore();
      assets.upsertEmojiCatalog(definitions ?? this.allEmojis);
    },

    markEmojiUsed(emojiId: string) {
      if (!emojiId) return;

      const definition =
        this.allEmojis.find((emoji) => emoji.id === emojiId) ??
        this.catalog.find((emoji) => emoji.id === emojiId);
      if (definition) {
        this.hydrateAssetCache([definition]);
      }

      this.recentQfaceIds = withRecentEmojiId(this.recentQfaceIds, emojiId);
      this.persist();
    },

    async refreshCatalog() {
      this.isLoadingCatalog = true;
      this.error = null;

      try {
        const response = await getEmojis();
        this.remoteCatalog = response.items.map(mapEmojiResponse);
        this.hydrateAssetCache(this.remoteCatalog);
      } catch (error: any) {
        this.error = extractErrorMessage(error, "Failed to load emoji catalog");
      } finally {
        this.isLoadingCatalog = false;
      }
    },

    async refreshRecent(limit = 20) {
      this.isLoadingRecent = true;
      this.error = null;

      try {
        const response = await getRecentEmojis(limit);
        const serverRecentIds = response.items.map((emoji) => emoji.id);
        this.recentQfaceIds = serverRecentIds.slice(0, MAX_RECENT_EMOJIS);
        this.hydrateAssetCache(response.items.map(mapEmojiResponse));
        this.persist();
      } catch (error: any) {
        this.error = extractErrorMessage(error, "Failed to load recent emojis");
      } finally {
        this.isLoadingRecent = false;
      }
    },

    clearError() {
      this.error = null;
    },

    clear() {
      this.remoteCatalog = [];
      this.recentQfaceIds = [];
      this.isLoadingCatalog = false;
      this.isLoadingRecent = false;
      this.error = null;
      this.persist();
    },
  },
});
