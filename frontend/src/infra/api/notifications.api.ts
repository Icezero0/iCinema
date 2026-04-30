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
