import { defineStore } from "pinia";
import {
  listNotifications,
  getUnreadCount,
  markNotificationAsRead,
  markAllNotificationsAsRead,
  type Notification,
} from "@/infra/api/notifications.api";
import {
  approveJoinRequestById,
  getJoinRequestById,
  rejectJoinRequestById,
} from "@/infra/api/join-requests.api";
import type { RoomJoinRequest } from "@/infra/api/rooms.api";

type State = {
  items: Notification[];
  total: number;
  unreadCount: number;

  page: number;
  pageSize: number;
  totalPages: number;

  isLoading: boolean;
  isLoadingMore: boolean;
  isSyncingUnreadCount: boolean;

  error: string | null;

  joinRequestsById: Record<number, RoomJoinRequest>;
};

export const useNotificationsStore = defineStore("notifications", {
  state: (): State => ({
    items: [],
    total: 0,
    unreadCount: 0,

    page: 1,
    pageSize: 20,
    totalPages: 0,

    isLoading: false,
    isLoadingMore: false,
    isSyncingUnreadCount: false,

    error: null,

    joinRequestsById: {},
  }),

  getters: {
    hasAny(state) {
      return state.total > 0;
    },
    hasMore(state) {
      return state.page < state.totalPages;
    },
  },

  actions: {
    async hydrateJoinRequests(notifications: Notification[]) {
      const ids = notifications
        .filter(
          (n) =>
            n.related_type === "room_join_request" &&
            n.related_id != null &&
            !this.joinRequestsById[n.related_id],
        )
        .map((n) => n.related_id!) as number[];

      if (ids.length === 0) return;

      await Promise.all(
        ids.map(async (requestId) => {
          try {
            const detail = await getJoinRequestById(requestId);
            this.joinRequestsById[requestId] = detail;
          } catch {
            // 单个 hydrate 失败不阻断整个列表
          }
        }),
      );
    },

    async refreshFirstPage(pageSize = 20) {
      return this.refreshPage({
        page: 1,
        pageSize,
      });
    },

    async refreshPage(params?: {
      page?: number;
      pageSize?: number;
      isRead?: boolean | null;
    }) {
      const nextPage = params?.page ?? 1;
      const nextPageSize = params?.pageSize ?? this.pageSize ?? 20;

      this.pageSize = nextPageSize;
      this.page = nextPage;
      this.isLoading = true;
      this.error = null;

      try {
        const data = await listNotifications({
          page: nextPage,
          page_size: nextPageSize,
          is_read: params?.isRead ?? null,
        });

        this.items = data.items;
        this.total = data.total;
        this.page = data.page;
        this.pageSize = data.page_size;
        this.totalPages = data.total_pages;

        await this.hydrateJoinRequests(data.items);
      } catch (e: any) {
        this.error = e?.message ?? "Failed to load notifications";
      } finally {
        this.isLoading = false;
      }
    },

    async loadMore() {
      if (this.isLoading || this.isLoadingMore) return;
      if (!this.hasMore) return;

      this.isLoadingMore = true;
      this.error = null;

      try {
        const nextPage = this.page + 1;

        const data = await listNotifications({
          page: nextPage,
          page_size: this.pageSize,
        });

        const existingIds = new Set(this.items.map((x) => x.id));
        const appended = data.items.filter((x) => !existingIds.has(x.id));

        this.items = [...this.items, ...appended];
        this.total = data.total;
        this.page = data.page;
        this.pageSize = data.page_size;
        this.totalPages = data.total_pages;

        await this.hydrateJoinRequests(appended);
      } catch (e: any) {
        this.error = e?.message ?? "Failed to load more notifications";
      } finally {
        this.isLoadingMore = false;
      }
    },

    async fetchUnreadCount() {
      this.isSyncingUnreadCount = true;
      this.error = null;

      try {
        const data = await getUnreadCount();
        this.unreadCount = data.unread_count;
      } catch (e: any) {
        this.error = e?.message ?? "Failed to load unread count";
      } finally {
        this.isSyncingUnreadCount = false;
      }
    },

    async markAsRead(notificationId: number) {
      this.error = null;

      try {
        const updated = await markNotificationAsRead(notificationId);

        const idx = this.items.findIndex((x) => x.id === notificationId);
        if (idx >= 0) {
          this.items[idx] = updated;
        }

        if (this.unreadCount > 0 && updated.is_read) {
          this.unreadCount -= 1;
        }
      } catch (e: any) {
        this.error = e?.message ?? "Failed to mark notification as read";
        throw e;
      }
    },

    async markAllAsRead() {
      this.error = null;

      try {
        await markAllNotificationsAsRead();
        this.items = this.items.map((item) => ({
          ...item,
          is_read: true,
        }));
        this.unreadCount = 0;
      } catch (e: any) {
        this.error = e?.message ?? "Failed to mark all notifications as read";
        throw e;
      }
    },

    async approveWorkflowNotification(notificationId: number) {
      this.error = null;

      const n = this.items.find((x) => x.id === notificationId);
      if (!n || n.related_type !== "room_join_request" || n.related_id == null) {
        throw new Error("Notification is not a join-request workflow item");
      }

      try {
        const detail = await approveJoinRequestById(n.related_id);
        this.joinRequestsById[n.related_id] = detail;

        const updated = await markNotificationAsRead(notificationId);
        const idx = this.items.findIndex((x) => x.id === notificationId);
        if (idx >= 0) {
          this.items[idx] = updated;
        }

        await this.fetchUnreadCount();
      } catch (e: any) {
        this.error = e?.message ?? "Failed to approve join request";
        throw e;
      }
    },

    async rejectWorkflowNotification(notificationId: number) {
      this.error = null;

      const n = this.items.find((x) => x.id === notificationId);
      if (!n || n.related_type !== "room_join_request" || n.related_id == null) {
        throw new Error("Notification is not a join-request workflow item");
      }

      try {
        const detail = await rejectJoinRequestById(n.related_id);
        this.joinRequestsById[n.related_id] = detail;

        const updated = await markNotificationAsRead(notificationId);
        const idx = this.items.findIndex((x) => x.id === notificationId);
        if (idx >= 0) {
          this.items[idx] = updated;
        }

        await this.fetchUnreadCount();
      } catch (e: any) {
        this.error = e?.message ?? "Failed to reject join request";
        throw e;
      }
    },

    clear() {
      this.items = [];
      this.total = 0;
      this.unreadCount = 0;

      this.page = 1;
      this.pageSize = 20;
      this.totalPages = 0;

      this.error = null;

      this.isLoading = false;
      this.isLoadingMore = false;
      this.isSyncingUnreadCount = false;

      this.joinRequestsById = {};
    },
  },
});
