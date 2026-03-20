import { http } from "@/infra/http/client";

export type NotificationType = "system" | "workflow";
export type RelatedType = "room_join_request" | "announcement" | null;

export type UserBrief = {
  id: number;
  email: string;
  username: string | null;
  avatar_url: string | null;
};

export type Notification = {
  id: number;
  recipient_user_id: number;
  actor_user_id: number | null;
  notification_type: NotificationType;
  related_type: RelatedType;
  related_id: number | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  actor?: UserBrief | null;
};

export type NotificationListResponse = {
  items: Notification[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type NotificationUnreadCountResponse = {
  unread_count: number;
};

export type RoomJoinRequestSource = "apply" | "invite" | "member_invite";
export type RoomJoinRequestStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "cancelled";
export type RoomJoinRequestAction = "pending" | "approved" | "rejected";

export type RoomJoinRequestResponse = {
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

  initiator: UserBrief | null;
  target: UserBrief | null;
  room_action_by: UserBrief | null;
};

export async function listNotifications(params?: {
  page?: number;
  page_size?: number;
  is_read?: boolean | null;
  notification_type?: NotificationType | null;
}) {
  const { data } = await http.get<NotificationListResponse>("/notifications", {
    params,
  });
  return data;
}

export async function getUnreadCount() {
  const { data } = await http.get<NotificationUnreadCountResponse>(
    "/notifications/unread-count",
  );
  return data;
}

export async function markNotificationAsRead(notificationId: number) {
  const { data } = await http.post<Notification>(
    `/notifications/${notificationId}/read`,
  );
  return data;
}

export async function markAllNotificationsAsRead() {
  await http.post("/notifications/read-all");
}

export async function getJoinRequest(requestId: number) {
  const { data } = await http.get<RoomJoinRequestResponse>(
    `/join-requests/${requestId}`,
  );
  return data;
}

export async function approveJoinRequest(requestId: number) {
  const { data } = await http.post<RoomJoinRequestResponse>(
    `/join-requests/${requestId}/approve`,
  );
  return data;
}

export async function rejectJoinRequest(requestId: number) {
  const { data } = await http.post<RoomJoinRequestResponse>(
    `/join-requests/${requestId}/reject`,
  );
  return data;
}