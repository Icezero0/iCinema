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
  seekToSeconds: (seconds: number) => void;
  captureCurrentFrame: () => Promise<Blob>;
};

type UseRoomPlaybackStateOptions = {
  roomId: Ref<number>;
  playerStageRef: Ref<RoomPlayerStageHandle | null>;
  t: (key: string) => string;
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

export function useRoomPlaybackState(options: UseRoomPlaybackStateOptions) {
  const entitiesStore = useEntitiesStore();
  const toasts = useToastsStore();

  const playbackIsPlaying = ref(false);
  const playbackProgress = ref(0);
  const playbackBufferedProgress = ref(0);
  const playbackBufferedRanges = ref<Array<{ startPercent: number; endPercent: number }>>([]);
  const pendingSeekProgress = ref<number | null>(null);
  const playbackVolume = ref(DEFAULT_LOCAL_ROOM_VOLUME);
  const playbackCurrentTime = ref(0);
  const playbackDuration = ref(0);
  const playbackSourceType = ref<RoomVideoSourceType>("external_url");
  const playbackSourceUrl = ref("");
  const playbackSourceFile = ref<File | null>(null);
  const playbackSourceFileName = ref("");
  const playbackSourceRevision = ref(0);
  const pendingRealtimePlayback = ref<RoomRealtimePlaybackState | null>(null);

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

  async function applyStateToPlayerElement(state: RoomRealtimePlaybackState) {
    options.playerStageRef.value?.seekToSeconds(state.position_seconds);
    if (state.status === "playing") {
      await options.playerStageRef.value?.playVideo();
    } else {
      options.playerStageRef.value?.pauseVideo();
    }
  }

  function togglePlayback() {
    void options.playerStageRef.value?.togglePlayback();
  }

  function handlePlaybackProgressChange(value: number) {
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
      const state = pendingRealtimePlayback.value;
      pendingRealtimePlayback.value = null;
      void applyStateToPlayerElement(state);
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
  }) {
    playbackSourceType.value = payload.sourceType;

    if (payload.sourceType === "external_url") {
      playbackSourceUrl.value = payload.externalUrl.trim();
      playbackSourceFile.value = null;
      playbackSourceFileName.value = "";
    } else if (payload.localFile) {
      playbackSourceFile.value = payload.localFile;
      playbackSourceFileName.value = payload.localFile.name;
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
    playbackIsPlaying.value = false;
    playbackSourceRevision.value += 1;
  }

  function applyRealtimeVideoSource(source: RoomRealtimeVideoSourceState | null) {
    playbackSourceFile.value = null;
    playbackSourceFileName.value = "";
    playbackBufferedProgress.value = 0;
    playbackBufferedRanges.value = [];
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
      return;
    }

    playbackSourceType.value = source.source_type;
    playbackSourceUrl.value =
      source.source_type === "external_url"
        ? source.external_url ?? ""
        : "";
    playbackSourceRevision.value += 1;
  }

  async function applyRealtimePlaybackState(state: RoomRealtimePlaybackState | null) {
    if (!state) return;

    playbackIsPlaying.value = state.status === "playing";
    playbackCurrentTime.value = state.position_seconds;
    pendingSeekProgress.value = null;
    updatePlaybackProgress();

    if (playbackDuration.value <= 0) {
      pendingRealtimePlayback.value = state;
      return;
    }

    pendingRealtimePlayback.value = null;
    await applyStateToPlayerElement(state);
  }

  async function handleCopyPlayerScreenshot() {
    try {
      const blob = await options.playerStageRef.value?.captureCurrentFrame();
      if (!blob) {
        throw new Error(options.t("room.playback.screenshotNoFrame"));
      }

      if (!navigator.clipboard?.write || typeof ClipboardItem === "undefined") {
        throw new Error(options.t("room.playback.screenshotClipboardUnsupported"));
      }

      await navigator.clipboard.write([
        new ClipboardItem({ [blob.type]: blob }),
      ]);
      toasts.push({
        message: options.t("room.playback.screenshotCopied"),
        tone: "success",
      });
    } catch (error) {
      toasts.push({
        message:
          error instanceof Error && error.message
            ? error.message
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

  function resetPlaybackState() {
    playbackIsPlaying.value = false;
    playbackProgress.value = 0;
    pendingSeekProgress.value = null;
    pendingRealtimePlayback.value = null;
    playbackBufferedProgress.value = 0;
    playbackBufferedRanges.value = [];
    playbackCurrentTime.value = 0;
    playbackDuration.value = 0;
    playbackSourceType.value = "external_url";
    playbackSourceUrl.value = "";
    playbackSourceFile.value = null;
    playbackSourceFileName.value = "";
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
    playbackVolume,
    playbackCurrentTime,
    playbackDuration,
    playbackSourceType,
    playbackSourceUrl,
    playbackSourceFile,
    playbackSourceFileName,
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
    resetPlaybackState,
    resetPlaybackVolume,
  };
}
