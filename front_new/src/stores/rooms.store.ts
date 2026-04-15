import { defineStore } from "pinia";
import {
  applyRoomJoinRequest,
  createRoom,
  getMyRooms,
  getRooms,
  type Room,
  type RoomCreatePayload,
} from "@/infra/api/rooms.api";

type State = {
  myRooms: Room[];
  publicRooms: Room[];
  isLoading: boolean;
  isCreating: boolean;
  pendingJoinRoomIds: number[];
  error: string | null;
};

function extractErrorMessage(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (typeof error?.message === "string" && error.message) return error.message;

  return fallback;
}

export const useRoomsStore = defineStore("rooms", {
  state: (): State => ({
    myRooms: [],
    publicRooms: [],
    isLoading: false,
    isCreating: false,
    pendingJoinRoomIds: [],
    error: null,
  }),

  getters: {
    hasMyRooms(state) {
      return state.myRooms.length > 0;
    },
    hasPublicRooms(state) {
      return state.publicRooms.length > 0;
    },
    isJoinPending: (state) => {
      return (roomId: number) => state.pendingJoinRoomIds.includes(roomId);
    },
  },

  actions: {
    async fetchHomeRooms() {
      this.isLoading = true;
      this.error = null;

      try {
        const [myRoomsData, allRoomsData] = await Promise.all([
          getMyRooms({
            page: 1,
            page_size: 100,
          }),
          getRooms({
            page: 1,
            page_size: 100,
          }),
        ]);

        this.myRooms = myRoomsData.items;
        const myRoomIds = new Set(this.myRooms.map((room) => room.id));
        this.publicRooms = allRoomsData.items.filter(
          (room) => room.visibility === "public" && !myRoomIds.has(room.id),
        );
      } catch (error: any) {
        this.error = extractErrorMessage(error, "Failed to load rooms");
      } finally {
        this.isLoading = false;
      }
    },

    async createOwnedRoom(payload: RoomCreatePayload) {
      this.isCreating = true;
      this.error = null;

      try {
        const created = await createRoom(payload);
        this.myRooms = [created, ...this.myRooms.filter((x) => x.id !== created.id)];
        return created;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to create room");
        this.error = message;
        throw new Error(message);
      } finally {
        this.isCreating = false;
      }
    },

    async requestToJoin(roomId: number) {
      if (this.pendingJoinRoomIds.includes(roomId)) return;

      this.error = null;
      this.pendingJoinRoomIds = [...this.pendingJoinRoomIds, roomId];

      try {
        await applyRoomJoinRequest(roomId);
      } catch (error: any) {
        const message = extractErrorMessage(
          error,
          "Failed to submit join request",
        );
        this.error = message;
        this.pendingJoinRoomIds = this.pendingJoinRoomIds.filter((id) => id !== roomId);
        throw new Error(message);
      }
    },

    clearError() {
      this.error = null;
    },
  },
});
