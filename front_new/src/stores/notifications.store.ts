import { defineStore } from "pinia";
import {
  listNotifications,
  respondNotification,
  parseNotificationContent,
  type Notification,
} from "@/infra/api/notifications.api";

type State = {
  items: Notification[];
  total: number;
  isLoading: boolean;
  isLoadingMore: boolean;
  isSyncingTotal: boolean;
  error: string | null;
  hasMore: boolean;
  limit: number;
};

export const useNotificationsStore = defineStore("notifications", {
  state: (): State => ({
    items: [],
    total: 0,
    isLoading: false,
    isLoadingMore: false,
    isSyncingTotal: false,
    error: null,
    hasMore: true,
    limit: 20,
  }),

  getters: {
    hasAny(state) {
      return state.total > 0;
    },
  },

  actions: {
    /**
     * 首次进入页面加载
     */
    async refreshFirstPage(limit = 20) {
      this.limit = limit;
      this.isLoading = true;
      this.error = null;

      try {
        const data = await listNotifications({
          skip: 0,
          limit,
        });

        this.items = data.items;
        this.total = data.total;

        // 是否还有更多
        this.hasMore = data.items.length === limit;
      } catch (e: any) {
        this.error = e?.message ?? "Failed to load notifications";
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * 加载下一页（追加）
     */
    async loadMore() {
      if (this.isLoading || this.isLoadingMore) return;
      if (!this.hasMore) return;

      this.isLoadingMore = true;
      this.error = null;

      try {
        const skip = this.items.length;

        const data = await listNotifications({
          skip,
          limit: this.limit,
        });

        // 去重（保险）
        const existingIds = new Set(this.items.map((x) => x.id));
        const appended = data.items.filter((x) => !existingIds.has(x.id));

        this.items = [...this.items, ...appended];
        this.total = data.total;

        this.hasMore = data.items.length === this.limit;
      } catch (e: any) {
        this.error = e?.message ?? "Failed to load more notifications";
      } finally {
        this.isLoadingMore = false;
      }
    },

    async fetchTotal() {
      this.isSyncingTotal = true;
      this.error = null;

      try {
        const data = await listNotifications({ skip: 0, limit: 1 });
        this.total = data.total;
      } catch (e: any) {
        this.error = e?.message ?? "Failed to load notifications";
      } finally {
        this.isSyncingTotal = false;
      }
    },

    async respond(id: number, action: "accept" | "reject") {
      this.error = null;

      const n = this.items.find((x) => x.id === id);
      const parsed = n ? parseNotificationContent(n.content) : null;
      const token = parsed?.token;

      try {
        await respondNotification(id, { action, token });

        this.items = this.items.filter((x) => x.id !== id);
        await this.fetchTotal();

        // 删除后可能需要继续加载
        // 不在这里 loadMore，让页面 observer 决定
      } catch (e: any) {
        this.error = e?.message ?? "Failed to respond notification";
        throw e;
      }
    },

    clear() {
      this.items = [];
      this.total = 0;
      this.error = null;
      this.isLoading = false;
      this.isLoadingMore = false;
      this.isSyncingTotal = false;
      this.hasMore = true;
    },
  },
});
