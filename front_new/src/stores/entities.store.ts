import { defineStore } from "pinia";
import { getUserById, type UserResponse } from "@/infra/api/users.api";
import { getRoomById, type Room } from "@/infra/api/rooms.api";

type State = {
  usersById: Record<number, UserResponse>;
  roomsById: Record<number, Room>;
  loadingUsers: Record<number, boolean>;
  loadingRooms: Record<number, boolean>;
};

export const useEntitiesStore = defineStore("entities", {
  state: (): State => ({
    usersById: {},
    roomsById: {},
    loadingUsers: {},
    loadingRooms: {},
  }),

  actions: {
    async ensureUsers(userIds: Array<number | null | undefined>) {
      const ids = Array.from(
        new Set(userIds.filter((v): v is number => typeof v === "number" && v > 0)),
      );

      const toFetch = ids.filter(
        (id) => !this.usersById[id] && !this.loadingUsers[id],
      );
      if (toFetch.length === 0) return;

      await Promise.all(
        toFetch.map(async (id) => {
          this.loadingUsers[id] = true;
          try {
            const u = await getUserById(id);
            this.usersById[id] = u;
          } finally {
            this.loadingUsers[id] = false;
          }
        }),
      );
    },

    async ensureRooms(roomIds: Array<number | null | undefined>) {
      const ids = Array.from(
        new Set(roomIds.filter((v): v is number => typeof v === "number" && v > 0)),
      );

      const toFetch = ids.filter(
        (id) => !this.roomsById[id] && !this.loadingRooms[id],
      );
      if (toFetch.length === 0) return;

      await Promise.all(
        toFetch.map(async (id) => {
          this.loadingRooms[id] = true;
          try {
            const r = await getRoomById(id);
            this.roomsById[id] = r;
          } finally {
            this.loadingRooms[id] = false;
          }
        }),
      );
    },
  },
});