import { computed, onBeforeUnmount, ref } from "vue";
import Hls from "hls.js";
import { formatTime, isHlsUrl, readBufferedRanges, readSeekableRanges } from "./mediaUtils";
import type { MediaEngineKind } from "./mediaEngineTypes";
import { HLS_POC_PLAYER_CONFIG, type HlsPocPlayerConfig } from "./playerConfig";
import type {
  BufferedRange,
  MediaHealthState,
  PlaybackStateInput,
  PlayerState,
  PocLogger,
} from "./types";

export function useHlsPocMediaEngine(options: {
  writeLog: PocLogger;
  config?: HlsPocPlayerConfig;
}) {
  const config = options.config ?? HLS_POC_PLAYER_CONFIG;
  const videoRef = ref<HTMLVideoElement | null>(null);
  const sourceUrl = ref("");
  const appliedUrl = ref("");
  const playerState = ref<PlayerState>("idle");
  const mediaHealthState = ref<MediaHealthState>("unknown");
  const errorMessage = ref("");
  const currentTime = ref(0);
  const duration = ref(0);
  const bufferedRanges = ref<BufferedRange[]>([]);
  const seekableRanges = ref<BufferedRange[]>([]);
  const seekRestrictionMessage = ref("");
  const volume = ref(100);
  const activeEngineKind = ref<MediaEngineKind | "none">("none");

  let hls: Hls | null = null;
  let lastBufferedSignature = "";
  let pendingPlayback: PlaybackStateInput | null = null;
  let readyConfirmTimer: number | null = null;
  let stallingErrorTimer: number | null = null;
  let pendingBufferedSeek = false;

  const timelineLabel = computed(() =>
    `${formatTime(currentTime.value)} / ${formatTime(duration.value)}`);

  const progressPercent = computed(() =>
    duration.value > 0
      ? Math.min(100, Math.max(0, (currentTime.value / duration.value) * 100))
      : 0);

  const bufferedProgressPercent = computed(() => {
    const bufferedEnd = bufferedRanges.value.reduce((max, range) => Math.max(max, range.end), 0);
    return duration.value > 0
      ? Math.min(100, Math.max(0, (bufferedEnd / duration.value) * 100))
      : 0;
  });

  const bufferedRangePercents = computed(() =>
    bufferedRanges.value.map((range) => ({
      startPercent: duration.value > 0
        ? Math.min(100, Math.max(0, (range.start / duration.value) * 100))
        : 0,
      endPercent: duration.value > 0
        ? Math.min(100, Math.max(0, (range.end / duration.value) * 100))
        : 0,
    })));

  const bufferAhead = computed(() => {
    const current = currentTime.value;
    const range = bufferedRanges.value.find((item) =>
      current >= item.start - config.bufferRangeEpsilonSeconds &&
      current <= item.end + config.bufferRangeEpsilonSeconds);
    return range ? Math.max(0, range.end - current) : 0;
  });

  const canSeek = computed(() => {
    if (!Number.isFinite(duration.value) || duration.value <= 0) return false;
    if (activeEngineKind.value === "hls" || activeEngineKind.value === "local_video") {
      return true;
    }

    if (activeEngineKind.value === "direct_video") {
      return seekableRanges.value.length > 0;
    }

    return false;
  });

  function collectMediaMetrics() {
    const video = videoRef.value;
    const ranges = readBufferedRanges(video);
    const current = video?.currentTime ?? currentTime.value;
    const currentRange = ranges.find((item) =>
      current >= item.start - config.bufferRangeEpsilonSeconds &&
      current <= item.end + config.bufferRangeEpsilonSeconds);
    const readyEvaluation = evaluateReadyCandidate(video, ranges);

    return {
      playerState: playerState.value,
      mediaHealthState: mediaHealthState.value,
      appliedUrl: appliedUrl.value,
      readyState: video?.readyState ?? null,
      networkState: video?.networkState ?? null,
      paused: video?.paused ?? null,
      ended: video?.ended ?? null,
      seeking: video?.seeking ?? null,
      currentTime: Number(current.toFixed(3)),
      duration: video?.duration && Number.isFinite(video.duration)
        ? Number(video.duration.toFixed(3))
        : null,
      canSeek: canSeek.value,
      seekableRanges: readSeekableRanges(video),
      engineKind: activeEngineKind.value,
      seekRestrictionMessage: seekRestrictionMessage.value,
      bufferAhead: currentRange ? Number((currentRange.end - current).toFixed(3)) : 0,
      bufferedRanges: ranges,
      readyEvaluation,
    };
  }

  function updateMediaMetrics() {
    const video = videoRef.value;
    currentTime.value = video?.currentTime ?? 0;
    duration.value = video?.duration && Number.isFinite(video.duration) ? video.duration : 0;
    bufferedRanges.value = readBufferedRanges(video);
    seekableRanges.value = readSeekableRanges(video);
    if (video) {
      volume.value = Math.round(video.volume * 100);
    }
  }

  function cleanupPlayer() {
    clearReadyConfirmation();
    clearStallingErrorTimer();
    hls?.destroy();
    hls = null;
    lastBufferedSignature = "";
    pendingBufferedSeek = false;
    activeEngineKind.value = "none";

    const video = videoRef.value;
    if (!video) return;

    video.pause();
    video.removeAttribute("src");
    video.load();
  }

  async function loadSource(
    url: string,
    playback: PlaybackStateInput | null = null,
    engineKind: MediaEngineKind = isHlsUrl(url) ? "hls" : "direct_video",
  ) {
    cleanupPlayer();
    updateMediaMetrics();
    errorMessage.value = "";
    appliedUrl.value = url;
    activeEngineKind.value = url ? engineKind : "none";
    seekRestrictionMessage.value = "";
    pendingPlayback = playback;

    if (!url) {
      setPlayerState("idle", "sourceCleared");
      setMediaHealthState("unknown", "sourceCleared");
      options.writeLog("sourceCleared", { playback });
      return;
    }

    const video = videoRef.value;
    if (!video) return;

    setPlayerState("loading", "loadSource");
    setMediaHealthStalling("loadSource");
    options.writeLog("applySource", {
      url,
      playback,
      engineKind,
      hlsSupported: Hls.isSupported(),
      nativeHlsSupported: Boolean(video.canPlayType("application/vnd.apple.mpegurl")),
    });

    if (engineKind === "hls" && Hls.isSupported()) {
      hls = new Hls({
        enableWorker: config.hls.enableWorker,
        lowLatencyMode: config.hls.lowLatencyMode,
        maxBufferLength: config.hls.maxBufferLength,
        maxMaxBufferLength: config.hls.maxMaxBufferLength,
        backBufferLength: config.hls.backBufferLength,
        maxBufferSize: config.hls.maxBufferSize,
      });

      bindHlsEvents(hls);
      hls.attachMedia(video);
      hls.loadSource(url);
      return;
    }

    if (
      engineKind === "hls" &&
      !video.canPlayType("application/vnd.apple.mpegurl")
    ) {
      errorMessage.value = "HLS is not supported in this browser";
      setMediaHealthState("error", "hlsUnsupported");
      return;
    }

    video.src = url;
    video.load();
  }

  async function applyPlayback(
    playback: PlaybackStateInput | null,
    optionsForApply: { syncPosition: boolean },
  ) {
    if (!playback) return;

    const video = videoRef.value;
    if (!video) {
      pendingPlayback = playback;
      options.writeLog("playbackDeferredNoVideo", { playback, options: optionsForApply });
      return;
    }

    options.writeLog("playbackApply", { playback, options: optionsForApply });

    if (
      optionsForApply.syncPosition &&
      (
        !Number.isFinite(video.duration) ||
        video.duration <= 0
      )
    ) {
      pendingPlayback = playback;
      options.writeLog("playbackDeferredUntilDuration", { playback, options: optionsForApply });
      return;
    }

    if (optionsForApply.syncPosition && playback.position_seconds >= 0) {
      const nextTime = Math.min(
        playback.position_seconds,
        Math.max(0, video.duration - 0.25),
      );
      if (!canSeekToTime(nextTime)) {
        pendingPlayback = playback;
        seekRestrictionMessage.value = "该视频源暂不支持跳转到目标位置";
        setMediaHealthStalling("applyPlayback:targetNotSeekable");
        return;
      }

      seekRestrictionMessage.value = "";
      prepareSeek(nextTime, "applyPlayback");
      video.currentTime = nextTime;
      updateMediaMetrics();
    }

    video.playbackRate = playback.playback_rate;

    if (playback.status === "playing") {
      try {
        await video.play();
        setPlayerState("playing", "applyPlayback:play");
        options.writeLog("playbackApplied:play", { playback });
      } catch (error) {
        setPlayerState("paused", "applyPlayback:playRejected");
        options.writeLog("playbackPlayRejected", {
          playback,
          errorName: error instanceof Error ? error.name : null,
          errorMessage: error instanceof Error ? error.message : String(error),
        });
      }
      return;
    }

    video.pause();
    setPlayerState("paused", "applyPlayback:pause");
    options.writeLog("playbackApplied:pause", { playback });
  }

  function seekToPercent(value: number) {
    const video = videoRef.value;
    if (!video || duration.value <= 0 || !Number.isFinite(value)) return null;

    const nextTime = duration.value * (Math.min(100, Math.max(0, value)) / 100);
    if (!canSeekToTime(nextTime)) {
      seekRestrictionMessage.value = "该视频源暂不支持跳转到目标位置";
      return null;
    }

    seekRestrictionMessage.value = "";
    prepareSeek(nextTime, "seekToPercent");
    video.currentTime = nextTime;
    currentTime.value = nextTime;
    return nextTime;
  }

  function setVolume(value: number) {
    const normalized = Math.min(100, Math.max(0, Math.round(value)));
    volume.value = normalized;

    if (videoRef.value) {
      videoRef.value.volume = normalized / 100;
    }

    options.writeLog("volumeChanged", { volume: normalized });
  }

  function bindHlsEvents(instance: Hls) {
    instance.on(Hls.Events.MEDIA_ATTACHED, () => {
      options.writeLog("hls:mediaAttached");
    });

    instance.on(Hls.Events.MANIFEST_PARSED, (_event, data) => {
      options.writeLog("hls:manifestParsed", {
        levels: data.levels.length,
        firstLevel: data.firstLevel,
      });
    });

    instance.on(Hls.Events.LEVEL_LOADED, (_event, data) => {
      options.writeLog("hls:levelLoaded", {
        level: data.level,
        live: data.details.live,
        targetduration: data.details.targetduration,
        fragments: data.details.fragments.length,
      });
    });

    instance.on(Hls.Events.FRAG_LOADED, (_event, data) => {
      options.writeLog("hls:fragLoaded", {
        level: data.frag.level,
        sn: data.frag.sn,
        start: Number(data.frag.start.toFixed(3)),
        duration: Number(data.frag.duration.toFixed(3)),
      });
    });

    instance.on(Hls.Events.BUFFER_APPENDED, () => {
      updateMediaMetrics();
      logProgressIfChanged("hls:bufferAppended");
      scheduleReadyConfirmation("hls:bufferAppended");
    });

    instance.on(Hls.Events.ERROR, (_event, data) => {
      options.writeLog("hls:error", {
        type: data.type,
        details: data.details,
        fatal: data.fatal,
        error: data.error?.message ?? null,
      });

      if (data.fatal) {
        clearReadyConfirmation();
        setMediaHealthState("error", "hlsFatalError", {
          details: data.details,
        });
        errorMessage.value = data.error?.message ?? data.details;
      }
    });
  }

  function logProgressIfChanged(event: string) {
    const signature = bufferedRanges.value
      .map((item) => `${item.start}-${item.end}`)
      .join("|");

    if (signature === lastBufferedSignature) return;
    lastBufferedSignature = signature;
    options.writeLog(event);
  }

  function findBufferedRangeForCurrentTime(
    ranges: BufferedRange[],
    time: number,
  ) {
    return ranges.find((item) =>
      time >= item.start - config.bufferRangeEpsilonSeconds &&
      time <= item.end + config.bufferRangeEpsilonSeconds);
  }

  function findSeekableRangeForTime(time: number) {
    return seekableRanges.value.find((item) =>
      time >= item.start - config.bufferRangeEpsilonSeconds &&
      time <= item.end + config.bufferRangeEpsilonSeconds);
  }

  function canSeekToTime(time: number) {
    if (!Number.isFinite(duration.value) || duration.value <= 0) return false;

    if (activeEngineKind.value === "hls" || activeEngineKind.value === "local_video") {
      return true;
    }

    if (activeEngineKind.value === "direct_video") {
      return Boolean(findSeekableRangeForTime(time));
    }

    return false;
  }

  function evaluateReadyCandidate(
    video = videoRef.value,
    ranges = readBufferedRanges(video),
    targetTime?: number,
  ) {
    if (!video || !appliedUrl.value) {
      return {
        ready: false,
        reason: "no_source",
        bufferAhead: 0,
        requiredBufferAhead: config.readyBufferAheadSeconds,
      };
    }

    if (video.error || mediaHealthState.value === "error") {
      return {
        ready: false,
        reason: "error",
        bufferAhead: 0,
        requiredBufferAhead: config.readyBufferAheadSeconds,
      };
    }

    if (video.seeking && targetTime == null) {
      return {
        ready: false,
        reason: "seeking",
        bufferAhead: 0,
        requiredBufferAhead: config.readyBufferAheadSeconds,
      };
    }

    const mediaDuration = Number.isFinite(video.duration) ? video.duration : duration.value;
    if (!Number.isFinite(mediaDuration) || mediaDuration <= 0) {
      return {
        ready: false,
        reason: "duration_unavailable",
        bufferAhead: 0,
        requiredBufferAhead: config.readyBufferAheadSeconds,
      };
    }

    if (video.ended) {
      return {
        ready: true,
        reason: "ended",
        bufferAhead: 0,
        requiredBufferAhead: 0,
      };
    }

    const current = targetTime ?? video.currentTime;
    const currentRange = findBufferedRangeForCurrentTime(ranges, current);
    if (!currentRange) {
      return {
        ready: false,
        reason: "current_time_not_buffered",
        bufferAhead: 0,
        requiredBufferAhead: config.readyBufferAheadSeconds,
      };
    }

    const remaining = Math.max(0, mediaDuration - current);
    const bufferAhead = Math.max(0, currentRange.end - current);
    const reachesEnd =
      currentRange.end >= mediaDuration - config.endOfMediaEpsilonSeconds;
    const requiredBufferAhead = reachesEnd
      ? Math.max(0, remaining - config.endOfMediaEpsilonSeconds)
      : config.readyBufferAheadSeconds;
    const hasEnoughBufferedAhead =
      bufferAhead + config.bufferRangeEpsilonSeconds >= requiredBufferAhead;
    const hasDecodableFuture =
      targetTime != null ||
      video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA ||
      (reachesEnd && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA);

    return {
      ready: hasEnoughBufferedAhead && hasDecodableFuture,
      reason: hasEnoughBufferedAhead
        ? targetTime != null ? "target_buffered" : hasDecodableFuture ? "ready" : "waiting_for_decodable_future"
        : reachesEnd ? "waiting_for_end_buffer" : "waiting_for_buffer_ahead",
      bufferAhead: Number(bufferAhead.toFixed(3)),
      requiredBufferAhead: Number(requiredBufferAhead.toFixed(3)),
      reachesEnd,
      remaining: Number(remaining.toFixed(3)),
      readyState: video.readyState,
    };
  }

  function clearReadyConfirmation() {
    if (readyConfirmTimer == null) return;

    window.clearTimeout(readyConfirmTimer);
    readyConfirmTimer = null;
  }

  function clearStallingErrorTimer() {
    if (stallingErrorTimer == null) return;

    window.clearTimeout(stallingErrorTimer);
    stallingErrorTimer = null;
  }

  function armStallingErrorTimer(reason: string) {
    clearStallingErrorTimer();
    if (!appliedUrl.value || config.stallingToErrorMs <= 0) return;

    stallingErrorTimer = window.setTimeout(() => {
      stallingErrorTimer = null;
      if (mediaHealthState.value !== "stalling") return;

      errorMessage.value = `Media stayed stalling for ${Math.round(config.stallingToErrorMs / 1000)}s`;
      clearReadyConfirmation();
      setMediaHealthState("error", "stallingTimeout", {
        triggerReason: reason,
        timeoutMs: config.stallingToErrorMs,
      });
    }, config.stallingToErrorMs);
  }

  function setPlayerState(nextState: PlayerState, reason: string) {
    const previousState = playerState.value;
    if (previousState === nextState) return;

    playerState.value = nextState;
    options.writeLog("stateTransition", {
      machine: "player",
      from: previousState,
      to: nextState,
      reason,
    });
  }

  function setMediaHealthState(
    nextState: MediaHealthState,
    reason: string,
    data: Record<string, unknown> = {},
  ) {
    const previousState = mediaHealthState.value;
    if (previousState === nextState) return;

    mediaHealthState.value = nextState;
    if (nextState === "stalling") {
      armStallingErrorTimer(reason);
    } else {
      clearStallingErrorTimer();
    }
    options.writeLog("stateTransition", {
      machine: "mediaHealth",
      from: previousState,
      to: nextState,
      reason,
      ...data,
    });
  }

  function setMediaHealthStalling(reason: string) {
    clearReadyConfirmation();
    setMediaHealthState(appliedUrl.value ? "stalling" : "unknown", reason);
  }

  function prepareSeek(targetTime: number, reason: string) {
    const video = videoRef.value;
    const ranges = readBufferedRanges(video);
    const evaluation = evaluateReadyCandidate(video, ranges, targetTime);
    pendingBufferedSeek = evaluation.ready;

    if (evaluation.ready) {
      clearReadyConfirmation();
      return;
    }

    setMediaHealthStalling(`${reason}:targetNotReady`);
  }

  function scheduleReadyConfirmation(reason: string) {
    if (!appliedUrl.value || mediaHealthState.value === "error") return;

    const initialEvaluation = evaluateReadyCandidate();
    if (!initialEvaluation.ready) {
      return;
    }

    if (readyConfirmTimer != null) return;

    readyConfirmTimer = window.setTimeout(() => {
      readyConfirmTimer = null;
      updateMediaMetrics();
      const finalEvaluation = evaluateReadyCandidate();
      if (!finalEvaluation.ready) {
        options.writeLog("readyConfirmationRejected", {
          reason,
          evaluation: finalEvaluation,
        });
        return;
      }

      setMediaHealthState("ready", `${reason}:readyConfirmationAccepted`, {
        evaluation: finalEvaluation,
      });
      options.writeLog("readyConfirmationAccepted", {
        reason,
        evaluation: finalEvaluation,
      });
    }, config.readyConfirmDelayMs);
  }

  function handleVideoEvent(eventName: string) {
    updateMediaMetrics();

    if (eventName === "loadstart") {
      setPlayerState(appliedUrl.value ? "loading" : "idle", "video:loadstart");
      setMediaHealthStalling("video:loadstart");
    } else if (eventName === "loadedmetadata") {
      if (pendingPlayback && videoRef.value) {
        const playback = pendingPlayback;
        pendingPlayback = null;
        void applyPlayback(playback, { syncPosition: true });
      }
      scheduleReadyConfirmation("loadedmetadata");
    } else if (
      eventName === "canplay" ||
      eventName === "canplaythrough"
    ) {
      setPlayerState(videoRef.value?.paused ? "paused" : "playing", `video:${eventName}`);
      scheduleReadyConfirmation(eventName);
    } else if (eventName === "playing" || eventName === "play") {
      setPlayerState("playing", `video:${eventName}`);
      if (eventName === "playing") {
        scheduleReadyConfirmation(eventName);
      }
    } else if (eventName === "pause") {
      setPlayerState(appliedUrl.value ? "paused" : "idle", "video:pause");
    } else if (eventName === "waiting" || eventName === "stalled") {
      if (!pendingBufferedSeek) {
        setMediaHealthStalling(`video:${eventName}`);
      }
      setPlayerState(videoRef.value?.paused ? "paused" : "playing", `video:${eventName}`);
    } else if (eventName === "seeking") {
      if (!pendingBufferedSeek) {
        setMediaHealthStalling("video:seeking");
      }
    } else if (eventName === "seeked") {
      pendingBufferedSeek = false;
      scheduleReadyConfirmation(eventName);
    } else if (eventName === "ended") {
      setPlayerState("paused", "video:ended");
      scheduleReadyConfirmation(eventName);
    }

    options.writeLog(`video:${eventName}`);
  }

  function handleVideoError() {
    updateMediaMetrics();
    clearReadyConfirmation();
    setMediaHealthState("error", "video:error", {
      code: videoRef.value?.error?.code ?? null,
    });
    const video = videoRef.value;
    errorMessage.value = video?.error?.message || `Media error ${video?.error?.code ?? "unknown"}`;
    options.writeLog("video:error", {
      code: video?.error?.code ?? null,
      message: video?.error?.message ?? null,
    });
  }

  function handleTimeUpdate() {
    updateMediaMetrics();
    tryApplyPendingSeekablePlayback("timeupdate");
    scheduleReadyConfirmation("timeupdate");
  }

  function handleProgress() {
    updateMediaMetrics();
    tryApplyPendingSeekablePlayback("progress");
    logProgressIfChanged("video:progress");
    scheduleReadyConfirmation("video:progress");
  }

  function tryApplyPendingSeekablePlayback(reason: string) {
    if (!pendingPlayback || !Number.isFinite(duration.value) || duration.value <= 0) return;

    const targetTime = Math.min(
      pendingPlayback.position_seconds,
      Math.max(0, duration.value - 0.25),
    );
    if (!canSeekToTime(targetTime)) return;

    const playback = pendingPlayback;
    pendingPlayback = null;
    seekRestrictionMessage.value = "";
    void applyPlayback(playback, { syncPosition: true });
  }

  onBeforeUnmount(() => {
    cleanupPlayer();
  });

  return {
    videoRef,
    sourceUrl,
    appliedUrl,
    playerState,
    mediaHealthState,
    errorMessage,
    currentTime,
    duration,
    bufferedRanges,
    seekableRanges,
    canSeek,
    seekRestrictionMessage,
    volume,
    timelineLabel,
    progressPercent,
    bufferedProgressPercent,
    bufferedRangePercents,
    bufferAhead,
    collectMediaMetrics,
    loadSource,
    applyPlayback,
    seekToPercent,
    setVolume,
    handleVideoEvent,
    handleVideoError,
    handleTimeUpdate,
    handleProgress,
  };
}
