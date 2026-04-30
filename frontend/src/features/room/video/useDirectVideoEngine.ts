import type { PlaybackStateInput } from "./types";
import type { NativeVideoCore } from "./useNativeVideoCore";

export function useDirectVideoEngine(core: NativeVideoCore) {
  async function loadSource(url: string, playback: PlaybackStateInput | null = null) {
    core.sourceUrl.value = url;
    await core.loadSource(url, playback, "direct_video");
  }

  return {
    loadSource,
    unload: () => {},
  };
}
