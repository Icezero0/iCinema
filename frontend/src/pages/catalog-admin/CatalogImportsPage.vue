<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { listImports, getImport, importAction, discoverWorks, selectWorks, type ImportJob, type ImportItem } from '@/infra/api/catalog-imports.api';
import { listCategories, type CatalogCategory } from '@/infra/api/catalog.api';
import BaseInput from '@/ui/base/BaseInput.vue';
import BaseSelect from '@/ui/base/BaseSelect.vue';
import BaseSwitch from '@/ui/base/BaseSwitch.vue';
import BaseDateInput from '@/ui/base/BaseDateInput.vue';
import BaseDialog from '@/ui/base/BaseDialog.vue';
import { getBackendErrorReason } from '@/infra/http/client';
import { formatLocalDateTime } from '@/utils/datetime';
import AppPageShell from '@/ui/layout/AppPageShell.vue';
import BaseButton from '@/ui/base/BaseButton.vue';
import BaseCard from '@/ui/base/BaseCard.vue';
import BasePill from '@/ui/base/BasePill.vue';
import BaseConfirmDialog from '@/ui/base/BaseConfirmDialog.vue';
import { useToastsStore } from '@/stores/toasts.store';
import RowListItem from '@/ui/base/RowListItem.vue';

const { t, te } = useI18n(), route = useRoute(), router = useRouter();
const jobs = ref<ImportJob[]>([]), selected = ref<ImportJob | null>(null), page = ref(1), totalPages = ref(0);
const loading = ref(false), busy = ref(false);
const toasts = useToastsStore();
function notifyError(key: string) { toasts.push({ message: t(key), tone: 'danger' }); }
const confirmOpen = ref(false), pendingAction = ref<'start' | 'retry' | 'cancel'>('start');
const stoppingSearch = ref(false);
const confirmationKey = computed(() => stoppingSearch.value ? 'stopSearch' : pendingAction.value);
const canSelectResults = computed(() => !!selected.value && selected.value.query.phase === 'search' && ['preview', 'queued', 'running', 'cancelled'].includes(selected.value.status));
function rowSelectable(item: ImportItem) { return canSelectResults.value && !item.blocked && !busy.value; }
function toggleRow(item: ImportItem, event: Event) {
  if (!rowSelectable(item) || (event.target as HTMLElement).closest('button, a, details, input')) return;
  toggle(item.key, !checked.value.includes(item.key));
}
const detailPanel = ref<HTMLElement>();
let returnFocus: HTMLElement | null = null;
function closeDetail() {
  if (busy.value || confirmOpen.value) return;
  const query = { ...route.query }; delete query.job;
  void router.replace({ query }).then(() => returnFocus?.focus());
}
function trapFocus(event: KeyboardEvent) {
  if (event.key !== 'Tab' || confirmOpen.value) return;
  const nodes = Array.from(detailPanel.value?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), summary, a[href], [tabindex="0"]') ?? []).filter(el => el.getClientRects().length);
  if (event.shiftKey && document.activeElement === nodes[0]) { event.preventDefault(); nodes[nodes.length - 1]?.focus(); }
  else if (!event.shiftKey && document.activeElement === nodes[nodes.length - 1]) { event.preventDefault(); nodes[0]?.focus(); }
}
watch(() => selected.value?.id, async (id, oldId) => {
  if (id && !oldId) { returnFocus = document.activeElement as HTMLElement; await nextTick(); detailPanel.value?.querySelector<HTMLButtonElement>('button')?.focus(); }
});
watch(confirmOpen, async (value, previous) => {
  if (!value && previous) { await nextTick(); detailPanel.value?.querySelector<HTMLButtonElement>('button')?.focus(); }
});
const name = ref(''), category = ref(''), updatedFrom = ref(''), updatedTo = ref('');
const categories = ref<CatalogCategory[]>([]), checked = ref<string[]>([]), resultPage = ref(1);
const categoryOptions = computed(() => categories.value.map(c => ({ value: c.code, label: te(`catalogAdmin.categories.${c.code}`) ? t(`catalogAdmin.categories.${c.code}`) : c.name })));
const visibleItems = computed(() => selected.value?.items.slice((resultPage.value - 1) * 20, resultPage.value * 20) ?? []);
const resultPages = computed(() => Math.max(1, Math.ceil((selected.value?.items.length ?? 0) / 20)));
const selectable = computed(() => selected.value?.items.filter(i => !i.blocked).map(i => i.key) ?? []);
const allChecked = computed(() => selectable.value.length > 0 && selectable.value.every(key => checked.value.includes(key)));
function toggle(key: string, value: boolean) { checked.value = value ? [...new Set([...checked.value, key])] : checked.value.filter(k => k !== key); }
async function search() {
  if (busy.value || !category.value) return;
  if (updatedFrom.value && updatedTo.value && updatedFrom.value > updatedTo.value) { notifyError('catalogAdmin.errors.validation'); return; }
  busy.value = true;
  try {
    const job = await discoverWorks({ name: name.value, category: category.value, updated_from: updatedFrom.value || null, updated_to: updatedTo.value || null });
    if (alive) await router.replace({ query: { job: job.id } });
  } catch (e) { if (alive) notifyError(errorKey(e)); }
  finally { busy.value = false; }
}
function statusLabel(job: ImportJob) {
  if (job.query.phase === 'search') {
    if (active(job)) return t('catalogImport.searching');
    if (job.status === 'failed') return t('catalogImport.searchFailed');
  }
  return t(`catalogImport.statuses.${job.status}`);
}
let readFailures = 0;
let alive = true, generation = 0, timer: ReturnType<typeof setTimeout> | null = null, actionId = 0;
let actionKeys: string[] = [], aggregateAction = false;
const completed = computed(() => selected.value?.items.filter(item => item.status !== 'pending').length ?? 0);
const active = (job: ImportJob) => ['queued', 'running'].includes(job.status);
function reasonLabel(value: string) {
  if (!value) return '';
  const split = value.indexOf(':');
  const code = split < 0 ? value : value.slice(0, split);
  const key = `catalogImport.errors.${code}`;
  return (te(key) ? t(key) : t('catalogImport.errors.catalog_import_data')) + (split < 0 ? '' : value.slice(split));
}
function errorKey(e: unknown) { const key = `catalogImport.errors.${getBackendErrorReason(e)}`; return te(key) ? key : 'catalogAdmin.errors.request'; }
async function load() {
  if (timer) clearTimeout(timer);
  const request = ++generation;
  loading.value = true;
  try {
    const result = await listImports(page.value);
    if (!alive || request !== generation) return;
    jobs.value = result.items; totalPages.value = result.total_pages;
    const id = Number(route.query.job);
    const detail = id > 0 && Number.isInteger(id) ? await getImport(id) : null;
    if (!alive || request !== generation) return;
    selected.value = detail;
    if (!categories.value.length) {
      const rows = await listCategories();
      if (!alive || request !== generation) return;
      categories.value = rows; category.value = rows[0]?.code ?? '';
    }
    readFailures = 0;
  } catch { if (alive && request === generation) readFailures++; }
  finally {
    if (alive && request === generation) {
      loading.value = false;
      if (readFailures || jobs.value.some(active) || (selected.value && active(selected.value))) {
        timer = setTimeout(() => void load(), readFailures ? Math.min(3000 * 2 ** Math.min(readFailures - 1, 4), 30000) : 3000);
      }
    }
  }
}
function ask(action: 'start' | 'retry' | 'cancel') {
  if (!selected.value || busy.value) return;
  actionId = selected.value.id; pendingAction.value = action; confirmOpen.value = true;
  stoppingSearch.value = action === 'cancel' && selected.value.query.phase === 'search' && active(selected.value);
  actionKeys = [...checked.value]; aggregateAction = !!selected.value.query.phase;
}
async function execute() {
  busy.value = true;
  try {
    if (pendingAction.value === 'start' && aggregateAction) await selectWorks(actionId, actionKeys);
    else await importAction(actionId, pendingAction.value);
    if (alive) { checked.value = []; await load(); }
  }
  catch (e) { if (alive) notifyError(errorKey(e)); }
  finally { busy.value = false; }
}
watch(() => route.query.job, () => { selected.value = null; checked.value = []; resultPage.value = 1; void load(); }, { immediate: true });
onBeforeUnmount(() => { alive = false; generation++; if (timer) clearTimeout(timer); });
</script>

<template>
  <AppPageShell :title="t('catalogImport.jobs')" back-to="/admin/videos" :back-text="t('catalogAdmin.title')" :max-width="1040">
    <template #actions><BaseButton :disabled="busy || loading" @click="load">{{ t('catalogDetail.refresh') }}</BaseButton></template>
    <div class="panels">
    <BaseCard class="card"><form @submit.prevent="search">
      <h2 class="sectionTitle">{{ t('catalogImport.searchTitle') }}</h2>
      <div class="filters">
        <label class="field"><span>{{ t('catalogImport.searchName') }}</span><BaseInput v-model="name" :disabled="busy" maxlength="255" /></label>
        <BaseSelect v-model="category" :options="categoryOptions" :label="t('catalogImport.categoryMapping')" :disabled="busy" />
        <div class="field"><span>{{ t('catalogImport.updatedFrom') }}</span><BaseDateInput v-model="updatedFrom" :label="t('catalogImport.updatedFrom')" :disabled="busy" /></div>
        <div class="field"><span>{{ t('catalogImport.updatedTo') }}</span><BaseDateInput v-model="updatedTo" :label="t('catalogImport.updatedTo')" :disabled="busy" /></div>
      </div><div class="actions footer"><BaseButton type="submit" variant="primary" :disabled="busy || !category" :loading="busy">{{ t('catalogImport.search') }}</BaseButton></div>
    </form></BaseCard>
    <BaseDialog :model-value="!!selected" :max-width="960" :close-on-overlay="!busy && !confirmOpen" :close-on-esc="!busy && !confirmOpen" :aria-label="t('catalogImport.taskDetails')" @update:model-value="closeDetail">
    <section v-if="selected" ref="detailPanel" class="taskDialog" @keydown="trapFocus">
      <div class="header"><h2>{{ t('catalogImport.jobTitle', { id: selected.id }) }}</h2><div class="actions"><BasePill>{{ statusLabel(selected) }}</BasePill><BaseButton :disabled="busy" @click="closeDetail">{{ t('catalogAdmin.close') }}</BaseButton></div></div>
      <template v-if="selected.query.phase">
        <p class="muted">{{ t('catalogImport.criteria', { name: selected.query.criteria?.name || '—', from: selected.query.criteria?.updated_from || '—', to: selected.query.criteria?.updated_to || '—' }) }}</p>
        <p role="status" class="muted">{{ t('catalogImport.scanProgress', { scanned: selected.query.scanned ?? 0, count: selected.items.length }) }} · {{ selected.query.complete ? t('catalogImport.completeScope') : t('catalogImport.incompleteScope') }}</p>
        <p v-for="failure in selected.query.failures" :key="failure.name" class="error">{{ failure.name }}: {{ reasonLabel(failure.reason) }}</p>
      </template>
      <p v-if="selected.query.phase !== 'search'" class="muted">{{ t('catalogImport.progress', { done: completed, total: selected.items.length }) }}</p>
      <p v-for="warning in selected.warnings" :key="warning" class="muted">{{ reasonLabel(warning) }}</p>
      <div class="actions footer">
        <BaseSwitch v-if="canSelectResults" :model-value="allChecked" :disabled="busy || !selectable.length" @update:model-value="checked = $event ? [...selectable] : []">{{ t('catalogImport.selectAll', { count: checked.length }) }}</BaseSwitch>
        <BaseButton v-if="canSelectResults || selected.status === 'preview'" variant="primary" :disabled="busy || (!!selected.query.phase && !checked.length)" @click="ask('start')">{{ t('catalogImport.start') }}</BaseButton>
        <BaseButton v-if="['failed', 'partial', 'interrupted', 'cancelled'].includes(selected.status)" :disabled="busy" @click="ask('retry')">{{ t('catalogImport.retry') }}</BaseButton>
        <BaseButton v-if="['preview', 'queued', 'running'].includes(selected.status)" :disabled="busy" @click="ask('cancel')">{{ t(selected.query.phase === 'search' && active(selected) ? 'catalogImport.stopSearch' : 'catalogImport.cancel') }}</BaseButton>
      </div>
      <div class="results">
      <RowListItem v-for="item in visibleItems" :key="item.key || item.upstream_id" dense class="resultRow" :class="{ chosen: checked.includes(item.key), selectable: rowSelectable(item) }" :interactive="rowSelectable(item)"
        :tabindex="rowSelectable(item) ? 0 : undefined" :role="rowSelectable(item) ? 'button' : undefined" :aria-pressed="rowSelectable(item) ? checked.includes(item.key) : undefined" :aria-label="rowSelectable(item) ? t('catalogImport.selectWork', { title: item.title }) : undefined"
        @click="toggleRow(item, $event)" @keydown.enter.self.prevent="toggleRow(item, $event)" @keydown.space.self.prevent="toggleRow(item, $event)">
        <div class="resultTitle"><strong>{{ item.title }}</strong>
          <template v-if="selected.query.phase">
            <BasePill size="sm" :tone="item.content_id ? 'accent' : 'muted'">{{ t(item.content_id ? 'catalogImport.alreadyExists' : 'catalogImport.notExists') }}</BasePill>
          </template>
          <BasePill v-if="item.status !== 'pending'" size="sm">{{ t(`catalogImport.statuses.${item.status}`) }}</BasePill>
        </div>
        <template v-if="selected.query.phase">
          <p class="muted">{{ t('catalogImport.sourceCount', { count: item.line_count }) }} · {{ t('catalogImport.episodeCount', { count: item.episode_count }) }} · {{ t('catalogImport.newEpisodeCount', { count: item.new_episodes }) }}</p>
          <p v-if="item.blocked && !item.reason" class="error">{{ t(`catalogImport.matches.${item.match}`) }}</p>
          <template v-for="source in item.sources" :key="`${source.provider_id}:${source.upstream_id}`">
            <p v-for="(warning, index) in source.warnings" :key="index" class="error">{{ source.provider_name }} · {{ reasonLabel(warning) }}</p>
          </template>
        </template>
        <p v-if="!selected.query.phase" class="muted">{{ t('catalogImport.upstreamId') }} {{ item.upstream_id }} · {{ t('catalogImport.entryCount', { count: item.entries }) }}</p>
        <p v-if="item.reason" class="error">{{ reasonLabel(item.reason) }}</p>
        <p v-for="(warning, index) in item.warnings" :key="index" class="muted">{{ reasonLabel(warning) }}</p>
        <template #right><BaseButton v-if="item.content_id" @click.stop="$router.push(`/admin/videos/${item.content_id}`)">{{ selected.status === 'preview' ? t('catalogImport.existing') : t('catalogImport.openWork') }}</BaseButton></template>
      </RowListItem>
      </div>
      <div class="actions footer"><BaseButton :disabled="resultPage <= 1" @click="resultPage--">{{ t('catalogAdmin.previous') }}</BaseButton><span>{{ resultPage }} / {{ resultPages }}</span><BaseButton :disabled="resultPage >= resultPages" @click="resultPage++">{{ t('catalogAdmin.next') }}</BaseButton></div>
    </section>
    </BaseDialog>
    <BaseCard class="card">
      <h2 class="sectionTitle">{{ t('catalogImport.searchTasks') }}</h2>
      <p v-if="!jobs.length" class="muted">{{ loading ? t('common.loading') : t('catalogImport.empty') }}</p>
      <div class="results">
      <RowListItem v-for="job in jobs" :key="job.id">
        <strong>{{ t('catalogImport.jobTitle', { id: job.id }) }}</strong><p class="muted">{{ formatLocalDateTime(job.created_at) }} · {{ t('catalogImport.itemCount', { count: job.items.length }) }}</p>
        <template #right><div class="actions"><BasePill>{{ statusLabel(job) }}</BasePill><BaseButton :disabled="busy" @click="router.replace({ query: { job: job.id } })">{{ t('catalogImport.view') }}</BaseButton></div></template>
      </RowListItem>
      </div>
      <div class="actions footer"><BaseButton :disabled="loading || page <= 1" @click="page--; load()">{{ t('catalogAdmin.previous') }}</BaseButton><span class="muted">{{ t('catalogAdmin.auditPagination', { page, pages: Math.max(totalPages, 1) }) }}</span><BaseButton :disabled="loading || page >= totalPages" @click="page++; load()">{{ t('catalogAdmin.next') }}</BaseButton></div>
    </BaseCard>
    </div>
    <BaseConfirmDialog v-if="confirmOpen" v-model="confirmOpen" :z-index="90" :lock-scroll="false" :title="t(`catalogImport.${confirmationKey}`)" :message="t(stoppingSearch ? 'catalogImport.stopSearchHint' : pendingAction === 'cancel' ? 'catalogImport.cancelHint' : 'catalogImport.startHint')" :confirm-text="t(`catalogImport.${confirmationKey}`)" :cancel-text="t('common.cancel')" @confirm="execute" />
  </AppPageShell>
</template>

<style scoped>
.panels { display: grid; gap: 20px; } .filters { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.taskDialog { padding: 24px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--r-2); max-height: calc(100dvh - 48px); overflow-y: auto; }
h2.sectionTitle { margin-bottom: 20px; }
.field { display: grid; gap: 8px; font-size: 13px; } .source { margin: 12px; } summary { cursor: pointer; font-size: 13px; margin: 12px 0; }
@media (max-width: 640px) { .filters { grid-template-columns: 1fr; } }
.card { padding: 20px; } .header, .actions { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.header { justify-content: space-between; } .actions { justify-content: flex-end; } .footer { margin: 16px 0; }
h2 { font-size: 16px; margin: 0; } strong { font-size: 14px; overflow-wrap: anywhere; }
.muted { color: var(--c-text-muted); font-size: 12px; line-height: 1.7; overflow-wrap: anywhere; } .error { color: var(--c-danger); font-size: 13px; }
.results { display: grid; gap: var(--s-2); }
.resultTitle { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.resultRow p { margin: 4px 0; } .resultRow summary { margin: 4px 0 0; }
.results .resultRow.selectable, .results .resultRow.selectable :deep(*) { cursor: pointer; }
.resultRow.chosen, .resultRow.chosen.selectable:hover { border-color: var(--c-primary); background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface)); box-shadow: inset 3px 0 var(--c-primary); }
.resultRow:focus-visible { outline: 2px solid var(--c-primary); outline-offset: 2px; }
</style>
