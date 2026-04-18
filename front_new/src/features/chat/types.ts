import type { MemberStatus, RoomRole } from "@/features/room/types";

export type ChatSegment =
  | { id: number | string; type: "text"; content: string }
  | {
    id: number | string;
    type: "emoji";
    emojiId: string;
    animated?: boolean;
  }
  | {
    id: number | string;
    type: "image";
    alt: string;
    src?: string;
    kind?: "sticker" | "image";
    assetId?: string;
    animated?: boolean;
  };

export type ChatMessage = {
  id: number | string;
  author: string;
  segments: ChatSegment[];
  self?: boolean;
  avatarVariant?: "default" | "room";
  role?: RoomRole;
  status?: MemberStatus | "idle";
};
