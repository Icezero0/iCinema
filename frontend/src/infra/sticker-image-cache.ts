import type { StickerResponse } from "@/infra/api/media.api";
import {
  clearMediaBlobCache,
  ensureMediaBlobCached,
  getCachedMediaBlob,
  pruneMediaBlobCache,
} from "@/infra/media-asset-cache";

function stickerCacheKey(stickerId: number) {
  return `sticker:${stickerId}`;
}

export async function getCachedStickerImageBlob(sticker: StickerResponse) {
  return getCachedMediaBlob(stickerCacheKey(sticker.id), sticker.url, sticker.updated_at);
}

export async function ensureStickerImageBlob(sticker: StickerResponse) {
  return ensureMediaBlobCached(stickerCacheKey(sticker.id), sticker.url, sticker.updated_at);
}

export async function pruneStickerImageCache(retainedStickerIds: number[]) {
  await pruneMediaBlobCache(retainedStickerIds.map(stickerCacheKey));
}

export async function clearStickerImageCache() {
  await clearMediaBlobCache();
}
