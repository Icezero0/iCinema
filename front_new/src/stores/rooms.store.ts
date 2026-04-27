import { defineStore } from "pinia";
import { useAuthStore } from "@/stores/auth.store";
import { useEntitiesStore } from "@/stores/entities.store";
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
  submittingJoinRoomIds: number[];
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
    submittingJoinRoomIds: [],
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
    isJoinSubmitting: (state) => {
      return (roomId: number) => state.submittingJoinRoomIds.includes(roomId);
    },
  },

  actions: {
    async fetchHomeRooms() {
      this.isLoading = true;
      this.error = null;

      try {
        const entities = useEntitiesStore();
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

        entities.upsertRooms(this.myRooms);
        entities.upsertRooms(this.publicRooms);
        entities.upsertUsers(
          this.myRooms.map((room) => ({
            id: room.owner_id,
            username: room.owner_name ?? null,
            avatar_url: room.owner_avatar_url ?? null,
          })),
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
        const auth = useAuthStore();
        const entities = useEntitiesStore();
        const created = await createRoom(payload);
        const hydratedCreated: Room = {
          ...created,
          owner_name: auth.me?.username || auth.me?.email || created.owner_name || null,
          owner_avatar_url: auth.me?.avatar_url || created.owner_avatar_url || null,
          my_role: "owner",
        };
        this.myRooms = [
          hydratedCreated,
          ...this.myRooms.filter((x) => x.id !== hydratedCreated.id),
        ];
        if (hydratedCreated.visibility === "public") {
          this.publicRooms = this.publicRooms.filter(
            (x) => x.id !== hydratedCreated.id,
          );
        }

        entities.upsertRoom(hydratedCreated);
        if (auth.me?.id) {
          entities.upsertUser({
            id: auth.me.id,
            email: auth.me.email,
            username: auth.me.username,
            avatar_url: auth.me.avatar_url,
          });
        }

        return hydratedCreated;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to create room");
        this.error = message;
        throw new Error(message);
      } finally {
        this.isCreating = false;
      }
    },

    async requestToJoin(roomId: number) {
      if (
        this.pendingJoinRoomIds.includes(roomId) ||
        this.submittingJoinRoomIds.includes(roomId)
      ) {
        return;
      }

      this.error = null;
      this.submittingJoinRoomIds = [...this.submittingJoinRoomIds, roomId];

      try {
        await applyRoomJoinRequest(roomId);
        this.submittingJoinRoomIds = this.submittingJoinRoomIds.filter(
          (id) => id !== roomId,
        );
        if (!this.pendingJoinRoomIds.includes(roomId)) {
          this.pendingJoinRoomIds = [...this.pendingJoinRoomIds, roomId];
        }
      } catch (error: any) {
        const message = extractErrorMessage(
          error,
          "Failed to submit join request",
        );
        this.error = message;
        this.submittingJoinRoomIds = this.submittingJoinRoomIds.filter(
          (id) => id !== roomId,
        );
        throw new Error(message);
      }
    },

    clearError() {
      this.error = null;
    },
  },
});
