import { defineStore } from "pinia";
import { getUserById, type UserResponse } from "@/infra/api/users.api";
import {
  getRoomById,
  type Room,
  type RoomBrief,
  type RoomJoinRequest,
  type RoomMember,
  type RoomUserBrief,
} from "@/infra/api/rooms.api";
import type { UserBrief as NotificationUserBrief } from "@/infra/api/notifications.api";

type EntityUser = {
  id: number;
  email?: string | null;
  username?: string | null;
  avatar_url?: string | null;
  auto_accept?: boolean | null;
};

type EntityRoom = {
  id: number;
  name?: string;
  owner_id?: number;
  owner_name?: string | null;
  owner_avatar_url?: string | null;
  visibility?: Room["visibility"];
  my_role?: Room["my_role"];
  join_audit_mode?: Room["join_audit_mode"];
};

type State = {
  usersById: Record<number, EntityUser>;
  roomsById: Record<number, EntityRoom>;
  loadingUsers: Record<number, boolean>;
  loadingRooms: Record<number, boolean>;
};

type UserSummaryInput =
  | UserResponse
  | RoomUserBrief
  | NotificationUserBrief
  | {
      id: number;
      email?: string | null;
      username?: string | null;
      avatar_url?: string | null;
    };
type RoomSummaryInput = Room | RoomBrief;

function mergeDefined<T extends Record<string, any>>(base: T | undefined, patch: Partial<T>): T {
  const next = { ...(base ?? {}) } as T;

  for (const [key, value] of Object.entries(patch)) {
    if (value !== undefined) {
      (next as any)[key] = value;
    }
  }

  return next;
}

function normalizeUser(user: UserSummaryInput): EntityUser {
  return {
    id: user.id,
    email: user.email,
    username: user.username,
    avatar_url: user.avatar_url,
    auto_accept: "auto_accept" in user ? user.auto_accept : undefined,
  };
}

function normalizeRoom(room: RoomSummaryInput): EntityRoom {
  return {
    id: room.id,
    name: room.name,
    owner_id: room.owner_id,
    visibility: room.visibility,
    owner_name: "owner_name" in room ? room.owner_name : undefined,
    owner_avatar_url: "owner_avatar_url" in room ? room.owner_avatar_url : undefined,
    my_role: "my_role" in room ? room.my_role : undefined,
    join_audit_mode:
      "join_audit_mode" in room ? room.join_audit_mode : undefined,
  };
}

export const useEntitiesStore = defineStore("entities", {
  state: (): State => ({
    usersById: {},
    roomsById: {},
    loadingUsers: {},
    loadingRooms: {},
  }),

  getters: {
    getUser: (state) => {
      return (userId: number | null | undefined) =>
        userId ? state.usersById[userId] ?? null : null;
    },
    getRoom: (state) => {
      return (roomId: number | null | undefined) =>
        roomId ? state.roomsById[roomId] ?? null : null;
    },
  },

  actions: {
    upsertUser(user: UserSummaryInput | null | undefined) {
      if (!user?.id) return;

      const normalized = normalizeUser(user);
      this.usersById[user.id] = mergeDefined(this.usersById[user.id], normalized);
    },

    upsertUsers(users: Array<UserSummaryInput | null | undefined>) {
      users.forEach((user) => this.upsertUser(user));
    },

    upsertRoom(room: RoomSummaryInput | null | undefined) {
      if (!room?.id) return;

      const normalized = normalizeRoom(room);
      this.roomsById[room.id] = mergeDefined(this.roomsById[room.id], normalized);
    },

    upsertRooms(rooms: Array<RoomSummaryInput | null | undefined>) {
      rooms.forEach((room) => this.upsertRoom(room));
    },

    upsertRoomMembers(members: Array<RoomMember | null | undefined>) {
      members.forEach((member) => {
        if (!member) return;
        this.upsertUser(member.user);
      });
    },

    upsertJoinRequests(requests: Array<RoomJoinRequest | null | undefined>) {
      requests.forEach((request) => {
        if (!request) return;
        this.upsertRoom(request.room);
        this.upsertUsers([
          request.initiator,
          request.target,
          request.room_action_by,
        ]);
      });
    },

    async ensureUsers(userIds: Array<number | null | undefined>) {
      const ids = Array.from(
        new Set(
          userIds.filter((value): value is number => typeof value === "number" && value > 0),
        ),
      );

      const toFetch = ids.filter(
        (id) => !this.usersById[id] && !this.loadingUsers[id],
      );

      if (toFetch.length === 0) return;

      await Promise.all(
        toFetch.map(async (id) => {
          this.loadingUsers[id] = true;

          try {
            const user = await getUserById(id);
            this.upsertUser(user);
          } finally {
            this.loadingUsers[id] = false;
          }
        }),
      );
    },

    async ensureRooms(roomIds: Array<number | null | undefined>) {
      const ids = Array.from(
        new Set(
          roomIds.filter((value): value is number => typeof value === "number" && value > 0),
        ),
      );

      const toFetch = ids.filter(
        (id) => !this.roomsById[id] && !this.loadingRooms[id],
      );

      if (toFetch.length === 0) return;

      await Promise.all(
        toFetch.map(async (id) => {
          this.loadingRooms[id] = true;

          try {
            const room = await getRoomById(id);
            this.upsertRoom(room);
          } finally {
            this.loadingRooms[id] = false;
          }
        }),
      );
    },

    clear() {
      this.usersById = {};
      this.roomsById = {};
      this.loadingUsers = {};
      this.loadingRooms = {};
    },
  },
});
