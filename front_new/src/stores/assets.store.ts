import { defineStore } from "pinia";
import {
  uploadImage,
  type MediaAssetUploadResponse,
  type StickerResponse,
} from "@/infra/api/media.api";
import type { ChatEmojiDefinition } from "@/features/chat/emoji";
import { readPersistedState, writePersistedState } from "@/stores/persistence";

const STORAGE_KEY = "icinema:assets-store";
const MAX_PERSISTED_ASSETS = 240;

export type AssetKind = "image" | "sticker" | "emoji";

export type CachedAssetRecord = {
  key: string;
  kind: AssetKind;
  id: number | string;
  url: string | null;
  label?: string | null;
  provider?: string | null;
  mime_type?: string | null;
  file_size?: number | null;
  width?: number | null;
  height?: number | null;
  status?: string | null;
  static_url?: string | null;
  animated_url?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  cached_at: string;
};

type PersistedState = {
  assetsByKey: Record<string, CachedAssetRecord>;
};

type State = PersistedState & {
  isUploadingImage: boolean;
  error: string | null;
};

function createEmptyPersistedState(): PersistedState {
  return {
    assetsByKey: {},
  };
}

function extractErrorMessage(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (typeof error?.message === "string" && error.message) return error.message;

  return fallback;
}

export function createAssetKey(kind: AssetKind, id: number | string) {
  return `${kind}:${String(id)}`;
}

function trimPersistedAssets(assetsByKey: Record<string, CachedAssetRecord>) {
  const keptKeys = Object.values(assetsByKey)
    .sort((a, b) => Date.parse(b.cached_at) - Date.parse(a.cached_at))
    .slice(0, MAX_PERSISTED_ASSETS)
    .map((asset) => asset.key);

  return keptKeys.reduce<Record<string, CachedAssetRecord>>((result, key) => {
    const asset = assetsByKey[key];
    if (asset) {
      result[key] = asset;
    }
    return result;
  }, {});
}

export const useAssetsStore = defineStore("assets", {
  state: (): State => {
    const persisted = readPersistedState<PersistedState>(
      STORAGE_KEY,
      createEmptyPersistedState(),
    );

    return {
      ...persisted,
      isUploadingImage: false,
      error: null,
    };
  },

  getters: {
    getAsset: (state) => {
      return (kind: AssetKind, id: number | string | null | undefined) =>
        id == null ? null : state.assetsByKey[createAssetKey(kind, id)] ?? null;
    },
    getImageAsset() {
      return (id: number | null | undefined) =>
        typeof id === "number" ? this.getAsset("image", id) : null;
    },
    getStickerAsset() {
      return (id: number | null | undefined) =>
        typeof id === "number" ? this.getAsset("sticker", id) : null;
    },
    getEmojiAsset() {
      return (id: string | null | undefined) =>
        id ? this.getAsset("emoji", id) : null;
    },
  },

  actions: {
    persist() {
      this.assetsByKey = trimPersistedAssets(this.assetsByKey);

      writePersistedState(STORAGE_KEY, {
        assetsByKey: this.assetsByKey,
      } satisfies PersistedState);
    },

    upsertAsset(asset: Omit<CachedAssetRecord, "key" | "cached_at"> & {
      cached_at?: string;
    }) {
      const key = createAssetKey(asset.kind, asset.id);

      this.assetsByKey[key] = {
        ...this.assetsByKey[key],
        ...asset,
        key,
        cached_at: asset.cached_at || new Date().toISOString(),
      };

      this.persist();
      return this.assetsByKey[key];
    },

    upsertImageAsset(asset: MediaAssetUploadResponse | null | undefined) {
      if (!asset?.id) return null;

      return this.upsertAsset({
        kind: "image",
        id: asset.id,
        url: asset.url,
        mime_type: asset.mime_type,
        file_size: asset.file_size,
        status: asset.status,
      });
    },

    upsertMessageImageAsset(asset: {
      id: number;
      url: string | null;
    } | null | undefined) {
      if (!asset?.id || !asset.url) return null;

      return this.upsertAsset({
        kind: "image",
        id: asset.id,
        url: asset.url,
        status: "ready",
      });
    },

    upsertStickerAsset(sticker: StickerResponse | null | undefined) {
      if (!sticker?.id) return null;

      return this.upsertAsset({
        kind: "sticker",
        id: sticker.id,
        url: sticker.url,
        mime_type: sticker.mime_type,
        file_size: sticker.file_size,
        width: sticker.width,
        height: sticker.height,
        status: sticker.status,
        created_at: sticker.created_at,
        updated_at: sticker.updated_at,
      });
    },

    upsertMessageStickerAsset(asset: {
      id: number;
      url: string | null;
    } | null | undefined) {
      if (!asset?.id || !asset.url) return null;

      return this.upsertAsset({
        kind: "sticker",
        id: asset.id,
        url: asset.url,
        status: "ready",
      });
    },

    upsertEmojiAsset(emoji: {
      id: string;
      label?: string | null;
      provider?: string | null;
      staticUrl?: string | null;
      animatedUrl?: string | null;
    } | null | undefined) {
      if (!emoji?.id) return null;

      return this.upsertAsset({
        kind: "emoji",
        id: emoji.id,
        url: emoji.animatedUrl ?? emoji.staticUrl ?? null,
        label: emoji.label ?? null,
        provider: emoji.provider ?? null,
        static_url: emoji.staticUrl ?? null,
        animated_url: emoji.animatedUrl ?? null,
        status: "ready",
      });
    },

    upsertEmojiCatalog(definitions: Array<ChatEmojiDefinition | null | undefined>) {
      definitions.forEach((emoji) => {
        if (!emoji?.id) return;

        this.upsertEmojiAsset({
          id: emoji.id,
          label: emoji.label,
          staticUrl: emoji.staticUrl ?? null,
          animatedUrl: emoji.animatedUrl ?? null,
        });
      });
    },

    async uploadImage(file: File) {
      this.isUploadingImage = true;
      this.error = null;

      try {
        const uploaded = await uploadImage(file);
        this.upsertImageAsset(uploaded);
        return uploaded;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to upload image");
        this.error = message;
        throw new Error(message);
      } finally {
        this.isUploadingImage = false;
      }
    },

    clearError() {
      this.error = null;
    },

    clear() {
      this.assetsByKey = {};
      this.isUploadingImage = false;
      this.error = null;
      this.persist();
    },
  },
});
