import { defineStore } from "pinia";
import { getUserById, type UserResponse } from "@/infra/api/users.api";
import {
  getRoomById,
  type Room,
  type RoomBrief,
  type RoomJoinRequest,
  type RoomMember,
  type RoomSettings,
  type RoomUserBrief,
} from "@/infra/api/rooms.api";
import type { UserBrief as NotificationUserBrief } from "@/infra/api/notifications.api";
import {
  readPersistedState,
  writePersistedState,
} from "@/stores/persistence";

export type LocalRoomSyncStrategy =
  | "adaptive-speed"
  | "auto-seek"
  | "manual-sync";

export const DEFAULT_LOCAL_ROOM_SYNC_STRATEGY: LocalRoomSyncStrategy = "adaptive-speed";
export const DEFAULT_LOCAL_ROOM_VOLUME = 50;

function isLocalRoomSyncStrategy(value: unknown): value is LocalRoomSyncStrategy {
  return (
    value === "adaptive-speed" ||
    value === "auto-seek" ||
    value === "manual-sync"
  );
}

function roomLocalSyncStrategyStorageKey(roomId: number) {
  return `icinema:room:${roomId}:localSyncStrategy`;
}

function roomLocalVolumeStorageKey(roomId: number) {
  return `icinema:room:${roomId}:volume`;
}

function normalizeLocalRoomVolume(value: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return DEFAULT_LOCAL_ROOM_VOLUME;
  }

  return Math.min(100, Math.max(0, Math.round(value)));
}

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
  selected_room_video_source_type?: RoomSettings["selected_room_video_source_type"];
  sync_policy?: RoomSettings["sync_policy"];
  active_sync_permission?: RoomSettings["active_sync_permission"];
  local_sync_strategy?: LocalRoomSyncStrategy;
  local_volume?: number;
};

type EntityRoomMember = {
  room_id: number;
  user_id: number;
  joined_at?: string | null;
  role: RoomMember["role"];
};

type State = {
  usersById: Record<number, EntityUser>;
  roomsById: Record<number, EntityRoom>;
  roomMembersByRoomId: Record<number, EntityRoomMember[]>;
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

function normalizeRoomMember(member: RoomMember): EntityRoomMember {
  return {
    room_id: member.room_id,
    user_id: member.user_id,
    joined_at: member.joined_at,
    role: member.role,
  };
}

export const useEntitiesStore = defineStore("entities", {
  state: (): State => ({
    usersById: {},
    roomsById: {},
    roomMembersByRoomId: {},
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
    getRoomMembers: (state) => {
      return (roomId: number | null | undefined) =>
        roomId ? state.roomMembersByRoomId[roomId] ?? [] : [];
    },
    getRoomMember: (state) => {
      return (roomId: number | null | undefined, userId: number | null | undefined) => {
        if (!roomId || !userId) return null;
        return state.roomMembersByRoomId[roomId]?.find((member) => member.user_id === userId) ?? null;
      };
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

    upsertRoomSettings(settings: RoomSettings | null | undefined) {
      if (!settings?.room_id) return;

      this.roomsById[settings.room_id] = mergeDefined(this.roomsById[settings.room_id], {
        id: settings.room_id,
        selected_room_video_source_type: settings.selected_room_video_source_type,
        sync_policy: settings.sync_policy,
        active_sync_permission: settings.active_sync_permission,
      });
    },

    setRoomLocalSyncStrategy(roomId: number, strategy: LocalRoomSyncStrategy) {
      if (!roomId) return;

      this.roomsById[roomId] = mergeDefined(this.roomsById[roomId], {
        id: roomId,
        local_sync_strategy: strategy,
      });
      writePersistedState(roomLocalSyncStrategyStorageKey(roomId), strategy);
    },

    loadRoomLocalSyncStrategy(roomId: number) {
      if (!roomId) return DEFAULT_LOCAL_ROOM_SYNC_STRATEGY;

      const persisted = readPersistedState<unknown>(
        roomLocalSyncStrategyStorageKey(roomId),
        DEFAULT_LOCAL_ROOM_SYNC_STRATEGY,
      );
      const strategy = isLocalRoomSyncStrategy(persisted)
        ? persisted
        : DEFAULT_LOCAL_ROOM_SYNC_STRATEGY;

      this.roomsById[roomId] = mergeDefined(this.roomsById[roomId], {
        id: roomId,
        local_sync_strategy: strategy,
      });

      return strategy;
    },

    setRoomLocalVolume(roomId: number, volume: number) {
      const normalizedVolume = normalizeLocalRoomVolume(volume);
      if (!roomId) return normalizedVolume;

      this.roomsById[roomId] = mergeDefined(this.roomsById[roomId], {
        id: roomId,
        local_volume: normalizedVolume,
      });
      writePersistedState(roomLocalVolumeStorageKey(roomId), normalizedVolume);

      return normalizedVolume;
    },

    loadRoomLocalVolume(roomId: number) {
      if (!roomId) return DEFAULT_LOCAL_ROOM_VOLUME;

      const persisted = readPersistedState<unknown>(
        roomLocalVolumeStorageKey(roomId),
        DEFAULT_LOCAL_ROOM_VOLUME,
      );
      const volume = normalizeLocalRoomVolume(persisted);

      this.roomsById[roomId] = mergeDefined(this.roomsById[roomId], {
        id: roomId,
        local_volume: volume,
      });

      return volume;
    },

    upsertRoomMembers(members: Array<RoomMember | null | undefined>) {
      const groupedMembers: Record<number, EntityRoomMember[]> = {};

      members.forEach((member) => {
        if (!member) return;
        this.upsertUser(member.user);
        const roomMembers = groupedMembers[member.room_id] ?? [];
        groupedMembers[member.room_id] = roomMembers;
        roomMembers.push(normalizeRoomMember(member));
      });

      Object.entries(groupedMembers).forEach(([roomId, roomMembers]) => {
        const numericRoomId = Number(roomId);
        this.roomMembersByRoomId[numericRoomId] = roomMembers;
      });
    },

    upsertRoomMember(member: RoomMember | null | undefined) {
      if (!member) return;

      this.upsertUser(member.user);

      const existingMembers = this.roomMembersByRoomId[member.room_id] ?? [];
      const nextMember = normalizeRoomMember(member);
      const existingIndex = existingMembers.findIndex(
        (item) => item.user_id === member.user_id,
      );

      if (existingIndex === -1) {
        this.roomMembersByRoomId[member.room_id] = [...existingMembers, nextMember];
        return;
      }

      this.roomMembersByRoomId[member.room_id] = existingMembers.map((item, index) =>
        index === existingIndex ? nextMember : item,
      );
    },

    removeRoomMember(roomId: number, userId: number) {
      const roomMembers = this.roomMembersByRoomId[roomId];
      if (!roomMembers) return;

      this.roomMembersByRoomId[roomId] = roomMembers.filter(
        (member) => member.user_id !== userId,
      );
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
      this.roomMembersByRoomId = {};
      this.loadingUsers = {};
      this.loadingRooms = {};
    },
  },
});
