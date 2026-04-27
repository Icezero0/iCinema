import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import Hls from "hls.js";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";

const HLS_FORWARD_BUFFER_SECONDS = 90;
const HLS_MAX_FORWARD_BUFFER_SECONDS = 180;
const HLS_BACK_BUFFER_SECONDS = 45;
const HLS_MAX_BUFFER_SIZE = 120 * 1024 * 1024;
const WAITING_CONFIRM_DELAY_MS = 180;
const SEEK_END_EPSILON_SECONDS = 0.25;

export type RoomBufferedRange = {
  startPercent: number;
  endPercent: number;
};

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
  const isWaiting = ref(false);
  const playerError = ref("");
  const hasLoadedMetadata = ref(false);
  let hls: Hls | null = null;
  let localObjectUrl = "";
  let waitingCheckTimer = 0;
  let playbackFrame = 0;
  let externalNoCorsRetryUrl = "";

  const normalizedVolume = computed(() =>
    Math.min(1, Math.max(0, Math.round(options.volume.value) / 100)));
  const hasSource = computed(() =>
    options.sourceType.value === "external_url"
      ? options.sourceUrl.value.trim().length > 0
      : options.sourceFile.value != null);
  const isCurrentHlsSource = computed(() =>
    options.sourceType.value === "external_url" && isHlsSource(options.sourceUrl.value.trim()));

  function clearWaitingTimer() {
    if (!waitingCheckTimer) return;
    window.clearTimeout(waitingCheckTimer);
    waitingCheckTimer = 0;
  }

  function clearMediaSource() {
    clearWaitingTimer();
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
    playerError.value = message;
    isWaiting.value = false;
    options.emit.error(message);
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
          if (!data.fatal) return;
          setPlayerError(options.messages.hlsLoadFailed);
        });
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
    isWaiting.value = false;
    isPlaying.value = false;
    hasLoadedMetadata.value = false;
    options.emit.playStateChange(false);
    options.emit.durationChange(0);
    options.emit.timeChange(0);
    options.emit.bufferedProgressChange(0);
    options.emit.bufferedRangesChange([]);
    options.emit.waitingChange(false);
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
    options.emit.durationChange(
      video?.duration && Number.isFinite(video.duration) ? video.duration : 0,
    );
    emitBufferedProgress();
  }

  function handleTimeUpdate() {
    clearWaitingState();
    syncPlaybackFrame();
  }

  function handleDurationChange() {
    const duration = videoRef.value?.duration ?? 0;
    options.emit.durationChange(Number.isFinite(duration) ? duration : 0);
    emitBufferedProgress();
  }

  function handlePlay() {
    isPlaying.value = true;
    clearWaitingState();
    options.emit.playStateChange(true);
    startPlaybackFrameLoop();
  }

  function handlePause() {
    isPlaying.value = false;
    options.emit.playStateChange(false);
    stopPlaybackFrameLoop();
    syncPlaybackFrame();
  }

  function handleWaiting() {
    clearWaitingTimer();

    waitingCheckTimer = window.setTimeout(() => {
      waitingCheckTimer = 0;
      const video = videoRef.value;
      const blocked =
        !!video &&
        !video.paused &&
        !video.ended &&
        video.readyState < HTMLMediaElement.HAVE_FUTURE_DATA;

      isWaiting.value = blocked;
      options.emit.waitingChange(blocked);
    }, WAITING_CONFIRM_DELAY_MS);
  }

  function handleCanPlay() {
    clearWaitingState();
    emitBufferedProgress();
  }

  function handleSeeking() {
    emitBufferedProgress();
  }

  function handleSeeked() {
    emitBufferedProgress();
  }

  function emitBufferedProgress() {
    const video = videoRef.value;

    if (
      !video ||
      !isCurrentHlsSource.value ||
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
    clearWaitingTimer();
    if (!isWaiting.value) return;
    isWaiting.value = false;
    options.emit.waitingChange(false);
  }

  function handleEnded() {
    isPlaying.value = false;
    isWaiting.value = false;
    options.emit.playStateChange(false);
    options.emit.waitingChange(false);
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
      isWaiting.value = false;
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

  onMounted(loadCurrentSource);

  onBeforeUnmount(() => {
    clearWaitingTimer();
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
    handleSeeking,
    handleSeeked,
    handleEnded,
    handleVideoError,
  };
}
