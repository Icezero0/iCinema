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
import { useAssetsStore } from "@/stores/assets.store";
import { readPersistedState, writePersistedState } from "@/stores/persistence";
import { useToastsStore } from "@/stores/toasts.store";
import { i18n } from "@/infra/i18n";

const STORAGE_KEY = "icinema:stickers-store";
const MAX_RECENT_STICKERS = 30;
const MAX_PERSISTED_STICKERS = 200;

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
      error: null,
    };
  },

  getters: {
    library(state) {
      return state.libraryIds
        .map((id) => state.stickersById[id])
        .filter((sticker): sticker is StickerResponse => Boolean(sticker));
    },
    recentStickers(state) {
      return state.recentStickerIds
        .map((id) => state.stickersById[id])
        .filter((sticker): sticker is StickerResponse => Boolean(sticker));
    },
    getSticker: (state) => {
      return (stickerId: number | null | undefined) =>
        typeof stickerId === "number" ? state.stickersById[stickerId] ?? null : null;
    },
  },

  actions: {
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
    },

    rememberRecentSticker(stickerId: number) {
      if (!this.stickersById[stickerId]) return;
      this.recentStickerIds = withRecentStickerId(this.recentStickerIds, stickerId);
      this.persist();
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
      this.error = null;
      this.persist();
    },
  },
});
