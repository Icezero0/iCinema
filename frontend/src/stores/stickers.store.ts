import { defineStore } from "pinia";
import {
  collectImageAsSticker as collectImageAsStickerApi,
  collectSticker,
  getStickerLibrary,
  updateStickerLibrary,
  uploadSticker,
  type MediaAssetUploadResponse,
  type StickerResponse,
} from "@/infra/api/media.api";
import {
  clearStickerImageCache,
  ensureStickerImageBlob,
  pruneStickerImageCache,
} from "@/infra/sticker-image-cache";
import { useAssetsStore } from "@/stores/assets.store";
import { readPersistedState, writePersistedState } from "@/stores/persistence";
import { useToastsStore } from "@/stores/toasts.store";
import { i18n } from "@/infra/i18n";

const STORAGE_KEY = "icinema:stickers-store";
const MAX_RECENT_STICKERS = 30;
const MAX_PERSISTED_STICKERS = 200;

export type StickerWithDisplayUrl = StickerResponse & {
  display_url?: string;
};

type PersistedState = {
  stickersById: Record<number, StickerResponse>;
  libraryIds: number[];
  recentStickerIds: number[];
};

type State = PersistedState & {
  total: number;
  isLoading: boolean;
  isUploading: boolean;
  isSyncingLibrary: boolean;
  isEditingLibrary: boolean;
  stickerImageUrls: Record<number, string>;
  cachingStickerImageIds: Record<number, boolean>;
  error: string | null;
};

function createEmptyPersistedState(): PersistedState {
  return {
    stickersById: {},
    libraryIds: [],
    recentStickerIds: [],
  };
}

function extractErrorMessage(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (typeof error?.message === "string" && error.message) return error.message;

  return fallback;
}

function withRecentStickerId(ids: number[], stickerId: number) {
  return [stickerId, ...ids.filter((id) => id !== stickerId)].slice(
    0,
    MAX_RECENT_STICKERS,
  );
}

function trimPersistedStickers(
  stickersById: Record<number, StickerResponse>,
  prioritizedIds: number[],
) {
  const orderedIds = Array.from(
    new Set([
      ...prioritizedIds,
      ...Object.values(stickersById)
        .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
        .map((sticker) => sticker.id),
    ]),
  ).slice(0, MAX_PERSISTED_STICKERS);

  return orderedIds.reduce<Record<number, StickerResponse>>((result, id) => {
    const sticker = stickersById[id];
    if (sticker) {
      result[id] = sticker;
    }
    return result;
  }, {});
}

function mapUploadedAssetToSticker(asset: MediaAssetUploadResponse): StickerResponse {
  const now = new Date().toISOString();

  return {
    id: asset.id,
    asset_type: asset.asset_type,
    mime_type: asset.mime_type,
    file_size: asset.file_size,
    width: null,
    height: null,
    status: asset.status,
    sort_order: 0,
    url: asset.url,
    created_at: now,
    updated_at: now,
  };
}

export const useStickersStore = defineStore("stickers", {
  state: (): State => {
    const persisted = readPersistedState<PersistedState>(
      STORAGE_KEY,
      createEmptyPersistedState(),
    );

    return {
      ...persisted,
      total: persisted.libraryIds.length,
      isLoading: false,
      isUploading: false,
      isSyncingLibrary: false,
      isEditingLibrary: false,
      stickerImageUrls: {},
      cachingStickerImageIds: {},
      error: null,
    };
  },

  getters: {
    library(state) {
      return state.libraryIds
        .map((id) => state.stickersById[id])
        .filter((sticker): sticker is StickerResponse => Boolean(sticker))
        .map((sticker) => ({
          ...sticker,
          display_url: state.stickerImageUrls[sticker.id],
        }));
    },
    recentStickers(state) {
      return state.recentStickerIds
        .map((id) => state.stickersById[id])
        .filter((sticker): sticker is StickerResponse => Boolean(sticker))
        .map((sticker) => ({
          ...sticker,
          display_url: state.stickerImageUrls[sticker.id],
        }));
    },
    getSticker: (state) => {
      return (stickerId: number | null | undefined) =>
        typeof stickerId === "number" ? state.stickersById[stickerId] ?? null : null;
    },
    getStickerDisplayUrl: (state) => {
      return (stickerId: number | null | undefined) =>
        typeof stickerId === "number" ? state.stickerImageUrls[stickerId] ?? null : null;
    },
  },

  actions: {
    setStickerImageUrl(stickerId: number, url: string) {
      const previousUrl = this.stickerImageUrls[stickerId];
      if (previousUrl && previousUrl !== url) {
        URL.revokeObjectURL(previousUrl);
      }

      this.stickerImageUrls[stickerId] = url;
    },

    revokeStickerImageUrl(stickerId: number) {
      const previousUrl = this.stickerImageUrls[stickerId];
      if (previousUrl) {
        URL.revokeObjectURL(previousUrl);
      }

      delete this.stickerImageUrls[stickerId];
    },

    revokeAllStickerImageUrls() {
      Object.values(this.stickerImageUrls).forEach((url) => {
        URL.revokeObjectURL(url);
      });
      this.stickerImageUrls = {};
    },

    persist() {
      const libraryIds = this.libraryIds.filter((id) => this.stickersById[id]);
      const recentStickerIds = this.recentStickerIds.filter((id) => this.stickersById[id]);
      const stickersById = trimPersistedStickers(this.stickersById, [
        ...libraryIds,
        ...recentStickerIds,
      ]);

      this.stickersById = stickersById;
      this.libraryIds = libraryIds;
      this.recentStickerIds = recentStickerIds;

      writePersistedState(STORAGE_KEY, {
        stickersById,
        libraryIds,
        recentStickerIds,
      } satisfies PersistedState);
    },

    upsertSticker(sticker: StickerResponse | null | undefined) {
      if (!sticker?.id) return;

      const assets = useAssetsStore();
      this.stickersById[sticker.id] = sticker;
      assets.upsertStickerAsset(sticker);
      this.persist();
      void this.ensureStickerImageCached(sticker);
    },

    upsertStickers(stickers: Array<StickerResponse | null | undefined>) {
      const assets = useAssetsStore();

      stickers.forEach((sticker) => {
        if (sticker?.id) {
          this.stickersById[sticker.id] = sticker;
          assets.upsertStickerAsset(sticker);
        }
      });
      this.persist();
      void this.syncStickerImageCache();
    },

    async ensureStickerImageCached(sticker: StickerResponse | null | undefined) {
      if (!sticker?.id || this.cachingStickerImageIds[sticker.id]) return;

      this.cachingStickerImageIds[sticker.id] = true;

      try {
        const blob = await ensureStickerImageBlob(sticker);
        if (!blob) return;

        this.setStickerImageUrl(sticker.id, URL.createObjectURL(blob));
      } catch {
        // Keep using the original remote URL if local image caching fails.
      } finally {
        delete this.cachingStickerImageIds[sticker.id];
      }
    },

    async syncStickerImageCache() {
      const libraryStickers = this.libraryIds
        .map((id) => this.stickersById[id])
        .filter((sticker): sticker is StickerResponse => Boolean(sticker));
      const libraryIds = libraryStickers.map((sticker) => sticker.id);

      Object.keys(this.stickerImageUrls).forEach((rawId) => {
        const stickerId = Number(rawId);
        if (!libraryIds.includes(stickerId)) {
          this.revokeStickerImageUrl(stickerId);
        }
      });

      try {
        await pruneStickerImageCache(libraryIds);
      } catch {
        // Cache cleanup is best-effort.
      }

      for (const sticker of libraryStickers) {
        void this.ensureStickerImageCached(sticker);
      }
    },

    rememberRecentSticker(stickerId: number) {
      if (!this.stickersById[stickerId]) return;
      this.recentStickerIds = withRecentStickerId(this.recentStickerIds, stickerId);
      this.persist();
    },

    setLibraryEditing(isEditing: boolean) {
      this.isEditingLibrary = isEditing;
    },

    async refreshLibrary(params?: {
      all?: boolean;
      page?: number | null;
      page_size?: number | null;
    }) {
      this.isLoading = true;
      this.error = null;

      try {
        const response = await getStickerLibrary(params);
        this.upsertStickers(response.items);
        this.libraryIds = response.items.map((sticker) => sticker.id);
        this.total = response.total;
        this.persist();
        void this.syncStickerImageCache();
        return response;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to load sticker library");
        this.error = message;
        throw new Error(message);
      } finally {
        this.isLoading = false;
      }
    },

    async collectSticker(stickerId: number) {
      this.error = null;

      try {
        const sticker = await collectSticker(stickerId);
        this.upsertSticker(sticker);
        this.libraryIds = [sticker.id, ...this.libraryIds.filter((id) => id !== sticker.id)];
        this.recentStickerIds = withRecentStickerId(this.recentStickerIds, sticker.id);
        this.total = Math.max(this.total, this.libraryIds.length);
        this.persist();
        void this.syncStickerImageCache();
        return sticker;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to collect sticker");
        this.error = message;
        throw new Error(message);
      }
    },

    async collectImageAsSticker(imageId: number) {
      this.error = null;

      try {
        const sticker = await collectImageAsStickerApi(imageId);
        const existedInLibrary = this.libraryIds.includes(sticker.id);
        this.upsertSticker(sticker);

        if (!existedInLibrary) {
          this.libraryIds = [sticker.id, ...this.libraryIds.filter((id) => id !== sticker.id)];
          this.recentStickerIds = withRecentStickerId(this.recentStickerIds, sticker.id);
          this.total = Math.max(this.total, this.libraryIds.length);
        }

        this.persist();
        void this.syncStickerImageCache();
        return {
          sticker,
          existedInLibrary,
        };
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to collect image as sticker");
        this.error = message;
        throw new Error(message);
      }
    },

    async syncLibrary(stickerIds?: number[]) {
      this.isSyncingLibrary = true;
      this.error = null;

      try {
        const ids = (stickerIds ?? this.libraryIds).filter((id) => this.stickersById[id]);
        await updateStickerLibrary(ids);
        this.libraryIds = ids;
        this.total = ids.length;
        this.persist();
        void this.syncStickerImageCache();
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to sync sticker library");
        this.error = message;
        throw new Error(message);
      } finally {
        this.isSyncingLibrary = false;
      }
    },

    async uploadSticker(file: File) {
      const toasts = useToastsStore();
      this.isUploading = true;
      this.error = null;

      try {
        const uploaded = await uploadSticker(file);
        const existedInLibrary = this.libraryIds.includes(uploaded.id);
        const sticker = mapUploadedAssetToSticker(uploaded);
        this.upsertSticker(sticker);
        this.libraryIds = [sticker.id, ...this.libraryIds.filter((id) => id !== sticker.id)];
        this.recentStickerIds = withRecentStickerId(this.recentStickerIds, sticker.id);
        this.total = Math.max(this.total, this.libraryIds.length);
        if (existedInLibrary) {
          toasts.push({
            message: i18n.global.t("chat.emojiPanel.stickerUpload.duplicate"),
            tone: "warning",
          });
        }
        this.persist();
        void this.syncStickerImageCache();
        return sticker;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to upload sticker");
        this.error = message;
        throw new Error(message);
      } finally {
        this.isUploading = false;
      }
    },

    clearError() {
      this.error = null;
    },

    clear() {
      this.stickersById = {};
      this.libraryIds = [];
      this.recentStickerIds = [];
      this.total = 0;
      this.isLoading = false;
      this.isUploading = false;
      this.isSyncingLibrary = false;
      this.isEditingLibrary = false;
      this.cachingStickerImageIds = {};
      this.revokeAllStickerImageUrls();
      this.error = null;
      this.persist();
      void clearStickerImageCache();
    },
  },
});
