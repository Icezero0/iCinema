import { http } from "@/infra/http/client";
import type { UserBrief } from "@/infra/api/notifications.api";

export type FeedbackType = "bug" | "suggestion" | "experience" | "other";
export type FeedbackPage =
  | "home"
  | "room"
  | "public_rooms"
  | "join_requests"
  | "notifications"
  | "profile"
  | "contact"
  | "other";
export type FeedbackStatus = "open" | "reviewing" | "resolved" | "closed";

export type Feedback = {
  id: number;
  creator_id: number;
  handled_by_id: number | null;
  feedback_type: FeedbackType;
  page: FeedbackPage;
  title: string;
  description: string;
  status: FeedbackStatus;
  admin_note: string | null;
  handled_at: string | null;
  created_at: string;
  updated_at: string;
  creator?: UserBrief | null;
  handled_by?: UserBrief | null;
  screenshot_asset_ids: number[];
  screenshot_urls: string[];
};

export type FeedbackListResponse = {
  items: Feedback[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type CreateFeedbackPayload = {
  feedback_type: FeedbackType;
  page: FeedbackPage;
  title: string;
  description: string;
  screenshots?: File[];
};

export type UpdateFeedbackPayload = {
  status?: FeedbackStatus | null;
  admin_note?: string | null;
};

export async function createFeedback(payload: CreateFeedbackPayload) {
  const form = new FormData();
  form.append("feedback_type", payload.feedback_type);
  form.append("page", payload.page);
  form.append("title", payload.title);
  form.append("description", payload.description);

  for (const screenshot of payload.screenshots ?? []) {
    form.append("screenshots", screenshot);
  }

  const { data } = await http.post<Feedback>("/feedback", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listMyFeedback(params?: {
  page?: number;
  page_size?: number;
  status?: FeedbackStatus | null;
  feedback_type?: FeedbackType | null;
  feedback_page?: FeedbackPage | null;
}) {
  const { data } = await http.get<FeedbackListResponse>("/feedback", { params });
  return data;
}

export async function listAllFeedback(params?: {
  page?: number;
  page_size?: number;
  status?: FeedbackStatus | null;
  feedback_type?: FeedbackType | null;
  feedback_page?: FeedbackPage | null;
}) {
  const { data } = await http.get<FeedbackListResponse>("/feedback/admin", {
    params,
  });
  return data;
}

export async function updateFeedback(
  feedbackId: number,
  payload: UpdateFeedbackPayload,
) {
  const { data } = await http.patch<Feedback>(
    `/feedback/admin/${feedbackId}`,
    payload,
  );
  return data;
}

export async function getFeedbackScreenshotBlob(assetId: number) {
  const { data } = await http.get<Blob>(`/feedback/assets/${assetId}`, {
    responseType: "blob",
  });
  return data;
}
