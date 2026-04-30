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
    type: "media";
    alt: string;
    kind: "sticker" | "image";
    src?: string;
    assetId?: string;
    animated?: boolean;
  };

export type ChatMessage = {
  id: number | string;
  author: string;
  authorUserId?: number | null;
  avatarUrl?: string | null;
  segments: ChatSegment[];
  self?: boolean;
  avatarVariant?: "default" | "room";
  role?: RoomRole;
  status?: MemberStatus;
};
