import { defineStore } from "pinia";
import {
  createRoomMessage,
  getRoomMessages,
  type MessageContentIn,
  type MessageResponse,
  type MessageSegmentIn,
} from "@/infra/api/messages.api";
import type { ChatMessage, ChatSegment } from "@/features/chat/types";
import {
  stripChatTextCursorAnchors,
  trimTrailingInvisibleTextSegments,
} from "@/features/chat/segments";
import { useAuthStore } from "@/stores/auth.store";
import { useEntitiesStore } from "@/stores/entities.store";
import { useAssetsStore } from "@/stores/assets.store";
import { resolveMediaUrl } from "@/infra/media";

type RoomMessagesState = {
  items: MessageResponse[];
  nextBeforeId: number | null;
  hasLoaded: boolean;
  isLoading: boolean;
  isLoadingHistory: boolean;
  isSending: boolean;
  error: string | null;
};

type State = {
  rooms: Record<number, RoomMessagesState>;
};

function createEmptyRoomState(): RoomMessagesState {
  return {
    items: [],
    nextBeforeId: null,
    hasLoaded: false,
    isLoading: false,
    isLoadingHistory: false,
    isSending: false,
    error: null,
  };
}

function extractErrorMessage(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (typeof error?.message === "string" && error.message) return error.message;

  return fallback;
}

function normalizeMessages(messages: MessageResponse[]) {
  const map = new Map<number, MessageResponse>();

  messages.forEach((message) => {
    map.set(message.id, message);
  });

  return Array.from(map.values()).sort((a, b) => a.id - b.id);
}

function mergeMessages(
  existing: MessageResponse[],
  incoming: MessageResponse[],
  mode: "replace" | "append" | "prepend",
) {
  if (mode === "replace") {
    return normalizeMessages(incoming);
  }

  if (mode === "append") {
    return normalizeMessages([...existing, ...incoming]);
  }

  return normalizeMessages([...incoming, ...existing]);
}

function parseAssetId(assetId: string | undefined) {
  if (!assetId) return null;

  const parsed = Number(assetId);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function slugifyFilenamePart(value: string | undefined, fallback: string) {
  const normalized = (value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

  return normalized || fallback;
}

function inferFileExtension(mimeType: string | undefined, fallback: string) {
  if (!mimeType) return fallback;

  if (mimeType === "image/jpeg") return "jpg";
  if (mimeType === "image/png") return "png";
  if (mimeType === "image/gif") return "gif";
  if (mimeType === "image/webp") return "webp";
  if (mimeType === "image/svg+xml") return "svg";

  const [, subtype] = mimeType.split("/");
  return subtype || fallback;
}

function sniffImageMimeType(bytes: Uint8Array) {
  if (bytes.length >= 6) {
    const header = String.fromCharCode(...bytes.slice(0, 6));
    if (header === "GIF87a" || header === "GIF89a") {
      return "image/gif";
    }
  }

  if (
    bytes.length >= 8 &&
    bytes[0] === 0x89 &&
    bytes[1] === 0x50 &&
    bytes[2] === 0x4e &&
    bytes[3] === 0x47 &&
    bytes[4] === 0x0d &&
    bytes[5] === 0x0a &&
    bytes[6] === 0x1a &&
    bytes[7] === 0x0a
  ) {
    return "image/png";
  }

  if (
    bytes.length >= 3 &&
    bytes[0] === 0xff &&
    bytes[1] === 0xd8 &&
    bytes[2] === 0xff
  ) {
    return "image/jpeg";
  }

  if (
    bytes.length >= 12 &&
    String.fromCharCode(...bytes.slice(0, 4)) === "RIFF" &&
    String.fromCharCode(...bytes.slice(8, 12)) === "WEBP"
  ) {
    return "image/webp";
  }

  return null;
}

async function createUploadFileFromSegment(
  segment: Extract<ChatSegment, { type: "media" }>,
) {
  if (!segment.src) {
    throw new Error("Media segment is missing source data");
  }

  const response = await fetch(segment.src);
  if (!response.ok) {
    throw new Error("Failed to read media content before upload");
  }

  const blob = await response.blob();
  const bytes = new Uint8Array(await blob.arrayBuffer());
  const actualMimeType = sniffImageMimeType(bytes) ?? blob.type;
  const extension = inferFileExtension(
    actualMimeType,
    segment.kind === "sticker" ? "webp" : "png",
  );
  const basename = slugifyFilenamePart(
    segment.alt,
    segment.kind === "sticker" ? "sticker" : "image",
  );

  return new File([bytes], `${basename}.${extension}`, {
    type: actualMimeType || undefined,
  });
}

async function prepareSegmentsForSend(
  segments: ChatSegment[],
  assets: ReturnType<typeof useAssetsStore>,
) {
  const resolvedSegments = await Promise.all(segments.map(async (segment) => {
    if (segment.type !== "media") {
      return segment;
    }

    if (parseAssetId(segment.assetId)) {
      return segment;
    }

    const uploadFile = await createUploadFileFromSegment(segment);
    const uploaded = segment.kind === "sticker"
      ? await assets.uploadSticker(uploadFile)
      : await assets.uploadImage(uploadFile);

    const resolvedSegment = {
      ...segment,
      assetId: String(uploaded.id),
      src: resolveMediaUrl(uploaded.url) || segment.src,
    } satisfies ChatSegment;

    Object.assign(segment, resolvedSegment);
    return resolvedSegment;
  }));

  return resolvedSegments;
}

function mapChatSegmentsToMessageSegments(segments: ChatSegment[]) {
  const result: MessageSegmentIn[] = [];
  const normalizedSegments = trimTrailingInvisibleTextSegments([...segments]);

  normalizedSegments.forEach((segment) => {
    if (segment.type === "text") {
      const text = stripChatTextCursorAnchors(segment.content);
      if (!text) return;
      result.push({
        type: "text",
        text,
      });
      return;
    }

    if (segment.type === "emoji") {
      result.push({
        type: "emoji",
        id: segment.emojiId,
      });
      return;
    }

    const assetId = parseAssetId(segment.assetId);
    if (!assetId) {
      return;
    }

    if (segment.kind === "sticker") {
      result.push({
        type: "sticker",
        id: assetId,
      });
      return;
    }

    result.push({
      type: "image",
      id: assetId,
    });
  });

  return result;
}

function mapMessageToChatMessage(
  message: MessageResponse,
  currentUserId: number | null | undefined,
  roomMemberRole: ChatMessage["role"],
  avatarUrl: string | null,
  getMediaDisplayUrl: (kind: "image" | "sticker", id: number, fallbackUrl: string | null) => string | undefined,
): ChatMessage {
  const author =
    message.sender?.username ||
    message.sender?.email ||
    (message.sender_user_id ? `User #${message.sender_user_id}` : "System");

  return {
    id: message.id,
    author,
    authorUserId: message.sender_user_id,
    avatarUrl,
    self:
      typeof currentUserId === "number" &&
      currentUserId > 0 &&
      message.sender_user_id === currentUserId,
    avatarVariant: "room",
    role: roomMemberRole,
    status: "idle",
    segments: message.content.segments.map((segment, index) => {
      if (segment.type === "text") {
        return {
          id: `${message.id}-${index}`,
          type: "text",
          content: segment.text,
        } satisfies ChatSegment;
      }

      if (segment.type === "emoji") {
        return {
          id: `${message.id}-${index}`,
          type: "emoji",
          emojiId: segment.id,
        } satisfies ChatSegment;
      }

      return {
        id: `${message.id}-${index}`,
        type: "media",
        alt: segment.type === "sticker" ? "Sticker" : "Image",
        src: getMediaDisplayUrl(segment.type, segment.id, segment.url),
        kind: segment.type === "sticker" ? "sticker" : "image",
        assetId: String(segment.id),
      } satisfies ChatSegment;
    }),
  };
}

export const useMessagesStore = defineStore("messages", {
  state: (): State => ({
    rooms: {},
  }),

  getters: {
    getRoomState: (state) => {
      return (roomId: number | null | undefined) =>
        typeof roomId === "number" && roomId > 0
          ? state.rooms[roomId] ?? createEmptyRoomState()
          : createEmptyRoomState();
    },
    getRoomMessages: (state) => {
      return (roomId: number | null | undefined) =>
        typeof roomId === "number" && roomId > 0
          ? state.rooms[roomId]?.items ?? []
          : [];
    },
    getRoomChatMessages: (state) => {
      return (roomId: number | null | undefined) => {
        if (typeof roomId !== "number" || roomId <= 0) return [];

        const auth = useAuthStore();
        const entities = useEntitiesStore();
        const items = state.rooms[roomId]?.items ?? [];

        return items.map((message) => {
          const roomMember = entities.getRoomMember(roomId, message.sender_user_id);
          const senderUser = entities.getUser(message.sender_user_id);
          const assets = useAssetsStore();
          const avatarUrl = resolveMediaUrl(message.sender?.avatar_url ?? senderUser?.avatar_url);
          return mapMessageToChatMessage(
            message,
            auth.me?.id,
            roomMember?.role ?? "member",
            avatarUrl,
            (kind, id, fallbackUrl) =>
              assets.getAssetDisplayUrl(kind, id) ||
              resolveMediaUrl(fallbackUrl) ||
              undefined,
          );
        });
      };
    },
  },

  actions: {
    ensureRoomState(roomId: number) {
      this.rooms[roomId] = this.rooms[roomId] ?? createEmptyRoomState();
      return this.rooms[roomId];
    },

    hydrateDependencies(messages: MessageResponse[]) {
      const entities = useEntitiesStore();
      const assets = useAssetsStore();

      entities.upsertUsers(messages.map((message) => message.sender));

      messages.forEach((message) => {
        message.content.segments.forEach((segment) => {
          if (segment.type === "image") {
            assets.upsertMessageImageAsset({
              id: segment.id,
              url: resolveMediaUrl(segment.url),
            });
            return;
          }

          if (segment.type === "sticker") {
            assets.upsertMessageStickerAsset({
              id: segment.id,
              url: resolveMediaUrl(segment.url),
            });
          }
        });
      });
    },

    setRoomMessages(
      roomId: number,
      messages: MessageResponse[],
      mode: "replace" | "append" | "prepend" = "replace",
    ) {
      const roomState = this.ensureRoomState(roomId);
      roomState.items = mergeMessages(roomState.items, messages, mode);
      roomState.hasLoaded = true;
      this.hydrateDependencies(messages);
    },

    async refreshRoomMessages(roomId: number, limit = 30) {
      const roomState = this.ensureRoomState(roomId);
      roomState.isLoading = true;
      roomState.error = null;

      try {
        const response = await getRoomMessages(roomId, { limit });
        this.setRoomMessages(roomId, response.items, "replace");
        roomState.nextBeforeId = response.next_before_id ?? null;
        return response;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to load room messages");
        roomState.error = message;
        throw new Error(message);
      } finally {
        roomState.isLoading = false;
      }
    },

    async ensureRoomMessages(roomId: number, limit = 30) {
      const roomState = this.ensureRoomState(roomId);

      if (roomState.hasLoaded || roomState.isLoading) {
        return roomState;
      }

      await this.refreshRoomMessages(roomId, limit);
      return this.rooms[roomId];
    },

    async loadOlderMessages(roomId: number, limit = 30) {
      const roomState = this.ensureRoomState(roomId);

      if (roomState.isLoadingHistory || roomState.nextBeforeId == null) {
        return roomState;
      }

      roomState.isLoadingHistory = true;
      roomState.error = null;

      try {
        const response = await getRoomMessages(roomId, {
          before_id: roomState.nextBeforeId,
          limit,
        });

        this.setRoomMessages(roomId, response.items, "prepend");
        roomState.nextBeforeId = response.next_before_id ?? null;
        return response;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to load message history");
        roomState.error = message;
        throw new Error(message);
      } finally {
        roomState.isLoadingHistory = false;
      }
    },

    async sendSegments(roomId: number, segments: ChatSegment[]) {
      const roomState = this.ensureRoomState(roomId);
      const assets = useAssetsStore();
      roomState.isSending = true;
      roomState.error = null;

      try {
        const preparedSegments = await prepareSegmentsForSend(segments, assets);
        const messageSegments = mapChatSegmentsToMessageSegments(preparedSegments);

        if (messageSegments.length === 0) {
          throw new Error("No valid message segments to send");
        }

        const payload: MessageContentIn = {
          segments: messageSegments,
        };

        const created = await createRoomMessage(roomId, {
          content: payload,
        });

        this.setRoomMessages(roomId, [created], "append");
        return created;
      } catch (error: any) {
        const message = extractErrorMessage(error, "Failed to send message");
        roomState.error = message;
        throw new Error(message);
      } finally {
        roomState.isSending = false;
      }
    },

    async sendText(roomId: number, text: string) {
      const content = text.trim();
      if (!content) {
        throw new Error("Message text is empty");
      }

      return this.sendSegments(roomId, [
        {
          id: `text-${Date.now()}`,
          type: "text",
          content,
        },
      ]);
    },

    appendRealtimeMessage(message: MessageResponse) {
      const roomState = this.ensureRoomState(message.room_id);
      roomState.error = null;
      this.setRoomMessages(message.room_id, [message], "append");
    },

    replaceRoomMessage(message: MessageResponse) {
      this.setRoomMessages(message.room_id, [message], "append");
    },

    clearRoom(roomId: number) {
      delete this.rooms[roomId];
    },

    clear() {
      this.rooms = {};
    },
  },
});
