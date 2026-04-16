import { http } from "@/infra/http/client";
import type {
  RoomJoinRequest,
  RoomJoinRequestListResponse,
  RoomJoinRequestStatus,
} from "@/infra/api/rooms.api";

export type RoomJoinRequestListScope =
  | "handled_by_me"
  | "created_by_me"
  | "all_related_to_me";

export async function listJoinRequests(params?: {
  page?: number;
  page_size?: number;
  status?: RoomJoinRequestStatus | null;
  room_id?: number | null;
  initiator_user_id?: number | null;
  target_user_id?: number | null;
  scope?: RoomJoinRequestListScope;
}) {
  const { data } = await http.get<RoomJoinRequestListResponse>(
    "/join-requests",
    { params },
  );
  return data;
}

export async function getJoinRequestById(requestId: number) {
  const { data } = await http.get<RoomJoinRequest>(`/join-requests/${requestId}`);
  return data;
}

export async function approveJoinRequestById(requestId: number) {
  const { data } = await http.post<RoomJoinRequest>(
    `/join-requests/${requestId}/approve`,
  );
  return data;
}

export async function rejectJoinRequestById(requestId: number) {
  const { data } = await http.post<RoomJoinRequest>(
    `/join-requests/${requestId}/reject`,
  );
  return data;
}
