import { openDB, type DBSchema } from "idb";
import { resolveMediaUrl } from "@/infra/media";
import type { StickerResponse } from "@/infra/api/media.api";

const DB_NAME = "icinema-sticker-cache";
const DB_VERSION = 1;
const STORE_NAME = "stickerImages";

type CachedStickerImage = {
  id: number;
  sourceUrl: string;
  updatedAt: string;
  blob: Blob;
};

interface StickerImageCacheDB extends DBSchema {
  stickerImages: {
    key: number;
    value: CachedStickerImage;
  };
}

function canUseIndexedDB() {
  return typeof window !== "undefined" && "indexedDB" in window;
}

const dbPromise = canUseIndexedDB()
  ? openDB<StickerImageCacheDB>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    },
  })
  : null;

function cacheEntryMatches(entry: CachedStickerImage, sticker: StickerResponse) {
  return entry.sourceUrl === sticker.url && entry.updatedAt === sticker.updated_at;
}

async function getDb() {
  return dbPromise;
}

export async function getCachedStickerImageBlob(sticker: StickerResponse) {
  const db = await getDb();
  if (!db) return null;

  const entry = await db.get(STORE_NAME, sticker.id);
  if (!entry) return null;

  if (!cacheEntryMatches(entry, sticker)) {
    await db.delete(STORE_NAME, sticker.id);
    return null;
  }

  return entry.blob;
}

export async function ensureStickerImageBlob(sticker: StickerResponse) {
  const cached = await getCachedStickerImageBlob(sticker);
  if (cached) return cached;

  const db = await getDb();
  if (!db) return null;

  const url = resolveMediaUrl(sticker.url);
  if (!url) return null;

  const response = await fetch(url);
  if (!response.ok) return null;

  const blob = await response.blob();
  await db.put(STORE_NAME, {
    id: sticker.id,
    sourceUrl: sticker.url,
    updatedAt: sticker.updated_at,
    blob,
  });

  return blob;
}

export async function pruneStickerImageCache(retainedStickerIds: number[]) {
  const db = await getDb();
  if (!db) return;

  const retainedIds = new Set(retainedStickerIds);
  const keys = await db.getAllKeys(STORE_NAME);

  await Promise.all(
    keys
      .filter((key): key is number => typeof key === "number" && !retainedIds.has(key))
      .map((key) => db.delete(STORE_NAME, key)),
  );
}

export async function clearStickerImageCache() {
  const db = await getDb();
  if (!db) return;

  await db.clear(STORE_NAME);
}
