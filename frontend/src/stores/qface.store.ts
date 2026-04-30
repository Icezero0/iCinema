import { defineStore } from "pinia";
import {
  qfaceCatalog,
  type QfaceDefinition,
} from "@/features/chat/emoji";
import { useAssetsStore } from "@/stores/assets.store";
import { readPersistedState, writePersistedState } from "@/stores/persistence";

const STORAGE_KEY = "icinema:qface-store";
const LEGACY_EMOJI_STORAGE_KEY = "icinema:emoji-store";
const MAX_RECENT_QFACES = 30;

type PersistedState = {
  recentQfaceIds: string[];
};

type State = PersistedState & {
  catalog: QfaceDefinition[];
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

function readPersistedQfaceState() {
  const persisted = normalizePersistedState(
    readPersistedState<unknown>(STORAGE_KEY, null),
  );

  if (persisted.recentQfaceIds.length > 0) {
    return persisted;
  }

  return normalizePersistedState(
    readPersistedState<unknown>(LEGACY_EMOJI_STORAGE_KEY, null),
  );
}

function withRecentQfaceId(ids: string[], qfaceId: string) {
  return [qfaceId, ...ids.filter((id) => id !== qfaceId)].slice(
    0,
    MAX_RECENT_QFACES,
  );
}

export const useQfaceStore = defineStore("qface", {
  state: (): State => {
    const persisted = readPersistedQfaceState();

    return {
      catalog: [...qfaceCatalog],
      recentQfaceIds: persisted.recentQfaceIds,
    };
  },

  getters: {
    allQfaces(state) {
      return state.catalog;
    },
    recentQfaces(state): QfaceDefinition[] {
      const map = new Map(state.catalog.map((qface) => [qface.id, qface]));

      return state.recentQfaceIds
        .map((id) => map.get(id))
        .filter((qface): qface is QfaceDefinition => Boolean(qface));
    },
    getQfaceById(state) {
      const map = new Map(state.catalog.map((qface) => [qface.id, qface]));

      return (qfaceId: string | null | undefined) =>
        qfaceId ? map.get(qfaceId) ?? null : null;
    },
  },

  actions: {
    persist() {
      writePersistedState(STORAGE_KEY, {
        recentQfaceIds: this.recentQfaceIds,
      } satisfies PersistedState);
    },

    hydrateAssetCache(definitions?: QfaceDefinition[]) {
      const assets = useAssetsStore();
      assets.upsertQfaceCatalog(definitions ?? this.allQfaces);
    },

    markQfaceUsed(qfaceId: string) {
      if (!qfaceId) return;

      const definition = this.allQfaces.find((qface) => qface.id === qfaceId);
      if (definition) {
        this.hydrateAssetCache([definition]);
      }

      this.recentQfaceIds = withRecentQfaceId(this.recentQfaceIds, qfaceId);
      this.persist();
    },

    clear() {
      this.recentQfaceIds = [];
      this.persist();
    },
  },
});
