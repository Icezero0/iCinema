<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import axios from 'axios';
import { getRoomOmofun, resolveRoomOmofun, type OmofunResult, type RoomOmofunState } from '@/infra/api/omofun.api';
import type { OmofunSelection } from '@/infra/realtime/roomRealtime';
import { getBackendErrorReason } from '@/infra/http/client';
import { useToastsStore } from '@/stores/toasts.store';
import BaseDialog from '@/ui/base/BaseDialog.vue';
import BaseInput from '@/ui/base/BaseInput.vue';
import BaseButton from '@/ui/base/BaseButton.vue';
import BaseCard from '@/ui/base/BaseCard.vue';

const props = defineProps<{
  roomId: number;
  current?: OmofunSelection | null; sourceRevision: number; active: boolean;
  applying?: boolean; canApply?: boolean; closeKey?: number;
}>();
const emit = defineEmits<{
  (e: 'select', selection: OmofunSelection, expectedRevision: number): void;
  (e: 'dialog-change', open: boolean): void;
}>();
const { t, te } = useI18n(), toasts = useToastsStore();
const input = ref(''), state = ref<RoomOmofunState | null>(null);
const result = ref<OmofunResult | null>(null);
const busy = ref(false), dialogOpen = ref(false), selected = ref('');
const expectedRevision = ref(0);
const episode = computed(() => result.value?.snapshot?.episodes.find(item => item.id === selected.value));
const parsing = computed(() => busy.value || state.value?.state === 'parsing');
const progressData = computed(() => state.value?.progress);
const progress = computed(() => progressData.value?.total ? Math.round(progressData.value.completed / progressData.value.total * 100) : 0);
const statusKey = computed(() => ['ready', 'failed'].includes(state.value?.state ?? '') ? state.value!.state : 'empty');
const reparse = computed(() => {
  if (state.value?.state !== 'ready' || !state.value.result?.snapshot) return false;
  const value = input.value.trim();
  let workId = /^[1-9][0-9]{0,19}$/.test(value) ? value : '';
  if (!workId) {
    try {
      const url = new URL(value);
      if (!['http:', 'https:'].includes(url.protocol) || url.hostname !== 'omofun.in'
        || url.username || url.password || url.port || /[\\\s]/.test(value)) return false;
      const match = url.pathname.match(/^\/vod\/(?:detail\/([1-9][0-9]{0,19})\.html|play\/([1-9][0-9]{0,19})(?:\/(?:ep[0-9]+(?:\.[0-9]+)?)\.html|\.html|\/)?)$/);
      workId = match?.[1] ?? match?.[2] ?? '';
    } catch { return false; }
  }
  return workId === state.value.result.work_id;
});
let alive = true, generation = 0, failures = 0, initialized = false, edited = false;
let timer: ReturnType<typeof setTimeout> | undefined;

function error(reason: string) {
  toasts.push({ message: t(te(`omofun.errors.${reason}`) ? `omofun.errors.${reason}` : 'omofun.errors.request'), tone: 'danger' });
}
function accept(data: RoomOmofunState) {
  state.value = data;
  if (!initialized && !edited) input.value = data.work_id ?? '';
  initialized = true;
}
function poll(request: number, delay = 2000) {
  clearTimeout(timer);
  if (!props.active || !alive) return;
  timer = setTimeout(async () => {
    try {
      const data = await getRoomOmofun(props.roomId);
      if (!alive || request !== generation) return;
      failures = 0; accept(data);
      poll(request, data.state === 'parsing' ? 2000 : 5000);
    } catch (err) {
      if (!alive || request !== generation) return;
      failures++;
      if (failures === 3) error(getBackendErrorReason(err));
      if (axios.isAxiosError(err) && [401, 403, 404].includes(err.response?.status ?? 0)) return;
      poll(request, Math.min(30000, 2000 * 2 ** Math.min(failures, 4)));
    }
  }, delay);
}
async function load() {
  if (!input.value.trim() || parsing.value || props.applying || !props.canApply) return;
  const value = input.value.trim(), force = reparse.value, request = ++generation;
  clearTimeout(timer); busy.value = true; failures = 0;
  try {
    const data = await resolveRoomOmofun(props.roomId, value, force);
    if (!alive || request !== generation) return;
    accept(data);
    if (force && data.state !== 'parsing' && (data.result?.retry_after ?? 0) > 0) {
      toasts.push({ message: t('omofun.cooldown', { seconds: data.result!.retry_after }) });
    }
  } catch (err) {
    if (alive && request === generation) error(getBackendErrorReason(err));
  } finally { if (alive && request === generation) { busy.value = false; poll(request); } }
}
function openEpisodes() {
  if (!state.value?.result?.snapshot) return;
  result.value = state.value.result;
  selected.value = result.value.work_id === props.current?.work_id ? props.current.episode_id : '';
  expectedRevision.value = props.sourceRevision;
  dialogOpen.value = true;
}
function choose(lineId: string) {
  if (!result.value?.snapshot || !episode.value || props.applying || !props.canApply) return;
  emit('select', { work_id: result.value.work_id, episode_id: episode.value.id,
    line_id: lineId, cache_version: result.value.version }, expectedRevision.value);
}
function edit(value: string) {
  input.value = value;
  edited = true;
}
watch(dialogOpen, open => emit('dialog-change', open));
watch(() => props.closeKey, () => { dialogOpen.value = false; });
watch(() => props.active, active => {
  if (!active) { dialogOpen.value = false; clearTimeout(timer); }
  else if (!busy.value) poll(generation, 0);
}, { immediate: true });
onBeforeUnmount(() => { alive = false; generation++; clearTimeout(timer); emit('dialog-change', false); });
</script>

<template>
  <div class="omofunControl">
    <BaseInput :model-value="input" :aria-label="t('omofun.workId')" :placeholder="t('omofun.placeholder')"
      maxlength="2048" :disabled="busy || applying" @update:model-value="edit" @keydown.enter.prevent="load()" />
    <div class="currentStatus" role="status"><span>{{ t(`omofun.states.${statusKey}`) }}</span><strong v-if="state?.state === 'ready'">{{ state.result?.snapshot?.title }}</strong></div>
    <div v-if="parsing" class="parseProgress" role="progressbar" :aria-label="t('omofun.states.parsing')"
      :aria-valuemin="0" :aria-valuemax="100" :aria-valuenow="progressData?.total ? progress : undefined">
      <div class="progressTrack"><span :class="{ pending: !progressData?.total }" :style="{ width: `${progressData?.total ? progress : 25}%` }" /></div>
      <span>{{ progressData?.total ? `${progressData.completed} / ${progressData.total}` : t('omofun.states.parsing') }}</span>
    </div>
    <div class="actions">
      <BaseButton :disabled="!input.trim() || parsing || applying || !canApply" @click="load()">{{ t(reparse ? 'omofun.refresh' : 'omofun.open') }}</BaseButton>
      <BaseButton :disabled="!state?.result?.snapshot || applying" variant="primary" @click="openEpisodes">{{ t('omofun.openEpisodes') }}</BaseButton>
    </div>
    <BaseDialog v-model="dialogOpen" :max-width="800" :z-index="120" :aria-label="t('omofun.openEpisodes')">
      <BaseCard class="episodeDialog">
        <header><h2>{{ result?.snapshot?.title || t('omofun.openEpisodes') }}</h2><BaseButton @click="dialogOpen = false">{{ t('common.close') }}</BaseButton></header>
        <p v-if="!result?.snapshot" role="status" class="status">{{ t(parsing ? 'omofun.states.parsing' : 'omofun.noEpisodesYet') }}</p>
        <template v-else>
          <div class="episodeGrid">
            <BaseButton v-for="item in result.snapshot.episodes" :key="item.id" :id="`omofun-${item.id}`"
              :variant="selected === item.id ? 'primary' : 'default'" :title="item.title" :aria-label="item.title || item.number"
              :aria-expanded="selected === item.id" :disabled="applying" @click="selected = item.id">{{ item.number }}</BaseButton>
          </div>
          <BaseCard v-if="episode" class="lineCard" role="region" :aria-labelledby="`omofun-${episode.id}`">
            <h3>{{ episode.title || episode.number }}</h3>
            <p v-if="episode.skipped_lines" class="status">{{ t('omofun.skipped', { count: episode.skipped_lines }) }}</p>
            <div class="lineGrid"><BaseButton v-for="line in episode.lines" :key="line.id"
              :disabled="applying || !canApply" :variant="current?.work_id === result.work_id && current?.episode_id === episode.id && current?.line_id === line.id ? 'primary' : 'default'"
              :aria-label="t('omofun.playLine', { name: line.source.slice(0, 2).toUpperCase() })"
              @click="choose(line.id)">{{ t('omofun.lineName', { name: line.source.slice(0, 2).toUpperCase() }) }}</BaseButton></div>
          </BaseCard>
        </template>
      </BaseCard>
    </BaseDialog>
  </div>
</template>

<style scoped>
.omofunControl { display: grid; gap: 10px; min-width: 0; }
.omofunControl > input { width: 100%; min-width: 0; box-sizing: border-box; font-size: 12px; }
.actions { display: flex; justify-content: flex-end; gap: 8px; }
.currentStatus { display: flex; flex-wrap: wrap; gap: 6px 12px; font-size: 12px; color: var(--c-text-muted); overflow-wrap: anywhere; }
.currentStatus strong { color: var(--c-text); font-weight: 500; }
.actions :deep(button) { min-height: 34px; height: 34px; font-size: 12px; padding: 0 10px; }
.parseProgress { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 10px; font-size: 12px; color: var(--c-text-muted); }
.progressTrack { height: 5px; overflow: hidden; border-radius: 5px; background: var(--c-border); }
.progressTrack span { display: block; height: 100%; background: var(--c-primary); transition: width .2s; }
.progressTrack .pending { animation: progress 1.4s ease-in-out infinite alternate; }
@keyframes progress { to { transform: translateX(300%); } }
@media (prefers-reduced-motion: reduce) { .progressTrack .pending { animation: none; } }
.episodeDialog { padding: 24px; max-height: min(75dvh, 720px); overflow: auto; }
header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
h2, h3 { margin: 0; font-size: 16px; overflow-wrap: anywhere; }
.episodeGrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(56px, 1fr)); gap: 10px; margin-top: 24px; }
.lineCard { margin-top: 24px; padding: 20px; }
.lineCard :deep(.lineGrid) { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
.status { font-size: 13px; color: var(--c-text-muted); }
@media (max-width: 640px) { .episodeDialog { padding: 16px; } }
</style>
