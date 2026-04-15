import { http } from "@/infra/http/client";

export type Room = {
  id: number;
  name: string;
  owner_id: number;
  is_public: boolean | null;
  config: string | null;
};

export type RoomListResponse = {
  items: Room[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type RoomCreatePayload = {
  name: string;
  is_public?: boolean | null;
  config?: string | null;
};

export type RoomPatchPayload = {
  name?: string | null;
  is_public?: boolean | null;
  config?: string | null;
};

export type RoomRole = "owner" | "manager" | "member";

export type RoomUserBrief = {
  id: number;
  email: string;
  username: string | null;
  avatar_url: string | null;
};

export type RoomMember = {
  room_id: number;
  user_id: number;
  joined_at: string | null;
  role: RoomRole;
  user: RoomUserBrief | null;
};

export type RoomMemberListResponse = {
  items: RoomMember[];
  total: number;
};

export type RoomJoinRequestSource = "apply" | "invite" | "member_invite";
export type RoomJoinRequestStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "cancelled";
export type RoomJoinRequestAction = "pending" | "approved" | "rejected";

export type RoomJoinRequest = {
  id: number;
  room_id: number;
  initiator_user_id: number;
  target_user_id: number;
  source: RoomJoinRequestSource;
  status: RoomJoinRequestStatus;
  room_action: RoomJoinRequestAction;
  target_action: RoomJoinRequestAction;
  room_action_by_user_id: number | null;
  created_at: string | null;
  updated_at: string | null;
  initiator: RoomUserBrief | null;
  target: RoomUserBrief | null;
  room_action_by: RoomUserBrief | null;
};

export type RoomJoinRequestListResponse = {
  items: RoomJoinRequest[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type RoomVideoSourceType = "external_url" | "local_file";
export type RoomSyncPolicy = "auto_sync" | "disabled";
export type RoomActiveSyncPermission =
  | "owner_only"
  | "owner_and_manager"
  | "all_members";

export type RoomSettings = {
  room_id: number;
  selected_room_video_source_type: RoomVideoSourceType;
  sync_policy: RoomSyncPolicy;
  active_sync_permission: RoomActiveSyncPermission;
};

export type RoomSettingsPatchPayload = {
  selected_room_video_source_type?: RoomVideoSourceType | null;
  sync_policy?: RoomSyncPolicy | null;
  active_sync_permission?: RoomActiveSyncPermission | null;
};

export async function getRooms(params?: {
  page?: number;
  page_size?: number;
  name?: string | null;
}) {
  const { data } = await http.get<RoomListResponse>("/rooms", { params });
  return data;
}

export async function createRoom(payload: RoomCreatePayload) {
  const { data } = await http.post<Room>("/rooms", payload);
  return data;
}

export async function getRoomById(roomId: number) {
  const { data } = await http.get<Room>(`/rooms/${roomId}`);
  return data;
}

export async function patchRoom(roomId: number, payload: RoomPatchPayload) {
  const { data } = await http.patch<Room>(`/rooms/${roomId}`, payload);
  return data;
}

export async function deleteRoom(roomId: number) {
  await http.delete(`/rooms/${roomId}`);
}

export async function getRoomMembers(roomId: number) {
  const { data } = await http.get<RoomMemberListResponse>(
    `/rooms/${roomId}/members`,
  );
  return data;
}

export async function getRoomJoinRequests(
  roomId: number,
  params?: {
    page?: number;
    page_size?: number;
    status?: RoomJoinRequestStatus | null;
    source?: RoomJoinRequestSource | null;
  },
) {
  const { data } = await http.get<RoomJoinRequestListResponse>(
    `/rooms/${roomId}/join-requests`,
    { params },
  );
  return data;
}

export async function applyRoomJoinRequest(roomId: number) {
  await http.post(`/rooms/${roomId}/join-requests/apply`);
}

export async function inviteRoomJoinRequest(
  roomId: number,
  payload: { target_user_id: number },
) {
  await http.post(`/rooms/${roomId}/join-requests/invite`, payload);
}

export async function removeRoomMember(roomId: number, targetUserId: number) {
  await http.delete(`/rooms/${roomId}/members/${targetUserId}`);
}

export async function getRoomSettings(roomId: number) {
  const { data } = await http.get<RoomSettings>(`/rooms/${roomId}/settings`);
  return data;
}

export async function patchRoomSettings(
  roomId: number,
  payload: RoomSettingsPatchPayload,
) {
  const { data } = await http.patch<RoomSettings>(
    `/rooms/${roomId}/settings`,
    payload,
  );
  return data;
}
