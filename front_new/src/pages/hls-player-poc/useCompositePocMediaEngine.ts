import { onBeforeUnmount, ref } from "vue";
import { useHlsPocMediaEngine } from "./useHlsPocMediaEngine";
import {
  classifyMediaEngineSource,
  type MediaEngine,
  type MediaEngineLoadInput,
  type MediaEngineSource,
} from "./mediaEngineTypes";
import { HLS_POC_PLAYER_CONFIG, type HlsPocPlayerConfig } from "./playerConfig";
import type { PlaybackStateInput, PocLogger } from "./types";

export function useCompositePocMediaEngine(options: {
  writeLog: PocLogger;
  config?: HlsPocPlayerConfig;
}): MediaEngine {
  const sourceType = ref<MediaEngineSource["sourceType"] | "none">("none");
  const engineKind = ref<MediaEngineSource["engineKind"] | "none">("none");
  const hlsEngine = useHlsPocMediaEngine({
    writeLog: options.writeLog,
    config: options.config ?? HLS_POC_PLAYER_CONFIG,
  });

  let activeObjectUrl: string | null = null;

  async function loadSource(
    input: MediaEngineLoadInput | string,
    playback: PlaybackStateInput | null = null,
  ) {
    releaseObjectUrl();

    const source = typeof input === "string"
      ? classifyMediaEngineSource({
        sourceType: "external_url",
        externalUrl: input,
        localFile: null,
      })
      : classifyMediaEngineSource(input);

    if (!source) {
      sourceType.value = "none";
      engineKind.value = "none";
      hlsEngine.sourceUrl.value = "";
      await hlsEngine.loadSource("", playback);
      return;
    }

    sourceType.value = source.sourceType;
    engineKind.value = source.engineKind;

    if (source.sourceType === "local_file") {
      activeObjectUrl = source.objectUrl;
      hlsEngine.sourceUrl.value = source.file.name;
      await hlsEngine.loadSource(source.objectUrl, playback);
      return;
    }

    hlsEngine.sourceUrl.value = source.url;
    await hlsEngine.loadSource(source.url, playback);
  }

  function releaseObjectUrl() {
    if (!activeObjectUrl) return;

    URL.revokeObjectURL(activeObjectUrl);
    activeObjectUrl = null;
  }

  onBeforeUnmount(() => {
    releaseObjectUrl();
  });

  return {
    ...hlsEngine,
    sourceType,
    engineKind,
    loadSource,
  };
}
