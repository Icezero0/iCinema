import { computed, ref, watch } from "vue";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";
import type {
  RoomRealtimePlaybackState,
  RoomRealtimeSnapshot,
  RoomRealtimeVideoSourceState,
} from "@/infra/realtime/roomRealtime";
import { toMediaEngineLoadInput } from "./mediaEngineTypes";
import { useCompositePocMediaEngine } from "./useCompositePocMediaEngine";
import { usePocLogger } from "./usePocLogger";
import { usePocRoomRealtimeBridge } from "./usePocRoomRealtimeBridge";
import {
  mapHealthToRealtimeStatus,
  POC_ROOM_ID,
  type PlaybackStateInput,
  type SyncGateState,
} from "./types";

export function useHlsPlayerPocController() {
  const syncGateState = ref<SyncGateState>("locked");

  let collectEngineMetrics: () => Record<string, unknown> = () => ({});
  let collectRealtimeMetrics: () => Record<string, unknown> = () => ({});

  const logger = usePocLogger(() => ({
    syncGateState: syncGateState.value,
    ...collectEngineMetrics(),
    ...collectRealtimeMetrics(),
  }));

  const engine = useCompositePocMediaEngine({
    writeLog: logger.writeLog,
  });

  collectEngineMetrics = engine.collectMediaMetrics;

  const realtime = usePocRoomRealtimeBridge({
    writeLog: logger.writeLog,
    onSnapshot: applyRealtimeSnapshot,
    onVideoSource: applyRealtimeVideoSource,
    onPlayback: applyRealtimePlayback,
  });

  collectRealtimeMetrics = realtime.collectRealtimeMetrics;

  const canUsePlayerControls = computed(() =>
    syncGateState.value === "unlocked" &&
    Boolean(engine.appliedUrl.value) &&
    engine.mediaHealthState.value !== "error");

  async function unlockSyncGate() {
    if (syncGateState.value === "unlocked") return;

    setSyncGateState("unlocked", "unlockSyncGate");
    await realtime.enterRoom();
  }

  async function applySourceFromControls(payload: {
    sourceType: RoomVideoSourceType;
    externalUrl: string;
    localFile: File | null;
  }) {
    const input = toMediaEngineLoadInput(
      payload.sourceType,
      payload.externalUrl.trim(),
      payload.localFile,
    );

    if (!input) {
      await engine.loadSource("");
      return;
    }

    if (input.sourceType === "local_file") {
      await engine.loadSource(input);
      return;
    }

    engine.sourceUrl.value = input.externalUrl;
    const handledByRealtime = await realtime.setVideoSource(input.externalUrl);
    if (!handledByRealtime) {
      await engine.loadSource(input);
    }
  }

  async function applyRealtimeSnapshot(snapshot: RoomRealtimeSnapshot) {
    const url = getExternalUrl(snapshot.room_video_source);
    engine.sourceUrl.value = url;
    await engine.loadSource(url, snapshot.playback);
  }

  async function applyRealtimeVideoSource(
    source: RoomRealtimeVideoSourceState | null,
    options: { resetPlayback: PlaybackStateInput | null },
  ) {
    const url = getExternalUrl(source);
    engine.sourceUrl.value = url;

    if (url && url === engine.appliedUrl.value) {
      logger.writeLog("realtimeVideoSourceSoftReset", {
        source,
        resetPlayback: options.resetPlayback,
      });
      if (options.resetPlayback) {
        await engine.applyPlayback(
          {
            ...options.resetPlayback,
            room_id: POC_ROOM_ID,
            anchor_ts_ms: Date.now(),
          } as RoomRealtimePlaybackState,
          { syncPosition: true },
        );
      }
      return;
    }

    logger.writeLog("realtimeVideoSourceReset", {
      source,
      previousUrl: engine.appliedUrl.value,
      resetPlayback: options.resetPlayback,
    });
    await engine.loadSource(url, options.resetPlayback);
  }

  async function applyRealtimePlayback(
    playback: RoomRealtimePlaybackState | null,
    options: { syncPosition: boolean },
  ) {
    await engine.applyPlayback(playback, options);
  }

  async function togglePlayback() {
    const video = engine.videoRef.value;
    if (!video || !canUsePlayerControls.value) {
      logger.writeLog("togglePlaybackIgnored");
      return;
    }

    if (video.paused) {
      logger.writeLog("playRequested", { via: "ws" });
      try {
        await realtime.play(engine.currentTime.value, video.playbackRate || 1);
      } catch (error) {
        logger.writeLog("playRejected", {
          errorName: error instanceof Error ? error.name : null,
          errorMessage: error instanceof Error ? error.message : String(error),
        });
      }
      return;
    }

    logger.writeLog("pauseRequested", { via: "ws" });
    try {
      await realtime.pause(engine.currentTime.value, video.playbackRate || 1);
    } catch (error) {
      logger.writeLog("pauseRejected", {
        errorName: error instanceof Error ? error.name : null,
        errorMessage: error instanceof Error ? error.message : String(error),
      });
    }
  }

  function handleProgressChange(value: number) {
    const nextTime = engine.seekToPercent(value);
    if (nextTime === null) return;

    logger.writeLog("seekRequested", {
      via: "ws",
      percent: value,
      positionSeconds: nextTime,
    });
    realtime.seek(nextTime);
  }

  function handleVolumeChange(value: number) {
    engine.setVolume(value);
  }

  function getExternalUrl(source: RoomRealtimeVideoSourceState | null | undefined) {
    return source?.source_type === "external_url"
      ? source.external_url?.trim() ?? ""
      : "";
  }

  function setSyncGateState(nextState: SyncGateState, reason: string) {
    const previousState = syncGateState.value;
    if (previousState === nextState) return;

    syncGateState.value = nextState;
    logger.writeLog("stateTransition", {
      machine: "syncGate",
      from: previousState,
      to: nextState,
      reason,
    });
  }

  watch(
    () => [
      engine.mediaHealthState.value,
      engine.appliedUrl.value,
      realtime.realtimeActive.value,
    ] as const,
    () => {
      realtime.reportUserPlayerStatus(
        mapHealthToRealtimeStatus(
          Boolean(engine.appliedUrl.value),
          engine.mediaHealthState.value,
        ),
        engine.currentTime.value,
      );
    },
  );

  return {
    POC_ROOM_ID,
    videoRef: engine.videoRef,
    sourceUrl: engine.sourceUrl,
    syncGateState,
    playerState: engine.playerState,
    mediaHealthState: engine.mediaHealthState,
    realtimeStatus: realtime.realtimeStatus,
    realtimeActive: realtime.realtimeActive,
    errorMessage: engine.errorMessage,
    currentTime: engine.currentTime,
    duration: engine.duration,
    bufferedRanges: engine.bufferedRanges,
    volume: engine.volume,
    logText: logger.logText,
    timelineLabel: engine.timelineLabel,
    progressPercent: engine.progressPercent,
    bufferedProgressPercent: engine.bufferedProgressPercent,
    bufferedRangePercents: engine.bufferedRangePercents,
    bufferAhead: engine.bufferAhead,
    unlockSyncGate,
    applySourceFromControls,
    togglePlayback,
    handleProgressChange,
    handleVolumeChange,
    handleVideoEvent: engine.handleVideoEvent,
    handleVideoError: engine.handleVideoError,
    handleTimeUpdate: engine.handleTimeUpdate,
    handleProgress: engine.handleProgress,
    copyLogs: logger.copyLogs,
    clearLogs: logger.clearLogs,
  };
}
