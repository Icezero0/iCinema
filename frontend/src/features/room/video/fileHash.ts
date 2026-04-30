import { createSHA256 } from "hash-wasm";

export type FileHashProgress = {
  loaded: number;
  total: number;
  percent: number;
};

export type ComputeFileSha256Options = {
  chunkSize?: number;
  onProgress?: (progress: FileHashProgress) => void;
};

const DEFAULT_CHUNK_SIZE = 4 * 1024 * 1024;

function nextFrame() {
  return new Promise<void>((resolve) => {
    if (typeof window !== "undefined" && window.requestAnimationFrame) {
      window.requestAnimationFrame(() => resolve());
      return;
    }

    setTimeout(resolve, 0);
  });
}

function emitProgress(
  onProgress: ComputeFileSha256Options["onProgress"],
  loaded: number,
  total: number,
) {
  onProgress?.({
    loaded,
    total,
    percent: total > 0 ? Math.round((loaded / total) * 100) : 100,
  });
}

export async function computeFileSha256(
  file: File,
  options: ComputeFileSha256Options = {},
) {
  const chunkSize = options.chunkSize ?? DEFAULT_CHUNK_SIZE;
  const hasher = await createSHA256();
  let loaded = 0;

  hasher.init();
  emitProgress(options.onProgress, loaded, file.size);

  while (loaded < file.size) {
    const nextLoaded = Math.min(file.size, loaded + chunkSize);
    const buffer = await file.slice(loaded, nextLoaded).arrayBuffer();
    hasher.update(new Uint8Array(buffer));
    loaded = nextLoaded;
    emitProgress(options.onProgress, loaded, file.size);
    await nextFrame();
  }

  return hasher.digest("hex");
}
