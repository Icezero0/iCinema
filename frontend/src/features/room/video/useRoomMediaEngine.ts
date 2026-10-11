import { ref } from "vue";
import { useDirectVideoEngine } from "./useDirectVideoEngine";
import { useHlsEngine } from "./useHlsEngine";
import { useLocalFileEngine } from "./useLocalFileEngine";
import { useBilibiliDashEngine } from "./useBilibiliDashEngine";
import type { BilibiliLocalMedia } from "@/infra/bilibili-desktop";
import { useNativeVideoCore } from "./useNativeVideoCore";
import {
  classifyMediaEngineSource,
  type MediaEngine,
  type MediaEngineLoadInput,
  type MediaEngineSource,
} from "./mediaEngineTypes";
import { ROOM_PLAYER_CONFIG, type RoomPlayerConfig } from "./playerConfig";
import type { MediaEngineLogger, PlaybackStateInput } from "./types";

export function useRoomMediaEngine(options: {
  writeLog: MediaEngineLogger;
  config?: RoomPlayerConfig;
}): MediaEngine {
  const sourceType = ref<MediaEngineSource["sourceType"] | "none">("none");
  const engineKind = ref<MediaEngineSource["engineKind"] | "none">("none");
  const core = useNativeVideoCore({
    writeLog: options.writeLog,
    config: options.config ?? ROOM_PLAYER_CONFIG,
  });
  const hlsEngine = useHlsEngine(core, {
    writeLog: options.writeLog,
    config: options.config ?? ROOM_PLAYER_CONFIG,
  });
  const directVideoEngine = useDirectVideoEngine(core);
  const localFileEngine = useLocalFileEngine(core);
  const bilibiliDashEngine = useBilibiliDashEngine(core);

  async function loadSource(
    input: MediaEngineLoadInput | string,
    playback: PlaybackStateInput | null = null,
  ) {
    await unloadActiveEngines();

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
      core.sourceUrl.value = "";
      await core.loadSource("", playback, "direct_video");
      return;
    }

    sourceType.value = source.sourceType;
    engineKind.value = source.engineKind;

    if (source.sourceType === "local_file") {
      await localFileEngine.loadFile(source.file, playback);
      return;
    }

    if (source.engineKind === "hls") {
      await hlsEngine.loadSource(source.url, playback);
      return;
    }

    await directVideoEngine.loadSource(source.url, playback);
  }

  async function loadBilibiliSource(media: BilibiliLocalMedia) {
    await unloadActiveEngines();
    sourceType.value = "bilibili_local";
    engineKind.value = "bilibili_dash";
    await bilibiliDashEngine.loadSource(media);
  }

  async function unloadActiveEngines() {
    hlsEngine.unload();
    directVideoEngine.unload();
    localFileEngine.unload();
    await bilibiliDashEngine.unload();
  }

  return {
    ...core,
    sourceType,
    engineKind,
    loadSource,
    loadBilibiliSource,
  };
}
