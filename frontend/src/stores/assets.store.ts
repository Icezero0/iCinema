import { defineStore } from "pinia";
import {
  uploadImage,
  uploadSticker,
  type MediaAssetUploadResponse,
  type StickerResponse,
} from "@/infra/api/media.api";
import type { QfaceDefinition } from "@/features/chat/emoji";
import { readPersistedState, writePersistedState } from "@/stores/persistence";
import {
  clearMediaBlobCache,
  ensureMediaBlobCached,
} from "@/infra/media-asset-cache";

const STORAGE_KEY = "icinema:assets-store";
const MAX_PERSISTED_ASSETS = 240;

export type AssetKind = "image" | "sticker" | "qface";

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
  isUploadingSticker: boolean;
  assetObjectUrls: Record<string, string>;
  cachingAssetKeys: Record<string, boolean>;
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
      isUploadingSticker: false,
      assetObjectUrls: {},
      cachingAssetKeys: {},
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
    getQfaceAsset() {
      return (id: string | null | undefined) =>
        id ? this.getAsset("qface", id) : null;
    },
    getAssetDisplayUrl: (state) => {
      return (kind: AssetKind, id: number | string | null | undefined) =>
        id == null ? null : state.assetObjectUrls[createAssetKey(kind, id)] ?? null;
    },
  },

  actions: {
    setAssetObjectUrl(key: string, url: string) {
      const previousUrl = this.assetObjectUrls[key];
      if (previousUrl && previousUrl !== url) {
        URL.revokeObjectURL(previousUrl);
      }

      this.assetObjectUrls[key] = url;
    },

    revokeAllAssetObjectUrls() {
      Object.values(this.assetObjectUrls).forEach((url) => {
        URL.revokeObjectURL(url);
      });
      this.assetObjectUrls = {};
    },

    async ensureAssetCached(asset: CachedAssetRecord | null | undefined) {
      if (!asset?.url) return;
      if (asset.kind !== "image" && asset.kind !== "sticker" && asset.kind !== "qface") return;
      if (this.cachingAssetKeys[asset.key]) return;

      this.cachingAssetKeys[asset.key] = true;

      try {
        const blob = await ensureMediaBlobCached(
          asset.key,
          asset.url,
          asset.updated_at ?? asset.created_at ?? "",
        );
        if (!blob) return;

        this.setAssetObjectUrl(asset.key, URL.createObjectURL(blob));
      } catch {
        // The remote URL remains available if local caching is unavailable.
      } finally {
        delete this.cachingAssetKeys[asset.key];
      }
    },

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
      void this.ensureAssetCached(this.assetsByKey[key]);
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

    upsertQfaceAsset(qface: {
      id: string;
      label?: string | null;
      provider?: string | null;
      staticUrl?: string | null;
      animatedUrl?: string | null;
    } | null | undefined) {
      if (!qface?.id) return null;

      return this.upsertAsset({
        kind: "qface",
        id: qface.id,
        url: qface.animatedUrl ?? qface.staticUrl ?? null,
        label: qface.label ?? null,
        provider: qface.provider ?? "qface",
        static_url: qface.staticUrl ?? null,
        animated_url: qface.animatedUrl ?? null,
        status: "ready",
      });
    },

    upsertQfaceCatalog(definitions: Array<QfaceDefinition | null | undefined>) {
      definitions.forEach((qface) => {
        if (!qface?.id) return;

        this.upsertQfaceAsset({
          id: qface.id,
          label: qface.label,
          staticUrl: qface.staticUrl ?? null,
          animatedUrl: qface.animatedUrl ?? null,
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

    async uploadSticker(file: File) {
      this.isUploadingSticker = true;
      this.error = null;

      try {
        const uploaded = await uploadSticker(file);
        this.upsertAsset({
          kind: "sticker",
          id: uploaded.id,
          url: uploaded.url,
          mime_type: uploaded.mime_type,
          file_size: uploaded.file_size,
          status: uploaded.status,
        });
        return uploaded;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to upload sticker");
        this.error = message;
        throw new Error(message);
      } finally {
        this.isUploadingSticker = false;
      }
    },

    clearError() {
      this.error = null;
    },

    clear() {
      this.assetsByKey = {};
      this.isUploadingImage = false;
      this.isUploadingSticker = false;
      this.cachingAssetKeys = {};
      this.revokeAllAssetObjectUrls();
      this.error = null;
      this.persist();
      void clearMediaBlobCache();
    },
  },
});
