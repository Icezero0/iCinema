import { http } from "@/infra/http/client";
import type { UserResponse } from "@/infra/api/users.api";

export type TextSegmentIn = {
  type: "text";
  text: string;
};

export type EmojiSegmentIn = {
  type: "emoji";
  id: string;
};

export type ImageSegmentIn = {
  type: "image";
  id: number;
};

export type StickerSegmentIn = {
  type: "sticker";
  id: number;
};

export type MessageSegmentIn =
  | TextSegmentIn
  | EmojiSegmentIn
  | ImageSegmentIn
  | StickerSegmentIn;

export type MessageContentIn = {
  segments: MessageSegmentIn[];
};

export type TextSegmentOut = {
  type: "text";
  text: string;
};

export type EmojiSegmentOut = {
  type: "emoji";
  id: string;
};

export type ImageSegmentOut = {
  type: "image";
  id: number;
  url: string | null;
};

export type StickerSegmentOut = {
  type: "sticker";
  id: number;
  url: string | null;
};

export type MessageSegmentOut =
  | TextSegmentOut
  | EmojiSegmentOut
  | ImageSegmentOut
  | StickerSegmentOut;

export type MessageContentOut = {
  segments: MessageSegmentOut[];
};

export type MessageCreatePayload = {
  content: MessageContentIn;
};

export type MessageResponse = {
  id: number;
  room_id: number;
  sender_user_id: number | null;
  sender: UserResponse | null;
  content: MessageContentOut;
  created_at: string;
  updated_at: string;
};

export type MessageListResponse = {
  items: MessageResponse[];
  next_before_id?: number | null;
};

export async function getRoomMessages(
  roomId: number,
  params?: {
    before_id?: number | null;
    limit?: number;
  },
) {
  const { data } = await http.get<MessageListResponse>(
    `/rooms/${roomId}/messages`,
    { params },
  );
  return data;
}

export async function createRoomMessage(
  roomId: number,
  payload: MessageCreatePayload,
) {
  const { data } = await http.post<MessageResponse>(
    `/rooms/${roomId}/messages`,
    payload,
  );
  return data;
}
