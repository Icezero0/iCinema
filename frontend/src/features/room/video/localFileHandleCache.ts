import { openDB, type DBSchema } from "idb";

const DB_NAME = "icinema-local-file-cache";
const DB_VERSION = 1;
const STORE_NAME = "roomLocalFiles";

export type LocalFileHandle = {
  name: string;
  kind?: string;
  getFile: () => Promise<File>;
  queryPermission?: (descriptor: { mode: "read" }) => Promise<PermissionState>;
  requestPermission?: (descriptor: { mode: "read" }) => Promise<PermissionState>;
};

export type LocalFileSelection = {
  file: File;
  handle?: LocalFileHandle | null;
};

type CachedRoomLocalFile = {
  key: string;
  roomId: number;
  fileHash: string;
  fileName: string;
  fileSize: number;
  fileLastModified: number;
  cachedAt: string;
  handle: LocalFileHandle;
};

interface LocalFileCacheDB extends DBSchema {
  roomLocalFiles: {
    key: string;
    value: CachedRoomLocalFile;
  };
}

const videoPickerTypes = [
  {
    description: "Video files",
    accept: {
      "video/*": [".mp4", ".m4v", ".webm", ".ogg", ".ogv", ".mov"],
    },
  },
];

function canUseIndexedDB() {
  return typeof window !== "undefined" && "indexedDB" in window;
}

function cacheKey(roomId: number) {
  return `room:${roomId}`;
}

const dbPromise = canUseIndexedDB()
  ? openDB<LocalFileCacheDB>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: "key" });
        }
      },
    })
  : null;

async function getDb() {
  return dbPromise;
}

async function ensureReadPermission(handle: LocalFileHandle) {
  const descriptor = { mode: "read" as const };
  const current = await handle.queryPermission?.(descriptor);
  if (current === "granted" || !handle.requestPermission) return current !== "denied";

  const requested = await handle.requestPermission(descriptor);
  return requested === "granted";
}

function fileMatchesCache(file: File, entry: CachedRoomLocalFile) {
  return (
    file.name === entry.fileName &&
    file.size === entry.fileSize &&
    file.lastModified === entry.fileLastModified
  );
}

export function canUseFileSystemAccessPicker() {
  return (
    typeof window !== "undefined" &&
    typeof (window as unknown as { showOpenFilePicker?: unknown }).showOpenFilePicker === "function"
  );
}

export async function pickLocalVideoFileWithHandle() {
  if (!canUseFileSystemAccessPicker()) return null;

  const picker = (window as unknown as {
    showOpenFilePicker: (options?: {
      multiple?: boolean;
      types?: typeof videoPickerTypes;
      excludeAcceptAllOption?: boolean;
    }) => Promise<LocalFileHandle[]>;
  }).showOpenFilePicker;

  const handles = await picker({
    multiple: false,
    types: videoPickerTypes,
    excludeAcceptAllOption: false,
  });
  const handle = handles[0];
  if (!handle) return null;

  const file = await handle.getFile();
  return { file, handle } satisfies LocalFileSelection;
}

export async function cacheRoomLocalFileHandle(options: {
  roomId: number;
  fileHash: string;
  file: File;
  handle?: LocalFileHandle | null;
}) {
  if (!options.handle) return;

  const db = await getDb();
  if (!db) return;

  await db.put(STORE_NAME, {
    key: cacheKey(options.roomId),
    roomId: options.roomId,
    fileHash: options.fileHash,
    fileName: options.file.name,
    fileSize: options.file.size,
    fileLastModified: options.file.lastModified,
    cachedAt: new Date().toISOString(),
    handle: options.handle,
  });
}

export async function getCachedRoomLocalFile(roomId: number, fileHash: string) {
  const db = await getDb();
  if (!db) return null;

  const key = cacheKey(roomId);
  const entry = await db.get(STORE_NAME, key);
  if (!entry) return null;

  if (entry.fileHash !== fileHash) {
    await db.delete(STORE_NAME, key);
    return null;
  }

  try {
    const allowed = await ensureReadPermission(entry.handle);
    if (!allowed) {
      await db.delete(STORE_NAME, key);
      return null;
    }

    const file = await entry.handle.getFile();
    if (!fileMatchesCache(file, entry)) {
      await db.delete(STORE_NAME, key);
      return null;
    }

    return { file, handle: entry.handle } satisfies LocalFileSelection;
  } catch {
    await db.delete(STORE_NAME, key);
    return null;
  }
}

export async function clearCachedRoomLocalFile(roomId: number) {
  const db = await getDb();
  if (!db) return;

  await db.delete(STORE_NAME, cacheKey(roomId));
}
