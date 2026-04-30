import { computed, ref, type Ref } from "vue";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";
import type {
  RoomRealtimePlaybackState,
  RoomRealtimeVideoSourceState,
} from "@/infra/realtime/roomRealtime";
import {
  DEFAULT_LOCAL_ROOM_VOLUME,
  useEntitiesStore,
} from "@/stores/entities.store";
import { useToastsStore } from "@/stores/toasts.store";

export type RoomPlayerStageHandle = {
  playVideo: () => Promise<void>;
  togglePlayback: () => Promise<void>;
  pauseVideo: () => void;
  seekToPercent: (percent: number) => void;
  seekToSeconds: (seconds: number) => Promise<void>;
  captureCurrentFrame: () => Promise<Blob>;
};

type UseRoomPlaybackStateOptions = {
  roomId: Ref<number>;
  playerStageRef: Ref<RoomPlayerStageHandle | null>;
  t: (key: string) => string;
};

type PendingRealtimePlayback = {
  state: RoomRealtimePlaybackState;
  syncPosition: boolean;
};

function formatPlaybackTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "00:00";

  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const restSeconds = totalSeconds % 60;
  const mm = String(minutes).padStart(2, "0");
  const ss = String(restSeconds).padStart(2, "0");

  if (hours <= 0) return `${mm}:${ss}`;
  return `${hours}:${mm}:${ss}`;
}

const PENDING_SEEK_EPSILON_SECONDS = 0.5;
const ROOM_PLAYBACK_APPLY_DEBUG = false;

export function useRoomPlaybackState(options: UseRoomPlaybackStateOptions) {
  const entitiesStore = useEntitiesStore();
  const toasts = useToastsStore();

  const playbackIsPlaying = ref(false);
  const playbackProgress = ref(0);
  const playbackBufferedProgress = ref(0);
  const playbackBufferedRanges = ref<Array<{ startPercent: number; endPercent: number }>>([]);
  const playbackCanSeek = ref(false);
  const pendingSeekProgress = ref<number | null>(null);
  const playbackVolume = ref(DEFAULT_LOCAL_ROOM_VOLUME);
  const playbackCurrentTime = ref(0);
  const playbackDuration = ref(0);
  const playbackSourceType = ref<RoomVideoSourceType>("external_url");
  const playbackSourceUrl = ref("");
  const playbackSourceFile = ref<File | null>(null);
  const playbackSourceFileName = ref("");
  const playbackSourceFileHash = ref("");
  const playbackSourceRevision = ref(0);
  const pendingRealtimePlayback = ref<PendingRealtimePlayback | null>(null);

  const playbackTimelineLabel = computed(() =>
    `${formatPlaybackTime(playbackCurrentTime.value)} / ${formatPlaybackTime(playbackDuration.value)}`);
  const playbackDisplayProgress = computed(() =>
    pendingSeekProgress.value ?? playbackProgress.value);

  function updatePlaybackProgress() {
    playbackProgress.value =
      playbackDuration.value > 0
        ? Math.min(100, Math.max(0, (playbackCurrentTime.value / playbackDuration.value) * 100))
        : 0;
  }

  async function applyStateToPlayerElement(
    state: RoomRealtimePlaybackState,
    syncPosition: boolean,
  ) {
    logRealtimePlaybackApply("applyStateToPlayerElement", {
      state,
      syncPosition,
      hasPlayer: Boolean(options.playerStageRef.value),
    });

    if (syncPosition) {
      logRealtimePlaybackApply("seekForRealtimeState", {
        positionSeconds: state.position_seconds,
      });
      await options.playerStageRef.value?.seekToSeconds(state.position_seconds);
    }

    if (state.status === "playing") {
      logRealtimePlaybackApply("playForRealtimeState", { state });
      await options.playerStageRef.value?.playVideo();
    } else {
      logRealtimePlaybackApply("pauseForRealtimeState", { state });
      options.playerStageRef.value?.pauseVideo();
    }
  }

  function togglePlayback() {
    void options.playerStageRef.value?.togglePlayback();
  }

  function handlePlaybackProgressChange(value: number) {
    if (!playbackCanSeek.value) return;

    options.playerStageRef.value?.pauseVideo();
    playbackIsPlaying.value = false;
    const normalizedValue = Math.min(100, Math.max(0, value));
    pendingSeekProgress.value = normalizedValue;
    playbackProgress.value = normalizedValue;
    options.playerStageRef.value?.seekToPercent(normalizedValue);
  }

  function handlePlaybackDurationChange(value: number) {
    playbackDuration.value = value;
    updatePlaybackProgress();
    if (value > 0 && pendingRealtimePlayback.value) {
      const pending = pendingRealtimePlayback.value;
      pendingRealtimePlayback.value = null;
      void applyStateToPlayerElement(pending.state, pending.syncPosition);
    }
  }

  function handlePlaybackTimeChange(value: number) {
    playbackCurrentTime.value = value;
    updatePlaybackProgress();

    if (pendingSeekProgress.value == null || playbackDuration.value <= 0) return;

    const pendingTime = playbackDuration.value * (pendingSeekProgress.value / 100);
    if (Math.abs(playbackCurrentTime.value - pendingTime) <= PENDING_SEEK_EPSILON_SECONDS) {
      pendingSeekProgress.value = null;
    }
  }

  function handleApplyPlaybackSource(payload: {
    sourceType: RoomVideoSourceType;
    externalUrl: string;
    localFile: File | null;
    localFileHash?: string | null;
  }) {
    playbackSourceType.value = payload.sourceType;

    if (payload.sourceType === "external_url") {
      playbackSourceUrl.value = payload.externalUrl.trim();
      playbackSourceFile.value = null;
      playbackSourceFileName.value = "";
      playbackSourceFileHash.value = "";
    } else if (payload.localFile) {
      playbackSourceFile.value = payload.localFile;
      playbackSourceFileName.value = payload.localFile.name;
      playbackSourceFileHash.value = payload.localFileHash ?? "";
      playbackSourceUrl.value = "";
      playbackBufferedProgress.value = 0;
      playbackBufferedRanges.value = [];
    }

    playbackCurrentTime.value = 0;
    playbackDuration.value = 0;
    playbackProgress.value = 0;
    pendingSeekProgress.value = null;
    pendingRealtimePlayback.value = null;
    playbackBufferedProgress.value = 0;
    playbackBufferedRanges.value = [];
    playbackCanSeek.value = false;
    playbackIsPlaying.value = false;
    playbackSourceRevision.value += 1;
  }

  function applyRealtimeVideoSource(source: RoomRealtimeVideoSourceState | null) {
    const nextSourceUrl = source?.source_type === "external_url"
      ? source.external_url?.trim() ?? ""
      : "";
    const isSameExternalSource =
      source !== null &&
      source.source_type === "external_url" &&
      playbackSourceType.value === "external_url" &&
      playbackSourceUrl.value === nextSourceUrl;
    const nextFileHash = source?.source_type === "local_file"
      ? source.file_hash ?? ""
      : "";
    const isSameLocalFileSource =
      source !== null &&
      source.source_type === "local_file" &&
      playbackSourceType.value === "local_file" &&
      Boolean(playbackSourceFile.value) &&
      playbackSourceFileHash.value === nextFileHash;

    if (isSameExternalSource || isSameLocalFileSource) {
      pendingSeekProgress.value = null;
      pendingRealtimePlayback.value = null;
      playbackIsPlaying.value = false;
      playbackCurrentTime.value = 0;
      playbackProgress.value = 0;
      return "soft-reset" as const;
    }

    playbackSourceFile.value = null;
    playbackSourceFileName.value = "";
    playbackSourceFileHash.value = "";
    playbackBufferedProgress.value = 0;
    playbackBufferedRanges.value = [];
    playbackCanSeek.value = false;
    playbackCurrentTime.value = 0;
    playbackDuration.value = 0;
    playbackProgress.value = 0;
    pendingSeekProgress.value = null;
    pendingRealtimePlayback.value = null;
    playbackIsPlaying.value = false;

    if (!source) {
      playbackSourceType.value = "external_url";
      playbackSourceUrl.value = "";
      playbackSourceRevision.value += 1;
      return "cleared" as const;
    }

    playbackSourceType.value = source.source_type;
    playbackSourceUrl.value =
      source.source_type === "external_url"
        ? source.external_url?.trim() ?? ""
        : "";
    playbackSourceRevision.value += 1;
    return "reloaded" as const;
  }

  async function applyRealtimePlaybackState(
    state: RoomRealtimePlaybackState | null,
    options?: { syncPosition?: boolean },
  ) {
    logRealtimePlaybackApply("applyRealtimePlaybackState", {
      state,
      syncPosition: options?.syncPosition ?? false,
      playbackIsPlaying: playbackIsPlaying.value,
      playbackCurrentTime: playbackCurrentTime.value,
      playbackDuration: playbackDuration.value,
      pendingRealtimePlayback: pendingRealtimePlayback.value,
    });

    if (!state) return;

    const syncPosition = options?.syncPosition ?? false;
    playbackIsPlaying.value = state.status === "playing";
    pendingSeekProgress.value = null;

    if (syncPosition) {
      playbackCurrentTime.value = state.position_seconds;
      updatePlaybackProgress();
    }

    if (syncPosition && playbackDuration.value <= 0) {
      pendingRealtimePlayback.value = { state, syncPosition };
      logRealtimePlaybackApply("deferRealtimePlaybackUntilDuration", {
        state,
        syncPosition,
      });
      return;
    }

    pendingRealtimePlayback.value = null;
    await applyStateToPlayerElement(state, syncPosition);
  }

  function logRealtimePlaybackApply(event: string, extra: Record<string, unknown> = {}) {
    if (!ROOM_PLAYBACK_APPLY_DEBUG) return;

    console.info("[iCinema playback apply debug]", {
      event,
      roomId: options.roomId.value,
      playbackIsPlaying: playbackIsPlaying.value,
      playbackCurrentTime: playbackCurrentTime.value,
      playbackDuration: playbackDuration.value,
      playbackProgress: playbackProgress.value,
      pendingSeekProgress: pendingSeekProgress.value,
      ...extra,
    });
  }

  async function handleCopyPlayerScreenshot() {
    try {
      const blob = await options.playerStageRef.value?.captureCurrentFrame();
      if (!blob) throw new Error("screenshotNoFrame");

      if (!navigator.clipboard?.write || typeof ClipboardItem === "undefined") {
        throw new Error("screenshotClipboardUnsupported");
      }

      await navigator.clipboard.write([
        new ClipboardItem({ [blob.type]: blob }),
      ]);
      toasts.push({
        message: options.t("room.playback.screenshotCopied"),
        tone: "success",
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "";
      const knownErrorKeys = new Set([
        "screenshotNoFrame",
        "screenshotClipboardUnsupported",
        "screenshotFailed",
      ]);
      toasts.push({
        message: knownErrorKeys.has(errorMessage)
          ? options.t(`room.playback.${errorMessage}`)
          : options.t("room.playback.screenshotFailed"),
        tone: "danger",
      });
    }
  }

  function loadLocalPlaybackVolume() {
    playbackVolume.value = entitiesStore.loadRoomLocalVolume(options.roomId.value);
  }

  function handlePlaybackVolumeChange(value: number) {
    playbackVolume.value = entitiesStore.setRoomLocalVolume(options.roomId.value, value);
  }

  function handlePlaybackCanSeekChange(value: boolean) {
    playbackCanSeek.value = value;
  }

  function resetPlaybackState() {
    playbackIsPlaying.value = false;
    playbackProgress.value = 0;
    pendingSeekProgress.value = null;
    pendingRealtimePlayback.value = null;
    playbackBufferedProgress.value = 0;
    playbackBufferedRanges.value = [];
    playbackCanSeek.value = false;
    playbackCurrentTime.value = 0;
    playbackDuration.value = 0;
    playbackSourceType.value = "external_url";
    playbackSourceUrl.value = "";
    playbackSourceFile.value = null;
    playbackSourceFileName.value = "";
    playbackSourceFileHash.value = "";
    playbackSourceRevision.value += 1;
  }

  function resetPlaybackVolume() {
    playbackVolume.value = DEFAULT_LOCAL_ROOM_VOLUME;
  }

  return {
    playbackIsPlaying,
    playbackProgress,
    playbackDisplayProgress,
    playbackBufferedProgress,
    playbackBufferedRanges,
    playbackCanSeek,
    playbackVolume,
    playbackCurrentTime,
    playbackDuration,
    playbackSourceType,
    playbackSourceUrl,
    playbackSourceFile,
    playbackSourceFileName,
    playbackSourceFileHash,
    playbackSourceRevision,
    playbackTimelineLabel,
    togglePlayback,
    handlePlaybackProgressChange,
    handlePlaybackDurationChange,
    handlePlaybackTimeChange,
    handleApplyPlaybackSource,
    applyRealtimeVideoSource,
    applyRealtimePlaybackState,
    handleCopyPlayerScreenshot,
    loadLocalPlaybackVolume,
    handlePlaybackVolumeChange,
    handlePlaybackCanSeekChange,
    resetPlaybackState,
    resetPlaybackVolume,
  };
}
