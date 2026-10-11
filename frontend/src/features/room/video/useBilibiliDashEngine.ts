import { onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import type shaka from "shaka-player";
import type { BilibiliLocalMedia } from "@/infra/bilibili-desktop";
import type { NativeVideoCore } from "./useNativeVideoCore";

let protocolRegistered = false;

function registerMediaProtocol(library: typeof shaka) {
  if (protocolRegistered) return;
  library.polyfill.installAll();
  if (!library.Player.isBrowserSupported() || !library.net.HttpFetchPlugin?.parse) {
    throw new Error("BILIBILI_DASH_UNSUPPORTED");
  }
  library.net.NetworkingEngine.registerScheme(
    "icinema-bili",
    library.net.HttpFetchPlugin.parse,
    library.net.NetworkingEngine.PluginPriority.PREFERRED,
    true,
  );
  protocolRegistered = true;
}

export function useBilibiliDashEngine(core: NativeVideoCore) {
  const { t } = useI18n();
  let player: shaka.Player | null = null;
  let manifestUrl: string | null = null;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let retryDelayMs = 1000;

  function clearRetry() {
    if (retryTimer) clearTimeout(retryTimer);
    retryTimer = null;
    retryDelayMs = 1000;
  }

  function retryUntilProgress(instance: shaka.Player) {
    if (player !== instance || retryTimer) return;
    retryTimer = setTimeout(() => {
      retryTimer = null;
      if (player !== instance) return;
      instance.retryStreaming();
      retryDelayMs = Math.min(10000, retryDelayMs * 2);
      retryUntilProgress(instance);
    }, retryDelayMs);
  }

  function showFailureAfterBufferEnds(instance: shaka.Player) {
    if (player !== instance) return;
    if (core.bufferAhead.value > 0.5 && !core.videoRef.value?.error) {
      retryTimer = setTimeout(() => {
        retryTimer = null;
        showFailureAfterBufferEnds(instance);
      }, 1500);
      return;
    }
    core.setFatalMediaError("bilibiliDashError", t("room.playback.errors.playFailed"));
  }

  async function unload() {
    clearRetry();
    core.setStallingRecoveryHandler(null);
    const previous = player;
    player = null;
    if (previous) await previous.destroy();
    if (manifestUrl) URL.revokeObjectURL(manifestUrl);
    manifestUrl = null;
  }

  async function loadSource(media: BilibiliLocalMedia) {
    await unload();
    core.sourceUrl.value = `bilibili:${media.bvid}/${media.cid}`;
    await core.loadSource(core.sourceUrl.value, null, "bilibili_dash", { attachMediaSource: false });
    const video = core.videoRef.value;
    if (!video) return;

    try {
      const library = (await import("shaka-player")).default;
      registerMediaProtocol(library);
      const instance = new library.Player();
      player = instance;
      await instance.attach(video);
      core.setStallingRecoveryHandler(() => {
        retryUntilProgress(instance);
        return player === instance;
      });
      instance.addEventListener("segmentappended", () => {
        if (player === instance) clearRetry();
      });
      instance.addEventListener("buffering", () => {
        if (player === instance && !instance.isBuffering()) clearRetry();
      });
      instance.addEventListener("error", (event) => {
        if (player !== instance) return;
        const detail = (event as Event & { detail?: shaka.util.Error }).detail;
        if (detail?.severity === library.util.Error.Severity.RECOVERABLE) return;
        if (retryTimer) return;
        if (detail?.category === library.util.Error.Category.NETWORK) {
          retryUntilProgress(instance);
          return;
        }
        showFailureAfterBufferEnds(instance);
      });
      instance.configure({ streaming: {
        bufferingGoal: Math.min(240, Math.ceil(media.duration)),
        retryParameters: { timeout: 0, stallTimeout: 0, connectionTimeout: 0 },
      } });
      manifestUrl = URL.createObjectURL(new Blob([media.mpd], { type: "application/dash+xml" }));
      await instance.load(manifestUrl);
      video.pause();
    } catch (error) {
      await unload();
      core.setFatalMediaError("bilibiliDashError", t("room.playback.errors.playFailed"), {
        detail: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  }

  onBeforeUnmount(() => { void unload(); });
  return { loadSource, unload };
}
