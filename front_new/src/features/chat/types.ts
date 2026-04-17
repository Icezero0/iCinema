import type { MemberStatus, RoomRole } from "@/features/room/types";

export type ChatSection =
  | { id: number | string; type: "text"; content: string }
  | { id: number | string; type: "image"; alt: string };

export type ChatMessage = {
  id: number | string;
  author: string;
  sections: ChatSection[];
  self?: boolean;
  avatarVariant?: "default" | "room";
  role?: RoomRole;
  status?: MemberStatus | "idle";
};
