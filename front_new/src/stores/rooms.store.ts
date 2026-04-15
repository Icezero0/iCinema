import { defineStore } from "pinia";
import {
  applyRoomJoinRequest,
  createRoom,
  getRoomMembers,
  getRooms,
  type Room,
  type RoomCreatePayload,
} from "@/infra/api/rooms.api";
import { useAuthStore } from "@/stores/auth.store";

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
      const auth = useAuthStore();
      const meId = auth.me?.id;

      this.isLoading = true;
      this.error = null;

      try {
        const data = await getRooms({
          page: 1,
          page_size: 100,
        });

        if (!meId) {
          this.myRooms = [];
          this.publicRooms = data.items.filter((room) => room.is_public);
          return;
        }

        const memberships = await Promise.all(
          data.items.map(async (room) => {
            try {
              const members = await getRoomMembers(room.id);
              return {
                room,
                isMember: members.items.some((item) => item.user_id === meId),
              };
            } catch {
              return {
                room,
                isMember: room.owner_id === meId,
              };
            }
          }),
        );

        this.myRooms = memberships
          .filter(({ room, isMember }) => room.owner_id === meId || isMember)
          .map(({ room }) => room);

        const myRoomIds = new Set(this.myRooms.map((room) => room.id));
        this.publicRooms = data.items.filter(
          (room) => room.is_public && !myRoomIds.has(room.id),
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
