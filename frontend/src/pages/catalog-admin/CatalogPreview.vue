<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import type { CatalogPreview } from '@/infra/api/catalog.api';
import { useNativeVideoCore } from '@/features/room/video/useNativeVideoCore';
import { useHlsEngine } from '@/features/room/video/useHlsEngine';
import { ROOM_PLAYER_CONFIG } from '@/features/room/video/playerConfig';

const props = defineProps<{ source: CatalogPreview }>();
const { t } = useI18n();
// Reuse the room's playback engines without connecting room state or WebSockets.
// A paused metadata-only preview must not trigger the room's no-progress timeout.
const config = { ...ROOM_PLAYER_CONFIG, stallingToErrorMs: 0 };
const core = useNativeVideoCore({ writeLog: () => {}, config });
const hls = useHlsEngine(core, { writeLog: () => {}, config });
const { videoRef, mediaHealthState } = core;
function setVideo(element: unknown) { videoRef.value = element as HTMLVideoElement | null; }
const failed = ref(false);
onMounted(async () => {
  try {
    if (props.source.media_type === 'hls') await hls.loadSource(props.source.url);
    else await core.loadSource(props.source.url, null, 'direct_video');
  } catch { failed.value = true; }
});
</script>

<template>
  <div>
    <video :ref="setVideo" controls playsinline preload="metadata"
      @error="core.handleVideoError" @loadedmetadata="core.handleVideoEvent('loadedmetadata')"
      @canplay="core.handleVideoEvent('canplay')" @playing="core.handleVideoEvent('playing')"
      @pause="core.handleVideoEvent('pause')" @waiting="core.handleVideoEvent('waiting')"
      @timeupdate="core.handleTimeUpdate" @progress="core.handleProgress" />
    <p v-if="failed || mediaHealthState === 'error'" role="alert" class="error">{{ t('catalogDetail.previewFailed') }}</p>
  </div>
</template>

<style scoped>
video { display: block; width: 100%; max-height: 60dvh; background: #000; border-radius: var(--r-2); }
.hint { color: var(--c-text-muted); font-size: 13px; line-height: 1.6; }
.error { color: var(--c-danger); }
</style>
