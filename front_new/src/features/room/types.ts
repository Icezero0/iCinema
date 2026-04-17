export type RoomPanelKey = "chat" | "members" | "requests" | "settings";
export type RoomRole = "owner" | "manager" | "member";
export type MemberStatus = "playing" | "paused" | "buffering" | "offline" | "error";

export type RoomRequestMockItem = {
  id: number;
  user: string;
  time: string;
  note: string;
};
