<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import axios from 'axios';
import { getCatalogGraph, type CatalogGraph, type CatalogEpisode } from '@/infra/api/catalog.api';
import { useToastsStore } from '@/stores/toasts.store';
import AppPageShell from '@/ui/layout/AppPageShell.vue';
import BaseCard from '@/ui/base/BaseCard.vue';
import BaseButton from '@/ui/base/BaseButton.vue';

const route = useRoute(), { t } = useI18n(), toasts = useToastsStore();
const graph = ref<CatalogGraph | null>(null), loading = ref(false);
const selectedId = ref<number | null>(null), copyingId = ref<number | null>(null);
let generation = 0, alive = true;
const episodes = computed(() => [...(graph.value?.episodes ?? [])].sort((a, b) => a.number - b.number || a.sort_order - b.sort_order || a.id - b.id));
const selectedEpisode = computed(() => episodes.value.find(episode => episode.id === selectedId.value));
const availableLines = computed(() => {
  const episode = selectedEpisode.value, data = graph.value;
  if (!episode || !data || data.content.disabled || episode.disabled) return [];
  return data.lines.filter(line => !line.disabled).flatMap(line => {
    const playback = data.playbacks.find(item => item.episode_id === episode.id && item.line_id === line.id && !item.disabled && item.media_type === 'hls' && item.url);
    return playback ? [{ ...line, playback }] : [];
  }).sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
});
function episodeLabel(episode: CatalogEpisode) {
  return episode.kind === 'episode'
    ? t('catalogDetail.episodeNumber', { number: episode.number })
    : `${t(`catalogDetail.kinds.${episode.kind}`)} ${episode.number}`;
}
function toggleEpisode(id: number) { selectedId.value = selectedId.value === id ? null : id; }
async function load() {
  const request = ++generation;
  loading.value = true;
  try {
    const result = await getCatalogGraph(Number(route.params.id));
    if (!alive || request !== generation) return;
    graph.value = result;
    if (!result.episodes.some(episode => episode.id === selectedId.value)) selectedId.value = null;
  } catch (err) {
    if (!alive || request !== generation) return;
    toasts.push({ message: t(axios.isAxiosError(err) && err.response?.status === 404 ? 'catalogAdmin.errors.missing' : 'catalogAdmin.errors.request'), tone: 'danger' });
  } finally { if (alive && request === generation) loading.value = false; }
}
async function copyLine(id: number, url: string) {
  if (copyingId.value !== null) return;
  copyingId.value = id;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(url);
    } else {
      // Support local HTTP environments without displaying the address.
      const previous = document.activeElement as HTMLElement | null;
      const textarea = document.createElement('textarea');
      textarea.value = url;
      textarea.readOnly = true;
      textarea.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0';
      document.body.appendChild(textarea);
      try {
        textarea.select();
        if (!document.execCommand('copy')) throw new Error('Copy failed');
      } finally { textarea.remove(); previous?.focus(); }
    }
    if (alive) toasts.push({ message: t('catalogDetail.linkCopied'), tone: 'success' });
  } catch {
    if (alive) toasts.push({ message: t('catalogDetail.linkCopyFailed'), tone: 'danger' });
  } finally { copyingId.value = null; }
}
watch(() => route.params.id, () => { graph.value = null; selectedId.value = null; void load(); }, { immediate: true });
onBeforeUnmount(() => { alive = false; generation++; });
</script>

<template>
  <AppPageShell :title="graph?.content.title ?? t('catalogDetail.title')" back-to="/admin/videos" :back-text="t('catalogAdmin.title')" :max-width="1040">
    <template #actions><BaseButton :disabled="loading" @click="load">{{ t('catalogDetail.refresh') }}</BaseButton></template>
    <p v-if="loading && !graph" role="status">{{ t('common.loading') }}</p>
    <BaseCard v-if="graph" class="episodesCard">
      <h2>{{ t('catalogDetail.episodes') }}</h2>
      <p v-if="!episodes.length" class="empty">{{ t('catalogDetail.noEpisodes') }}</p>
      <div v-else class="episodeGrid">
        <BaseButton v-for="episode in episodes" :id="`episode-${episode.id}`" :key="episode.id"
          class="episodeButton" :variant="selectedId === episode.id ? 'primary' : 'default'"
          :aria-expanded="selectedId === episode.id" :aria-controls="selectedId === episode.id ? 'episode-lines' : undefined"
          :aria-label="episodeLabel(episode)" :title="episode.title" @click="toggleEpisode(episode.id)">
          {{ episode.number }}
        </BaseButton>
      </div>
      <BaseCard v-if="selectedEpisode" id="episode-lines" class="linesCard" role="region" :aria-labelledby="`episode-${selectedEpisode.id}`">
        <h3>{{ episodeLabel(selectedEpisode) }}</h3>
        <p v-if="!availableLines.length" class="empty">{{ t('catalogDetail.noAvailableLines') }}</p>
        <div v-else class="lineGrid">
          <BaseButton v-for="line in availableLines" :key="line.playback.id" class="lineButton"
            :loading="copyingId === line.playback.id" :disabled="copyingId !== null"
            :aria-label="t('catalogDetail.copyLine', { name: line.display_name || line.name })"
            @click="copyLine(line.playback.id, line.playback.url)">
            {{ line.display_name || line.name }}
          </BaseButton>
        </div>
      </BaseCard>
    </BaseCard>
  </AppPageShell>
</template>

<style scoped>
.episodesCard { padding: 24px; }
.episodesCard :deep(h2), .episodesCard :deep(h3) { margin: 0; font-size: 15px; font-weight: 650; }
.episodesCard :deep(.episodeGrid) {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
  gap: 12px;
  margin-top: 20px;
}
.episodesCard :deep(.episodeButton) {
  width: 100%; min-width: 0; height: 44px; padding: 0 8px;
  font-variant-numeric: tabular-nums; font-size: 14px;
}
.episodesCard :deep(.linesCard) { margin-top: 24px; padding: 20px; background: var(--c-bg); }
.episodesCard :deep(.lineGrid) { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 16px; }
.episodesCard :deep(.lineButton) { min-width: 144px; max-width: 100%; height: auto; min-height: 40px; padding: 10px 16px; line-height: 1.5; overflow-wrap: anywhere; }
.episodesCard :deep(.empty) { padding: 16px 0; text-align: center; font-size: 13px; color: var(--c-muted); }
.error { color: var(--c-danger); }
@media (max-width: 640px) {
  .episodesCard { padding: 16px; }
  .episodesCard :deep(.episodeGrid) { grid-template-columns: repeat(auto-fill, minmax(52px, 1fr)); gap: 8px; margin-top: 16px; }
  .episodesCard :deep(.linesCard) { margin-top: 20px; padding: 16px; }
  .episodesCard :deep(.lineButton) { min-width: 0; }
}
</style>
