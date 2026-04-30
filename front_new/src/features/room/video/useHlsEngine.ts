import { onBeforeUnmount } from "vue";
import Hls from "hls.js";
import { ROOM_PLAYER_CONFIG, type RoomPlayerConfig } from "./playerConfig";
import type { MediaEngineLogger, PlaybackStateInput } from "./types";
import type { NativeVideoCore } from "./useNativeVideoCore";

export function useHlsEngine(
  core: NativeVideoCore,
  options: {
    writeLog: MediaEngineLogger;
    config?: RoomPlayerConfig;
  },
) {
  const config = options.config ?? ROOM_PLAYER_CONFIG;
  let hls: Hls | null = null;

  async function loadSource(url: string, playback: PlaybackStateInput | null = null) {
    destroyHls();
    core.sourceUrl.value = url;

    if (!url) {
      await core.loadSource("", playback, "hls");
      return;
    }

    if (Hls.isSupported()) {
      await core.loadSource(url, playback, "hls", { attachMediaSource: false });
      const video = core.videoRef.value;
      if (!video) return;

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

    if (core.canPlayNativeHls()) {
      await core.loadSource(url, playback, "hls");
      return;
    }

    await core.loadSource(url, playback, "hls", { attachMediaSource: false });
    core.setFatalMediaError(
      "hlsUnsupported",
      "HLS is not supported in this browser",
    );
  }

  function destroyHls() {
    hls?.destroy();
    hls = null;
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
      core.handleBufferAppended("hls:bufferAppended");
    });

    instance.on(Hls.Events.ERROR, (_event, data) => {
      options.writeLog("hls:error", {
        type: data.type,
        details: data.details,
        fatal: data.fatal,
        error: data.error?.message ?? null,
      });

      if (!data.fatal) return;

      core.setFatalMediaError(
        "hlsFatalError",
        data.error?.message ?? data.details,
        { details: data.details },
      );
    });
  }

  onBeforeUnmount(() => {
    destroyHls();
  });

  return {
    loadSource,
    unload: destroyHls,
  };
}
