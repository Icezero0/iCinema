import { onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import wsClient, { type WSConnectionStatus } from "@/infra/realtime/wsClient";
import {
  enterRoomRealtime,
  getRoomRealtimePresence,
  getRoomRealtimeVideoRuntime,
  leaveRoomRealtime,
  type RoomRealtimePlaybackState,
  type RoomRealtimePresenceState,
  type RoomRealtimeSessionClosed,
  type RoomRealtimeSnapshot,
  type RoomRealtimeResourceStatus,
  type RoomRealtimeUserResourceState,
  type RoomRealtimeUserResourceStatesState,
  type RoomRealtimeVideoSourceState,
} from "@/infra/realtime/roomRealtime";
import type { MessageResponse } from "@/infra/api/messages.api";
import { useAuthStore } from "@/stores/auth.store";
import { useMessagesStore } from "@/stores/messages.store";

type UseRoomRealtimeSessionOptions = {
  roomId: Ref<number>;
  refreshRoom: () => void | Promise<void>;
  refreshRoomMembers: () => void | Promise<void>;
  refreshRoomRequests: () => void | Promise<void>;
  refreshRoomSettings: () => void | Promise<void>;
  onSessionClosed?: (payload: RoomRealtimeSessionClosed) => void;
  onRealtimeMessage?: (payload: MessageResponse) => void;
  onRealtimeReconnected?: () => void | Promise<void>;
};

type RoomRealtimePlaybackEventAction =
  | "snapshot"
  | "playback_play"
  | "playback_pause"
  | "playback_seek";

type RoomRealtimePlaybackEvent = {
  action: RoomRealtimePlaybackEventAction;
  state: RoomRealtimePlaybackState;
};

type RoomRealtimeVideoSourceEventAction =
  | "snapshot"
  | "room_video_source_set";

type RoomRealtimeVideoSourceEvent = {
  action: RoomRealtimeVideoSourceEventAction;
  state: RoomRealtimeVideoSourceState | null;
};

const ROOM_REALTIME_DEBUG = false;
const ROOM_REALTIME_RESUME_CHECK_THROTTLE_MS = 2500;

function payloadRoomId(payload: unknown) {
  if (!payload || typeof payload !== "object") return null;

  const roomId = (payload as { room_id?: unknown }).room_id;
  return typeof roomId === "number" ? roomId : null;
}

function isCurrentRoomPayload(payload: unknown, roomId: number) {
  const eventRoomId = payloadRoomId(payload);
  return eventRoomId == null || eventRoomId === roomId;
}

function normalizePresentUserIds(snapshot: RoomRealtimeSnapshot) {
  return Array.isArray(snapshot.present_user_ids)
    ? snapshot.present_user_ids.filter((id) => typeof id === "number")
    : [];
}

function normalizeRealtimeResourceStatus(status: unknown): RoomRealtimeResourceStatus | null {
  if (status === "ready" || status === "stalling" || status === "error") return status;
  return null;
}

function normalizeUserResourceStates(state: RoomRealtimeUserResourceStatesState | null | undefined) {
  if (!Array.isArray(state?.user_resource_states)) return [];

  return state.user_resource_states.flatMap((item): RoomRealtimeUserResourceState[] => {
    const status = normalizeRealtimeResourceStatus(item?.status);
    if (
      typeof item?.room_id !== "number" ||
      typeof item?.user_id !== "number" ||
      !status
    ) {
      return [];
    }

    return [{ ...item, status }];
  });
}

export function useRoomRealtimeSession(options: UseRoomRealtimeSessionOptions) {
  const auth = useAuthStore();
  const messagesStore = useMessagesStore();
  const presentUserIds = ref<number[]>([]);
  const hasPresenceSnapshot = ref(false);
  const roomVideoSource = ref<RoomRealtimeVideoSourceState | null>(null);
  const roomVideoSourceEvent = ref<RoomRealtimeVideoSourceEvent | null>(null);
  const roomPlayback = ref<RoomRealtimePlaybackState | null>(null);
  const roomPlaybackEvent = ref<RoomRealtimePlaybackEvent | null>(null);
  const userResourceStates = ref<RoomRealtimeUserResourceState[]>([]);
  const isRealtimeActive = ref(false);
  const realtimeStatus = ref<WSConnectionStatus>(wsClient.connectionStatus);
  const realtimeError = ref("");

  let stopStatusSubscription: (() => void) | null = null;
  let stopEventSubscriptions: Array<() => void> = [];
  let enteredRoomId: number | null = null;
  let enteringRoomId: number | null = null;
  let enterAttempt = 0;
  let shouldRefreshAfterReconnect = false;
  let lastResumeCheckAt = 0;

  async function ensureConnectionReady() {
    auth.syncTokensFromStorage();

    if (!auth.isLoggedIn || !auth.accessToken) {
      throw new Error("Realtime connection requires an authenticated user");
    }

    await wsClient.connect(auth.accessToken);
  }

  async function enterCurrentRoom() {
    const roomId = options.roomId.value;
    auth.syncTokensFromStorage();
    if (!roomId || !auth.isLoggedIn || !auth.accessToken) return;
    if (enteredRoomId === roomId || enteringRoomId === roomId) return;

    const attempt = ++enterAttempt;
    enteringRoomId = roomId;
    realtimeError.value = "";

    try {
      await ensureConnectionReady();
      if (attempt !== enterAttempt || roomId !== options.roomId.value) return;

      const snapshot = await enterRoomRealtime(roomId);
      if (attempt !== enterAttempt || roomId !== options.roomId.value) return;

      const wasRecovering = shouldRefreshAfterReconnect;
      shouldRefreshAfterReconnect = false;
      enteredRoomId = roomId;
      isRealtimeActive.value = true;
      presentUserIds.value = normalizePresentUserIds(snapshot);
      hasPresenceSnapshot.value = true;
      roomVideoSource.value = snapshot.room_video_source ?? null;
      roomVideoSourceEvent.value = {
        action: "snapshot",
        state: snapshot.room_video_source ?? null,
      };
      roomPlayback.value = snapshot.playback ?? null;
      roomPlaybackEvent.value = snapshot.playback
        ? { action: "snapshot", state: snapshot.playback }
        : null;
      userResourceStates.value = normalizeUserResourceStates(snapshot.user_resource_states);

      if (wasRecovering) {
        void options.onRealtimeReconnected?.();
      }
    } catch (error) {
      if (attempt !== enterAttempt) return;
      isRealtimeActive.value = false;
      realtimeError.value =
        error instanceof Error ? error.message : "Failed to enter realtime room";
    } finally {
      if (enteringRoomId === roomId) {
        enteringRoomId = null;
      }
    }
  }

  function markRealtimeSessionDisconnected() {
    if (
      !enteredRoomId &&
      !enteringRoomId &&
      !isRealtimeActive.value &&
      !hasPresenceSnapshot.value
    ) {
      return;
    }

    enterAttempt += 1;
    shouldRefreshAfterReconnect = true;
    enteredRoomId = null;
    enteringRoomId = null;
    isRealtimeActive.value = false;
    presentUserIds.value = [];
    hasPresenceSnapshot.value = false;
    roomVideoSource.value = null;
    roomVideoSourceEvent.value = null;
    roomPlayback.value = null;
    roomPlaybackEvent.value = null;
    userResourceStates.value = [];
  }

  async function leaveEnteredRoom(roomId = enteredRoomId) {
    if (!roomId) return;

    enteredRoomId = null;
    enteringRoomId = null;
    isRealtimeActive.value = false;
    presentUserIds.value = [];
    hasPresenceSnapshot.value = false;
    roomVideoSource.value = null;
    roomVideoSourceEvent.value = null;
    roomPlayback.value = null;
    roomPlaybackEvent.value = null;
    userResourceStates.value = [];

    if (wsClient.connectionStatus !== "ready") return;

    try {
      await leaveRoomRealtime(roomId);
    } catch {
      // Leaving is best-effort; the server also cleans up on disconnect.
    }
  }

  function refreshIfCurrentRoom(payload: unknown, refresh: () => void | Promise<void>) {
    const roomId = options.roomId.value;
    if (!roomId || !isCurrentRoomPayload(payload, roomId)) return;
    void refresh();
  }

  function handlePresence(payload: RoomRealtimePresenceState) {
    if (!isCurrentRoomPayload(payload, options.roomId.value)) return;
    presentUserIds.value = Array.isArray(payload.present_user_ids)
      ? payload.present_user_ids.filter((id) => typeof id === "number")
      : [];
    hasPresenceSnapshot.value = true;
  }

  function handleMessage(payload: MessageResponse) {
    if (!payload?.room_id || payload.room_id !== options.roomId.value) return;
    messagesStore.appendRealtimeMessage(payload);
    options.onRealtimeMessage?.(payload);
  }

  function handleRoomVideoSource(payload: RoomRealtimeVideoSourceState) {
    if (!isCurrentRoomPayload(payload, options.roomId.value)) return;
    roomVideoSource.value = payload ?? null;
    roomVideoSourceEvent.value = {
      action: "room_video_source_set",
      state: payload ?? null,
    };
  }

  function handlePlayback(
    action: Exclude<RoomRealtimePlaybackEventAction, "snapshot">,
    payload: RoomRealtimePlaybackState,
  ) {
    if (!isCurrentRoomPayload(payload, options.roomId.value)) return;
    if (ROOM_REALTIME_DEBUG) {
      console.info("[iCinema realtime playback debug]", {
        event: "playbackEventReceived",
        action,
        roomId: options.roomId.value,
        payload,
        previousRoomPlayback: roomPlayback.value,
        previousRoomPlaybackEvent: roomPlaybackEvent.value,
      });
    }
    roomPlayback.value = payload ?? null;
    roomPlaybackEvent.value = payload ? { action, state: payload } : null;
  }

  async function fetchPresenceSnapshot() {
    const response = await getRoomRealtimePresence();
    const presence = response.presence;
    if (!presence || !isCurrentRoomPayload(presence, options.roomId.value)) return;

    handlePresence(presence);
  }

  async function fetchVideoRuntimeSnapshot(options?: { updateState?: boolean }) {
    const response = await getRoomRealtimeVideoRuntime();
    const shouldUpdateState = options?.updateState ?? true;

    roomVideoSource.value = response.room_video_source ?? null;
    roomPlayback.value = response.playback ?? null;
    userResourceStates.value = normalizeUserResourceStates(response.user_resource_states);

    if (shouldUpdateState) {
      roomVideoSourceEvent.value = {
        action: "snapshot",
        state: response.room_video_source ?? null,
      };
      roomPlaybackEvent.value = response.playback
        ? { action: "snapshot", state: response.playback }
        : null;
    }

    return response;
  }

  function handleUserResourceStates(payload: RoomRealtimeUserResourceStatesState) {
    if (!isCurrentRoomPayload(payload, options.roomId.value)) return;
    if (ROOM_REALTIME_DEBUG) {
      console.info("[iCinema realtime playback debug]", {
        event: "userResourceStatesReceived",
        roomId: options.roomId.value,
        payload,
      });
    }
    userResourceStates.value = normalizeUserResourceStates(payload);
  }

  function handleSessionClosed(payload: RoomRealtimeSessionClosed) {
    if (!isCurrentRoomPayload(payload, options.roomId.value)) return;
    enteredRoomId = null;
    isRealtimeActive.value = false;
    presentUserIds.value = [];
    hasPresenceSnapshot.value = true;
    roomVideoSource.value = null;
    roomVideoSourceEvent.value = null;
    roomPlayback.value = null;
    roomPlaybackEvent.value = null;
    userResourceStates.value = [];
    options.onSessionClosed?.(payload);
  }

  function bindEvents() {
    stopEventSubscriptions = [
      wsClient.onEvent("room_info", (payload) => {
        refreshIfCurrentRoom(payload, options.refreshRoom);
      }),
      wsClient.onEvent("room_settings", (payload) => {
        refreshIfCurrentRoom(payload, options.refreshRoomSettings);
      }),
      wsClient.onEvent("room_members", (payload) => {
        refreshIfCurrentRoom(payload, () => {
          void options.refreshRoomMembers();
          void options.refreshRoomRequests();
        });
      }),
      wsClient.onEvent<RoomRealtimePresenceState>("room_user_presence", handlePresence),
      wsClient.onEvent<MessageResponse>("message", handleMessage),
      wsClient.onEvent<RoomRealtimeVideoSourceState>("room_video_source_set", handleRoomVideoSource),
      wsClient.onEvent<RoomRealtimePlaybackState>("playback_play", (payload) => {
        handlePlayback("playback_play", payload);
      }),
      wsClient.onEvent<RoomRealtimePlaybackState>("playback_pause", (payload) => {
        handlePlayback("playback_pause", payload);
      }),
      wsClient.onEvent<RoomRealtimePlaybackState>("playback_seek", (payload) => {
        handlePlayback("playback_seek", payload);
      }),
      wsClient.onEvent<RoomRealtimeUserResourceStatesState>("user_resource_states", handleUserResourceStates),
      wsClient.onEvent<RoomRealtimeSessionClosed>("session_closed", handleSessionClosed),
    ];
  }

  function handlePageResume() {
    const now = Date.now();
    if (now - lastResumeCheckAt < ROOM_REALTIME_RESUME_CHECK_THROTTLE_MS) return;
    lastResumeCheckAt = now;

    auth.syncTokensFromStorage();
    if (!options.roomId.value || !auth.isLoggedIn || !auth.accessToken) return;

    if (
      wsClient.connectionStatus === "closed" ||
      wsClient.connectionStatus === "error" ||
      wsClient.connectionStatus === "idle"
    ) {
      markRealtimeSessionDisconnected();
      void enterCurrentRoom();
      return;
    }

    if (
      wsClient.connectionStatus === "ready" &&
      (enteredRoomId !== options.roomId.value || !isRealtimeActive.value)
    ) {
      markRealtimeSessionDisconnected();
      void enterCurrentRoom();
    }
  }

  function handleVisibilityChange() {
    if (document.visibilityState !== "visible") return;
    handlePageResume();
  }

  onMounted(() => {
    bindEvents();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pageshow", handlePageResume);
    window.addEventListener("focus", handlePageResume);
    stopStatusSubscription = wsClient.onStatusChange((status) => {
      realtimeStatus.value = status;
      if (status === "closed" || status === "error" || status === "reconnecting") {
        markRealtimeSessionDisconnected();
        return;
      }

      if (
        status === "ready" &&
        enteredRoomId !== options.roomId.value &&
        enteringRoomId !== options.roomId.value
      ) {
        void enterCurrentRoom();
      }
    });
    void enterCurrentRoom();
  });

  watch(
    () => options.roomId.value,
    async (roomId, previousRoomId) => {
      enterAttempt += 1;
      if (previousRoomId) {
        await leaveEnteredRoom(previousRoomId);
      }
      if (roomId) {
        void enterCurrentRoom();
      }
    },
  );

  watch(
    () => [auth.isLoggedIn, auth.accessToken] as const,
    ([isLoggedIn, accessToken]) => {
      if (!isLoggedIn || !accessToken) {
        enterAttempt += 1;
        void leaveEnteredRoom();
        return;
      }
      void enterCurrentRoom();
    },
  );

  onBeforeUnmount(() => {
    enterAttempt += 1;
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    window.removeEventListener("pageshow", handlePageResume);
    window.removeEventListener("focus", handlePageResume);
    stopStatusSubscription?.();
    stopEventSubscriptions.forEach((stop) => stop());
    stopEventSubscriptions = [];
    void leaveEnteredRoom();
  });

  return {
    presentUserIds,
    hasPresenceSnapshot,
    roomVideoSource,
    roomVideoSourceEvent,
    roomPlayback,
    roomPlaybackEvent,
    userResourceStates,
    isRealtimeActive,
    realtimeStatus,
    realtimeError,
    enterCurrentRoom,
    fetchPresenceSnapshot,
    fetchVideoRuntimeSnapshot,
  };
}
