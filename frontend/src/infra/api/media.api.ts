import { http } from "@/infra/http/client";

export type MediaAssetUploadResponse = {
  id: number;
  asset_type: string;
  url: string;
  mime_type: string;
  file_size: number;
  status: string;
};

export type StickerResponse = {
  id: number;
  asset_type: string;
  mime_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  status: string;
  sort_order: number;
  url: string;
  created_at: string;
  updated_at: string;
};

export type StickerLibraryResponse = {
  items: StickerResponse[];
  total: number;
  all: boolean;
  page: number | null;
  page_size: number | null;
  total_pages: number | null;
};

export type PlatformEmojiAssetResponse = {
  type: number;
  name: string;
  path: string;
  url: string;
};

export type PlatformEmojiResponse = {
  provider: string;
  id: string;
  describe: string | null;
  assets: PlatformEmojiAssetResponse[];
};

export type PlatformEmojiListResponse = {
  items: PlatformEmojiResponse[];
};

export async function uploadImage(file: File) {
  const form = new FormData();
  form.append("file", file);

  const { data } = await http.post<MediaAssetUploadResponse>(
    "/media/images",
    form,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );

  return data;
}

export async function uploadSticker(file: File) {
  const form = new FormData();
  form.append("file", file);

  const { data } = await http.post<MediaAssetUploadResponse>(
    "/media/stickers",
    form,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    },
  );

  return data;
}

export async function getStickerLibrary(params?: {
  all?: boolean;
  page?: number | null;
  page_size?: number | null;
}) {
  const { data } = await http.get<StickerLibraryResponse>(
    "/media/stickers/library",
    { params },
  );

  return data;
}

export async function updateStickerLibrary(stickerIds: number[]) {
  const { data } = await http.patch<Record<string, string>>(
    "/media/stickers/library",
    {
      sticker_ids: stickerIds,
    },
  );

  return data;
}

export async function collectSticker(stickerId: number) {
  const { data } = await http.post<StickerResponse>(
    `/media/stickers/${stickerId}/collect`,
  );

  return data;
}

export async function collectImageAsSticker(imageId: number) {
  const { data } = await http.post<StickerResponse>(
    `/media/images/${imageId}/collect-as-sticker`,
  );

  return data;
}

export async function getPlatformEmojis() {
  const { data } = await http.get<PlatformEmojiListResponse>("/media/emojis");
  return data;
}

export async function getRecentPlatformEmojis(limit = 20) {
  const { data } = await http.get<PlatformEmojiListResponse>("/media/emojis/recent", {
    params: { limit },
  });

  return data;
}
