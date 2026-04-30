import { onBeforeUnmount } from "vue";
import type { PlaybackStateInput } from "./types";
import type { NativeVideoCore } from "./useNativeVideoCore";

export function useLocalFileEngine(core: NativeVideoCore) {
  let activeObjectUrl: string | null = null;

  async function loadFile(file: File, playback: PlaybackStateInput | null = null) {
    releaseObjectUrl();
    activeObjectUrl = URL.createObjectURL(file);
    core.sourceUrl.value = file.name;
    await core.loadSource(activeObjectUrl, playback, "local_video");
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
    loadFile,
    unload: releaseObjectUrl,
  };
}
