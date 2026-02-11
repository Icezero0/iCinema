import { http } from "@/infra/http/client";

/**
 * 后端返回的 Notification 结构
 */
export type Notification = {
  id: number;
  content: string; // JSON string
  recipient_id: number;
  sender_id: number | null;
  status: string; // "pending"
  created_at: string;
  is_deleted: boolean;
};

export type NotificationListResponse = {
  items: Notification[];
  total: number;
};

/**
 * GET /notifications
 * 默认就是 pending + 未删除
 */
export async function listNotifications(params?: {
  skip?: number;
  limit?: number;
}) {
  const { data } = await http.get<NotificationListResponse>(
    "/notifications",
    {
      params,
    },
  );
  return data;
}

/**
 * POST /notifications/{notification_id}/respond
 */
export type NotificationRespondBody = {
  action: "accept" | "reject";
  token?: string;
};

export async function respondNotification(
  notificationId: number,
  body: NotificationRespondBody,
) {
  const { data } = await http.post(
    `/notifications/${notificationId}/respond`,
    body,
  );
  return data;
}

/**
 * 工具函数：解析 content JSON
 */
export function parseNotificationContent(
  content: string,
): {
  room_id?: number;
  user_id?: number;
  type?: string;
  token?: string;
} | null {
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
}
