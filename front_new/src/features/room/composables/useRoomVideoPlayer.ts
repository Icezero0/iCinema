import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import Hls from "hls.js";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";

const HLS_FORWARD_BUFFER_SECONDS = 90;
const HLS_MAX_FORWARD_BUFFER_SECONDS = 180;
const HLS_BACK_BUFFER_SECONDS = 45;
const HLS_MAX_BUFFER_SIZE = 120 * 1024 * 1024;
const SEEK_END_EPSILON_SECONDS = 0.25;
const HLS_BUFFER_STALLED_DETAIL = "bufferStalledError";
const STALL_CONFIRM_DELAY_MS = 80;
const PLAYBACK_ADVANCE_EPSILON_SECONDS = 0.04;
const BUFFER_STALL_MARGIN_SECONDS = 0.45;
const STATUS_CALIBRATION_INTERVAL_MS = 500;
const HLS_RECOVERY_CHECK_INTERVAL_MS = 5_000;
const MAX_HLS_RECOVERABLE_ERROR_MS = 30_000;
const MAX_HLS_RECOVERABLE_ERROR_COUNT = 8;

export type RoomBufferedRange = {
  startPercent: number;
  endPercent: number;
};

export type RoomLocalPlayerStatus = "idle" | "ready" | "stalling" | "error";

type UseRoomVideoPlayerOptions = {
  sourceType: Ref<RoomVideoSourceType>;
  sourceUrl: Ref<string>;
  sourceFile: Ref<File | null>;
  sourceRevision: Ref<number>;
  volume: Ref<number>;
  messages: {
    hlsLoadFailed: string;
    hlsUnsupported: string;
    sourceLoadFailed: string;
    playFailed: string;
    playFailedWithSource: string;
    screenshotNoFrame: string;
    screenshotFailed: string;
  };
  emit: {
    playStateChange: (value: boolean) => void;
    durationChange: (value: number) => void;
    timeChange: (value: number) => void;
    bufferedProgressChange: (value: number) => void;
    bufferedRangesChange: (value: RoomBufferedRange[]) => void;
    waitingChange: (value: boolean) => void;
    error: (value: string) => void;
  };
};

function isHlsSource(url: string) {
  const cleanUrl = url.split(/[?#]/, 1)[0]?.toLowerCase() ?? "";
  return cleanUrl.endsWith(".m3u8");
}

export function useRoomVideoPlayer(options: UseRoomVideoPlayerOptions) {
  const videoRef = ref<HTMLVideoElement | null>(null);
  const isPlaying = ref(false);
  const playerStatus = ref<RoomLocalPlayerStatus>("idle");
  const isWaiting = computed(() => playerStatus.value === "stalling");
  const playerError = ref("");
  const hasLoadedMetadata = ref(false);
  let hls: Hls | null = null;
  let localObjectUrl = "";
  let stallConfirmTimer = 0;
  let playbackFrame = 0;
  let statusCalibrationTimer = 0;
  let hlsRecoveryCheckTimer = 0;
  let hlsErrorStartedAt = 0;
  let hlsConsecutiveErrorCount = 0;
  let externalNoCorsRetryUrl = "";

  const normalizedVolume = computed(() =>
    Math.min(1, Math.max(0, Math.round(options.volume.value) / 100)));
  const hasSource = computed(() =>
    options.sourceType.value === "external_url"
      ? options.sourceUrl.value.trim().length > 0
      : options.sourceFile.value != null);
  const isCurrentHlsSource = computed(() =>
    options.sourceType.value === "external_url" && isHlsSource(options.sourceUrl.value.trim()));

  function clearMediaSource() {
    clearStallConfirmTimer();
    clearHlsRecoveryCheckTimer();
    resetHlsErrorTracking();
    stopPlaybackFrameLoop();

    hls?.destroy();
    hls = null;
    externalNoCorsRetryUrl = "";

    const video = videoRef.value;
    if (video) {
      video.pause();
      video.currentTime = 0;
      video.removeAttribute("src");
      video.removeAttribute("crossorigin");
      video.load();
    }

    if (localObjectUrl) {
      URL.revokeObjectURL(localObjectUrl);
      localObjectUrl = "";
    }
  }

  function setPlayerError(message: string) {
    clearStallConfirmTimer();
    clearHlsRecoveryCheckTimer();
    playerError.value = message;
    setPlayerStatus("error");
    options.emit.error(message);
  }

  function handleRecoverableHlsIssue() {
    const video = videoRef.value;

    if (!hlsErrorStartedAt) {
      hlsErrorStartedAt = Date.now();
    }
    hlsConsecutiveErrorCount += 1;

    if (isHlsIssueUnrecoverable()) {
      setPlayerError(options.messages.hlsLoadFailed);
      return;
    }

    if (video && shouldConsiderStalling(video)) {
      scheduleStallConfirmation();
    } else {
      setPlayerStatus("stalling");
    }
    startHlsRecoveryCheck();
  }

  function isHlsIssueUnrecoverable() {
    if (!hlsErrorStartedAt) return false;

    return (
      Date.now() - hlsErrorStartedAt > MAX_HLS_RECOVERABLE_ERROR_MS ||
      hlsConsecutiveErrorCount > MAX_HLS_RECOVERABLE_ERROR_COUNT
    );
  }

  function loadExternalSource(url: string) {
    const video = videoRef.value;
    if (!video || !url) return;
    video.crossOrigin = "anonymous";

    if (isHlsSource(url)) {
      if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = url;
        video.load();
        return;
      }

      if (Hls.isSupported()) {
        hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true,
          maxBufferLength: HLS_FORWARD_BUFFER_SECONDS,
          maxMaxBufferLength: HLS_MAX_FORWARD_BUFFER_SECONDS,
          backBufferLength: HLS_BACK_BUFFER_SECONDS,
          maxBufferSize: HLS_MAX_BUFFER_SIZE,
        });
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (!data.fatal) {
            if (data.details === HLS_BUFFER_STALLED_DETAIL) {
              scheduleStallConfirmation();
            } else {
              handleRecoverableHlsIssue();
            }
            return;
          }

          setPlayerError(options.messages.hlsLoadFailed);
        });
        hls.on(Hls.Events.FRAG_LOADED, handleHlsRecoverySignal);
        hls.on(Hls.Events.LEVEL_LOADED, handleHlsRecoverySignal);
        hls.on(Hls.Events.FRAG_PARSING_DATA, handleHlsRecoverySignal);
        hls.loadSource(url);
        hls.attachMedia(video);
        return;
      }

      setPlayerError(options.messages.hlsUnsupported);
      return;
    }

    video.src = url;
    video.load();
  }

  function loadLocalFileSource(file: File) {
    const video = videoRef.value;
    if (!video) return;

    localObjectUrl = URL.createObjectURL(file);
    video.src = localObjectUrl;
    video.load();
  }

  function resetPlaybackSignals() {
    clearStallConfirmTimer();
    resetHlsErrorTracking();
    isPlaying.value = false;
    hasLoadedMetadata.value = false;
    setPlayerStatus(hasSource.value ? "stalling" : "idle");
    options.emit.playStateChange(false);
    options.emit.durationChange(0);
    options.emit.timeChange(0);
    options.emit.bufferedProgressChange(0);
    options.emit.bufferedRangesChange([]);
  }

  function loadCurrentSource() {
    clearMediaSource();
    playerError.value = "";
    resetPlaybackSignals();

    if (!hasSource.value) return;

    try {
      if (videoRef.value) {
        videoRef.value.volume = normalizedVolume.value;
      }

      if (options.sourceType.value === "external_url") {
        loadExternalSource(options.sourceUrl.value.trim());
      } else if (options.sourceFile.value) {
        loadLocalFileSource(options.sourceFile.value);
      }
    } catch (error) {
      setPlayerError(error instanceof Error ? error.message : options.messages.sourceLoadFailed);
    }
  }

  async function playVideo() {
    const video = videoRef.value;
    if (!video || !hasSource.value || playerError.value) return;

    try {
      await video.play();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      setPlayerError(error instanceof Error ? error.message : options.messages.playFailed);
    }
  }

  function pauseVideo() {
    videoRef.value?.pause();
  }

  async function togglePlayback() {
    if (isPlaying.value) {
      pauseVideo();
      return;
    }
    await playVideo();
  }

  function seekToPercent(percent: number) {
    const video = videoRef.value;
    if (!video || !Number.isFinite(video.duration) || video.duration <= 0) return;

    pauseVideo();
    const normalizedPercent = Math.min(100, Math.max(0, percent));
    const rawTime = video.duration * (normalizedPercent / 100);
    video.currentTime =
      normalizedPercent >= 100
        ? Math.max(0, video.duration - SEEK_END_EPSILON_SECONDS)
        : rawTime;
    emitBufferedProgress();
  }

  function handleLoadedMetadata() {
    const video = videoRef.value;
    hasLoadedMetadata.value = true;
    if (video && canTreatAsReady(video)) {
      setReadyState();
    }
    options.emit.durationChange(
      video?.duration && Number.isFinite(video.duration) ? video.duration : 0,
    );
    emitBufferedProgress();
  }

  function handleTimeUpdate() {
    clearStallConfirmTimer();
    setReadyState();
    syncPlaybackFrame();
  }

  function handleDurationChange() {
    const duration = videoRef.value?.duration ?? 0;
    options.emit.durationChange(Number.isFinite(duration) ? duration : 0);
    emitBufferedProgress();
  }

  function handlePlay() {
    isPlaying.value = true;
    clearStallConfirmTimer();
    setReadyState();
    options.emit.playStateChange(true);
    startPlaybackFrameLoop();
  }

  function handlePause() {
    isPlaying.value = false;
    clearStallConfirmTimer();
    if (hasSource.value && !playerError.value) {
      setReadyState();
    }
    options.emit.playStateChange(false);
    stopPlaybackFrameLoop();
    syncPlaybackFrame();
  }

  function handleWaiting() {
    scheduleStallConfirmation();
  }

  function handleCanPlay() {
    clearStallConfirmTimer();
    setReadyState();
    emitBufferedProgress();
  }

  function handleProgress() {
    const video = videoRef.value;
    if (video && video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
      setReadyState();
    }
    emitBufferedProgress();
  }

  function handleSeeking() {
    setPlayerStatus("stalling");
    emitBufferedProgress();
  }

  function handleSeeked() {
    const video = videoRef.value;
    if (video && canTreatAsReady(video)) {
      setReadyState();
    }
    syncPlaybackFrame();
  }

  function emitBufferedProgress() {
    const video = videoRef.value;

    if (
      !video ||
      !Number.isFinite(video.duration) ||
      video.duration <= 0 ||
      video.buffered.length === 0
    ) {
      options.emit.bufferedProgressChange(0);
      options.emit.bufferedRangesChange([]);
      return;
    }

    let bufferedEnd = 0;
    const bufferedRanges: RoomBufferedRange[] = [];
    for (let index = 0; index < video.buffered.length; index += 1) {
      const start = video.buffered.start(index);
      const end = video.buffered.end(index);
      bufferedEnd = Math.max(bufferedEnd, end);
      bufferedRanges.push({
        startPercent: Math.min(100, Math.max(0, (start / video.duration) * 100)),
        endPercent: Math.min(100, Math.max(0, (end / video.duration) * 100)),
      });
    }

    const emittedProgress = Math.min(100, Math.max(0, (bufferedEnd / video.duration) * 100));
    options.emit.bufferedProgressChange(emittedProgress);
    options.emit.bufferedRangesChange(bufferedRanges);
  }

  function clearWaitingState() {
    setReadyState();
  }

  function clearStallConfirmTimer() {
    if (!stallConfirmTimer) return;
    window.clearTimeout(stallConfirmTimer);
    stallConfirmTimer = 0;
  }

  function scheduleStallConfirmation() {
    const video = videoRef.value;
    if (!video || !shouldConsiderStalling(video)) return;

    const probeTime = video.currentTime;
    clearStallConfirmTimer();
    stallConfirmTimer = window.setTimeout(() => {
      stallConfirmTimer = 0;
      const latestVideo = videoRef.value;
      if (!latestVideo || !shouldConsiderStalling(latestVideo)) {
        clearWaitingState();
        return;
      }

      const advanced =
        latestVideo.currentTime > probeTime + PLAYBACK_ADVANCE_EPSILON_SECONDS;
      if (advanced) {
        clearWaitingState();
        return;
      }

      const isStalled =
        isNearBufferedEnd(latestVideo) ||
        latestVideo.readyState < HTMLMediaElement.HAVE_FUTURE_DATA;

      if (isStalled) {
        setPlayerStatus("stalling");
      } else {
        setReadyState();
      }
    }, STALL_CONFIRM_DELAY_MS);
  }

  function shouldConsiderStalling(video: HTMLVideoElement) {
    return (
      hasSource.value &&
      !playerError.value &&
      !video.paused &&
      !video.ended
    );
  }

  function isNearBufferedEnd(video: HTMLVideoElement) {
    const bufferedEnd = getBufferedEndForCurrentTime(video);
    if (bufferedEnd == null) return true;
    return bufferedEnd - video.currentTime <= BUFFER_STALL_MARGIN_SECONDS;
  }

  function getBufferedEndForCurrentTime(video: HTMLVideoElement) {
    const currentTime = video.currentTime;

    for (let index = 0; index < video.buffered.length; index += 1) {
      const start = video.buffered.start(index);
      const end = video.buffered.end(index);
      if (
        currentTime >= start - BUFFER_STALL_MARGIN_SECONDS &&
        currentTime <= end + BUFFER_STALL_MARGIN_SECONDS
      ) {
        return end;
      }
    }

    return null;
  }

  function canTreatAsReady(video: HTMLVideoElement) {
    return (
      hasSource.value &&
      !playerError.value &&
      !video.seeking &&
      video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA
    );
  }

  function setReadyState() {
    if (!hasSource.value) {
      setPlayerStatus("idle");
      return;
    }

    if (playerError.value) return;
    resetHlsErrorTracking();
    setPlayerStatus("ready");
  }

  function setPlayerStatus(status: RoomLocalPlayerStatus) {
    if (playerStatus.value === status) return;

    const wasWaiting = playerStatus.value === "stalling";
    playerStatus.value = status;
    const nextWaiting = status === "stalling";
    if (wasWaiting !== nextWaiting) {
      options.emit.waitingChange(nextWaiting);
    }
  }

  function handleHlsRecoverySignal() {
    const video = videoRef.value;
    if (video && canTreatAsReady(video)) {
      setReadyState();
    }
  }

  function startHlsRecoveryCheck() {
    if (hlsRecoveryCheckTimer) return;

    hlsRecoveryCheckTimer = window.setInterval(() => {
      if (isHlsIssueUnrecoverable()) {
        setPlayerError(options.messages.hlsLoadFailed);
        return;
      }

      handleHlsRecoverySignal();
    }, HLS_RECOVERY_CHECK_INTERVAL_MS);
  }

  function clearHlsRecoveryCheckTimer() {
    if (!hlsRecoveryCheckTimer) return;
    window.clearInterval(hlsRecoveryCheckTimer);
    hlsRecoveryCheckTimer = 0;
  }

  function resetHlsErrorTracking() {
    hlsErrorStartedAt = 0;
    hlsConsecutiveErrorCount = 0;
    clearHlsRecoveryCheckTimer();
  }

  function calibratePlayerStatus() {
    const video = videoRef.value;

    if (!hasSource.value) {
      setPlayerStatus("idle");
      return;
    }

    if (playerError.value) {
      setPlayerStatus("error");
      return;
    }

    if (!video) return;

    if (canTreatAsReady(video) && playerStatus.value === "stalling") {
      setReadyState();
      return;
    }

    if (
      shouldConsiderStalling(video) &&
      video.readyState < HTMLMediaElement.HAVE_FUTURE_DATA
    ) {
      scheduleStallConfirmation();
    }
  }

  function handleEnded() {
    isPlaying.value = false;
    clearStallConfirmTimer();
    setReadyState();
    options.emit.playStateChange(false);
    stopPlaybackFrameLoop();
    syncPlaybackFrame();
  }

  function handleVideoError() {
    const currentUrl = options.sourceType.value === "external_url"
      ? options.sourceUrl.value.trim()
      : "";
    const video = videoRef.value;

    if (
      video &&
      currentUrl &&
      !isCurrentHlsSource.value &&
      video.crossOrigin === "anonymous" &&
      externalNoCorsRetryUrl !== currentUrl
    ) {
      externalNoCorsRetryUrl = currentUrl;
      playerError.value = "";
      clearStallConfirmTimer();
      setPlayerStatus("stalling");
      video.pause();
      video.removeAttribute("crossorigin");
      video.removeAttribute("src");
      video.src = currentUrl;
      video.load();
      resetPlaybackSignals();
      return;
    }

    stopPlaybackFrameLoop();
    setPlayerError(options.messages.playFailedWithSource);
  }

  function captureCurrentFrame() {
    return new Promise<Blob>((resolve, reject) => {
      const video = videoRef.value;
      if (
        !video ||
        !hasSource.value ||
        playerError.value ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
        video.videoWidth <= 0 ||
        video.videoHeight <= 0
      ) {
        reject(new Error(options.messages.screenshotNoFrame));
        return;
      }

      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      try {
        const context = canvas.getContext("2d");
        if (!context) {
          reject(new Error(options.messages.screenshotFailed));
          return;
        }

        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
          if (!blob) {
            reject(new Error(options.messages.screenshotFailed));
            return;
          }
          resolve(blob);
        }, "image/png");
      } catch {
        reject(new Error(options.messages.screenshotFailed));
      }
    });
  }

  function syncPlaybackFrame() {
    options.emit.timeChange(videoRef.value?.currentTime ?? 0);
    emitBufferedProgress();
  }

  function startPlaybackFrameLoop() {
    if (playbackFrame) return;

    const tick = () => {
      playbackFrame = 0;
      if (!isPlaying.value) return;
      syncPlaybackFrame();
      playbackFrame = window.requestAnimationFrame(tick);
    };

    playbackFrame = window.requestAnimationFrame(tick);
  }

  function stopPlaybackFrameLoop() {
    if (!playbackFrame) return;
    window.cancelAnimationFrame(playbackFrame);
    playbackFrame = 0;
  }

  function startStatusCalibration() {
    if (statusCalibrationTimer) return;
    statusCalibrationTimer = window.setInterval(
      calibratePlayerStatus,
      STATUS_CALIBRATION_INTERVAL_MS,
    );
  }

  function stopStatusCalibration() {
    if (!statusCalibrationTimer) return;
    window.clearInterval(statusCalibrationTimer);
    statusCalibrationTimer = 0;
  }

  onMounted(() => {
    loadCurrentSource();
    startStatusCalibration();
  });

  onBeforeUnmount(() => {
    clearStallConfirmTimer();
    clearHlsRecoveryCheckTimer();
    stopStatusCalibration();
    stopPlaybackFrameLoop();
    clearMediaSource();
  });

  watch(
    () => [
      options.sourceType.value,
      options.sourceUrl.value,
      options.sourceFile.value,
      options.sourceRevision.value,
    ] as const,
    loadCurrentSource,
  );

  watch(normalizedVolume, (volume) => {
    if (videoRef.value) {
      videoRef.value.volume = volume;
    }
  }, { immediate: true });

  return {
    videoRef,
    isPlaying,
    isWaiting,
    playerStatus,
    playerError,
    hasLoadedMetadata,
    hasSource,
    playVideo,
    pauseVideo,
    togglePlayback,
    seekToPercent,
    captureCurrentFrame,
    handleLoadedMetadata,
    handleTimeUpdate,
    handleDurationChange,
    handlePlay,
    handlePause,
    handleWaiting,
    handleCanPlay,
    handleProgress,
    handleSeeking,
    handleSeeked,
    handleEnded,
    handleVideoError,
  };
}
