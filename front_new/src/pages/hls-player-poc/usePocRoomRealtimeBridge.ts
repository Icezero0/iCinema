import { onBeforeUnmount, ref } from "vue";
import wsClient, { type WSConnectionStatus } from "@/infra/realtime/wsClient";
import {
  enterRoomRealtime,
  leaveRoomRealtime,
  sendRoomRealtimePlaybackPause,
  sendRoomRealtimePlaybackPlay,
  sendRoomRealtimePlaybackSeek,
  sendRoomRealtimeUserPlayerStatus,
  setRoomRealtimeVideoSource,
  type RoomRealtimePlaybackState,
  type RoomRealtimePlayerStatus,
  type RoomRealtimeSnapshot,
  type RoomRealtimeUserPlayerStatusResponse,
  type RoomRealtimeVideoSourceState,
} from "@/infra/realtime/roomRealtime";
import { useAuthStore } from "@/stores/auth.store";
import {
  POC_ROOM_ID,
  SOURCE_RESET_PLAYBACK,
  type PlaybackStateInput,
  type PocLogger,
} from "./types";

type RealtimeBridgeOptions = {
  writeLog: PocLogger;
  onSnapshot: (snapshot: RoomRealtimeSnapshot) => Promise<void>;
  onVideoSource: (
    source: RoomRealtimeVideoSourceState | null,
    options: { resetPlayback: PlaybackStateInput | null },
  ) => Promise<void>;
  onPlayback: (
    playback: RoomRealtimePlaybackState | null,
    options: { syncPosition: boolean },
  ) => Promise<void>;
};

export function usePocRoomRealtimeBridge(options: RealtimeBridgeOptions) {
  const auth = useAuthStore();
  const realtimeStatus = ref<WSConnectionStatus>(wsClient.connectionStatus);
  const realtimeActive = ref(false);
  const realtimeError = ref("");

  let stopStatusSubscription: (() => void) | null = null;
  let stopRealtimeSubscriptions: Array<() => void> = [];
  let lastReportedPlayerStatus: RoomRealtimePlayerStatus | null = null;

  function collectRealtimeMetrics() {
    return {
      realtimeStatus: realtimeStatus.value,
      realtimeActive: realtimeActive.value,
      realtimeError: realtimeError.value,
    };
  }

  async function enterRoom() {
    try {
      realtimeError.value = "";
      if (auth.status === "unknown") {
        await auth.init();
      } else {
        auth.syncTokensFromStorage();
      }

      if (!auth.isLoggedIn || !auth.accessToken) {
        realtimeError.value = "请先登录后再测试 WS 同步";
        options.writeLog("realtimeAuthMissing");
        return;
      }

      await wsClient.connect(auth.accessToken);
      bindRealtimeEvents();
      const snapshot = await enterRoomRealtime(POC_ROOM_ID);
      realtimeActive.value = true;
      options.writeLog("roomEnterAck", { snapshot });
      await options.onSnapshot(snapshot);
    } catch (error) {
      realtimeActive.value = false;
      realtimeError.value = error instanceof Error ? error.message : String(error);
      options.writeLog("roomEnterFailed", {
        errorName: error instanceof Error ? error.name : null,
        errorMessage: realtimeError.value,
      });
    }
  }

  async function setVideoSource(url: string) {
    if (!realtimeActive.value) {
      options.writeLog("applySourceLocallyWithoutRealtime", { url });
      return false;
    }

    try {
      const response = await setRoomRealtimeVideoSource({
        source_type: "external_url",
        external_url: url,
        anchor_ts_ms: Date.now(),
      });
      options.writeLog("roomVideoSourceSetAck", { response });
      await options.onVideoSource(response.room_video_source ?? null, {
        resetPlayback: null,
      });
      await options.onPlayback(response.playback ?? null, { syncPosition: true });
    } catch (error) {
      options.writeLog("roomVideoSourceSetFailed", {
        errorName: error instanceof Error ? error.name : null,
        errorMessage: error instanceof Error ? error.message : String(error),
      });
    }

    return true;
  }

  async function play(positionSeconds: number, playbackRate: number) {
    const response = await sendRoomRealtimePlaybackPlay({
      position_seconds: positionSeconds,
      anchor_ts_ms: Date.now(),
      playback_rate: playbackRate,
    });
    options.writeLog("playbackPlayAck", { response });
    await options.onPlayback(response.playback ?? null, { syncPosition: false });
  }

  async function pause(positionSeconds: number, playbackRate: number) {
    const response = await sendRoomRealtimePlaybackPause({
      position_seconds: positionSeconds,
      anchor_ts_ms: Date.now(),
      playback_rate: playbackRate,
    });
    options.writeLog("playbackPauseAck", { response });
    await options.onPlayback(response.playback ?? null, { syncPosition: false });
  }

  function seek(positionSeconds: number) {
    void sendRoomRealtimePlaybackSeek({
      position_seconds: positionSeconds,
      anchor_ts_ms: Date.now(),
    }).then((response) => {
      options.writeLog("playbackSeekAck", { response });
      void options.onPlayback(response.playback ?? null, { syncPosition: true });
    }).catch((error) => {
      options.writeLog("seekRejected", {
        errorName: error instanceof Error ? error.name : null,
        errorMessage: error instanceof Error ? error.message : String(error),
      });
    });
  }

  function reportUserPlayerStatus(status: RoomRealtimePlayerStatus, positionSeconds: number) {
    if (!realtimeActive.value) return;
    if (status === lastReportedPlayerStatus) return;

    lastReportedPlayerStatus = status;
    void sendRoomRealtimeUserPlayerStatus({
      status,
      reported_at_ms: Date.now(),
      position_seconds: positionSeconds,
    }).then(handleUserPlayerStatusResponse).catch((error) => {
      options.writeLog("userPlayerStatusFailed", {
        status,
        errorName: error instanceof Error ? error.name : null,
        errorMessage: error instanceof Error ? error.message : String(error),
      });
    });
  }

  function handleUserPlayerStatusResponse(response: RoomRealtimeUserPlayerStatusResponse) {
    options.writeLog("userPlayerStatusAck", { response });
    if (response.playback) {
      void options.onPlayback(response.playback, { syncPosition: false });
    }
  }

  function bindRealtimeEvents() {
    if (stopStatusSubscription || stopRealtimeSubscriptions.length > 0) return;

    stopStatusSubscription = wsClient.onStatusChange((status) => {
      realtimeStatus.value = status;
      options.writeLog("wsStatusChanged", { status });
    });

    stopRealtimeSubscriptions = [
      wsClient.onEvent<RoomRealtimeVideoSourceState>("room_video_source_set", (payload) => {
        if (payload.room_id !== POC_ROOM_ID) return;
        options.writeLog("wsRoomVideoSourceEvent", { payload });
        void options.onVideoSource(payload, {
          resetPlayback: SOURCE_RESET_PLAYBACK,
        });
      }),
      wsClient.onEvent<RoomRealtimePlaybackState>("playback_play", (payload) => {
        if (payload.room_id !== POC_ROOM_ID) return;
        options.writeLog("wsPlaybackPlayEvent", { payload });
        void options.onPlayback(payload, { syncPosition: false });
      }),
      wsClient.onEvent<RoomRealtimePlaybackState>("playback_pause", (payload) => {
        if (payload.room_id !== POC_ROOM_ID) return;
        options.writeLog("wsPlaybackPauseEvent", { payload });
        void options.onPlayback(payload, { syncPosition: false });
      }),
      wsClient.onEvent<RoomRealtimePlaybackState>("playback_seek", (payload) => {
        if (payload.room_id !== POC_ROOM_ID) return;
        options.writeLog("wsPlaybackSeekEvent", { payload });
        void options.onPlayback(payload, { syncPosition: true });
      }),
      wsClient.onEvent("user_player_states", (payload) => {
        options.writeLog("wsUserPlayerStatesEvent", { payload });
      }),
      wsClient.onEvent("session_closed", (payload) => {
        options.writeLog("wsSessionClosedEvent", { payload });
        realtimeActive.value = false;
      }),
    ];
  }

  onBeforeUnmount(() => {
    stopStatusSubscription?.();
    stopRealtimeSubscriptions.forEach((stop) => stop());
    stopRealtimeSubscriptions = [];
    if (realtimeActive.value) {
      void leaveRoomRealtime(POC_ROOM_ID).catch((error) => {
        options.writeLog("roomLeaveFailed", {
          errorName: error instanceof Error ? error.name : null,
          errorMessage: error instanceof Error ? error.message : String(error),
        });
      });
    }
  });

  return {
    realtimeStatus,
    realtimeActive,
    realtimeError,
    collectRealtimeMetrics,
    enterRoom,
    setVideoSource,
    play,
    pause,
    seek,
    reportUserPlayerStatus,
  };
}
