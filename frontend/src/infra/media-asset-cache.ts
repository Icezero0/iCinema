import { openDB, type DBSchema } from "idb";
import { resolveMediaUrl } from "@/infra/media";

const DB_NAME = "icinema-media-cache";
const DB_VERSION = 1;
const STORE_NAME = "mediaBlobs";

type CachedMediaBlob = {
  key: string;
  sourceUrl: string;
  updatedAt: string;
  blob: Blob;
};

interface MediaAssetCacheDB extends DBSchema {
  mediaBlobs: {
    key: string;
    value: CachedMediaBlob;
  };
}

function canUseIndexedDB() {
  return typeof window !== "undefined" && "indexedDB" in window;
}

const dbPromise = canUseIndexedDB()
  ? openDB<MediaAssetCacheDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: "key" });
        }
      },
    })
  : null;

function cacheEntryMatches(entry: CachedMediaBlob, sourceUrl: string, updatedAt: string) {
  return entry.sourceUrl === sourceUrl && entry.updatedAt === updatedAt;
}

async function getDb() {
  return dbPromise;
}

export async function getCachedMediaBlob(
  key: string,
  sourceUrl: string,
  updatedAt = "",
) {
  const db = await getDb();
  if (!db) return null;

  const entry = await db.get(STORE_NAME, key);
  if (!entry) return null;

  if (!cacheEntryMatches(entry, sourceUrl, updatedAt)) {
    await db.delete(STORE_NAME, key);
    return null;
  }

  return entry.blob;
}

export async function ensureMediaBlobCached(
  key: string,
  sourceUrl: string | null | undefined,
  updatedAt = "",
) {
  if (!sourceUrl) return null;

  const cached = await getCachedMediaBlob(key, sourceUrl, updatedAt);
  if (cached) return cached;

  const db = await getDb();
  if (!db) return null;

  const url = resolveMediaUrl(sourceUrl);
  if (!url) return null;

  const response = await fetch(url);
  if (!response.ok) return null;

  const blob = await response.blob();
  await db.put(STORE_NAME, {
    key,
    sourceUrl,
    updatedAt,
    blob,
  });

  return blob;
}

export async function pruneMediaBlobCache(retainedKeys: string[]) {
  const db = await getDb();
  if (!db) return;

  const retained = new Set(retainedKeys);
  const keys = await db.getAllKeys(STORE_NAME);

  await Promise.all(
    keys
      .filter((key): key is string => typeof key === "string" && !retained.has(key))
      .map((key) => db.delete(STORE_NAME, key)),
  );
}

export async function clearMediaBlobCache() {
  const db = await getDb();
  if (!db) return;

  await db.clear(STORE_NAME);
}
