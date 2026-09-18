<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, reactive, ref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useToastsStore } from '@/stores/toasts.store';
import axios from 'axios';
import {
  createCatalog, getCatalog, getCatalogAudits, listCatalog, listCategories, updateCatalog, deleteCatalog,
  type CatalogContent, type CatalogAudit, type CatalogCategory, type ContentInput, type ContentStatus, type ContentType,
} from '@/infra/api/catalog.api';
import { getBackendErrorReason } from '@/infra/http/client';
import AppPageShell from '@/ui/layout/AppPageShell.vue';
import BaseButton from '@/ui/base/BaseButton.vue';
import BaseCard from '@/ui/base/BaseCard.vue';
import BaseInput from '@/ui/base/BaseInput.vue';
import BaseSwitch from '@/ui/base/BaseSwitch.vue';
import BaseNumberInput from '@/ui/base/BaseNumberInput.vue';
import BaseDialog from '@/ui/base/BaseDialog.vue';
import BaseSelect from '@/ui/base/BaseSelect.vue';
import BasePill from '@/ui/base/BasePill.vue';
import BaseConfirmDialog from '@/ui/base/BaseConfirmDialog.vue';
import RowListItem from '@/ui/base/RowListItem.vue';
import { formatLocalDateTime } from '@/utils/datetime';

const { t, te } = useI18n();
const toasts = useToastsStore();
function notifyError(key: string) { toasts.push({ message: t(key), tone: 'danger' }); return key; }
const types: ContentType[] = ['tv', 'movie', 'ova', 'oad', 'ona', 'special'];
const statuses: ContentStatus[] = ['draft', 'published', 'withdrawn'];
const categories = ref<CatalogCategory[]>([]);
const categoriesLoading = ref(true);
const typeOptions = computed(() => types.map(value => ({ value, label: t(`catalogAdmin.types.${value}`) })));
const statusOptions = computed(() => statuses.map(value => ({ value, label: t(`catalogAdmin.statuses.${value}`) })));
function categoryLabel(code: string) {
  const key = `catalogAdmin.categories.${code}`;
  return te(key) ? t(key) : categories.value.find(item => item.code === code)?.name ?? code;
}
const categoryOptions = computed(() => categories.value.map(item => ({ value: item.code, label: categoryLabel(item.code) })));
const categoryFilters = computed(() => [{ value: '', label: t('catalogAdmin.allCategories') }, ...categoryOptions.value]);
const typeFilters = computed(() => [{ value: '', label: t('catalogAdmin.allTypes') }, ...typeOptions.value]);
const statusFilters = computed(() => [{ value: '', label: t('catalogAdmin.allStatuses') }, ...statusOptions.value]);
const availabilityFilters = computed(() => [
  { value: '', label: t('catalogAdmin.allAvailability') },
  { value: 'enabled', label: t('catalogAdmin.enabled') }, { value: 'disabled', label: t('catalogAdmin.disabled') },
]);
const items = ref<CatalogContent[]>([]);
const page = ref(1), total = ref(0), totalPages = ref(0);
const q = ref(''), category = ref(''), status = ref(''), enabled = ref(''), kind = ref('');
const loading = ref(false), saving = ref(false), opening = ref(false);
const error = ref(''), categoryError = ref('');
const editorOpen = ref(false), editing = ref<CatalogContent | null>(null), editorElement = ref<HTMLElement | null>(null);
const initial = ref('');
const form = reactive({ title: '', aliases: '', category: '', region: '', content_type: 'tv', year: '',
  description: '', status: 'draft', disabled: false, disabled_reason: '' });
const audits = ref<CatalogAudit[]>([]), auditPage = ref(1), auditPages = ref(0), auditError = ref('');
const confirmOpen = ref(false);
const deleteOpen = ref(false);
async function removeResource() {
  if (!editing.value || saving.value || opening.value) return;
  saving.value = true; 
  try {
    await deleteCatalog(editing.value.id, editing.value.version);
    if (!alive) return;
    editorGeneration++; editorOpen.value = false; editing.value = null;
    toasts.push({ message: t('catalogAdmin.deleted'), tone: 'success' });
    await refresh(); void restoreEditorFocus();
  } catch (e) { if (alive) notifyError(errorKey(e)); }
  finally { saving.value = false; }
}
let confirmResolve: ((result: boolean) => void) | null = null;
let listGeneration = 0, editorGeneration = 0;
let alive = true;
let editorTrigger: HTMLElement | null = null;
const currentYear = new Date().getFullYear();

function trapEditorFocus(event: KeyboardEvent) {
  if (event.key !== 'Tab' || confirmOpen.value || deleteOpen.value) return;
  const controls = Array.from(editorElement.value?.querySelectorAll<HTMLElement>(
    'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), summary, [tabindex="0"]',
  ) ?? []).filter(element => element.getClientRects().length > 0);
  const first = controls[0], last = controls[controls.length - 1];
  if (!first || !last) { event.preventDefault(); return; }
  if (event.shiftKey && (document.activeElement === first || document.activeElement === editorElement.value)) {
    event.preventDefault(); last.focus();
  } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}
async function restoreEditorFocus() { await nextTick(); editorTrigger?.focus({ preventScroll: true }); }

function errorKey(err: unknown) {
  const reason = getBackendErrorReason(err);
  if (reason === 'catalog_version_conflict') return 'catalogAdmin.errors.conflict';
  if (reason === 'catalog_category_not_found') return 'catalogAdmin.errors.category';
  if (axios.isAxiosError(err)) {
    if (err.response?.status === 403) return 'catalogAdmin.errors.forbidden';
    if (err.response?.status === 404) return 'catalogAdmin.errors.missing';
    if (err.response?.status === 422) return 'catalogAdmin.errors.validation';
  }
  return 'catalogAdmin.errors.request';
}
function dirty() { return editorOpen.value && JSON.stringify(form) !== initial.value; }
async function allowLeave(): Promise<boolean> {
  if (saving.value || opening.value || confirmResolve || deleteOpen.value) return false;
  if (!dirty()) return true;
  confirmOpen.value = true;
  return new Promise(resolve => { confirmResolve = resolve; });
}
function resolveLeave(result: boolean) {
  const resolve = confirmResolve; confirmResolve = null; confirmOpen.value = false; resolve?.(result);
}
onBeforeRouteLeave(() => allowLeave());
function beforeUnload(event: BeforeUnloadEvent) {
  if (dirty() || saving.value) { event.preventDefault(); event.returnValue = ''; }
}
onMounted(() => { window.addEventListener('beforeunload', beforeUnload); void loadCategories(); void refresh(); });
onBeforeUnmount(() => { alive = false; listGeneration++; editorGeneration++; resolveLeave(false); window.removeEventListener('beforeunload', beforeUnload); });

async function loadCategories() {
  categoryError.value = ''; categoriesLoading.value = true;
  try { const data = await listCategories(); if (alive) categories.value = data; }
  catch (e) { if (alive) categoryError.value = notifyError(errorKey(e)); }
  finally { if (alive) categoriesLoading.value = false; }
}
async function refresh(reset = false) {
  if (reset) page.value = 1;
  const request = ++listGeneration;
  loading.value = true; error.value = '';
  try {
    const data = await listCatalog({ q: q.value, category: category.value || undefined,
      status: (status.value || undefined) as ContentStatus | undefined,
      content_type: (kind.value || undefined) as ContentType | undefined,
      disabled: enabled.value === '' ? undefined : enabled.value === 'disabled', page: page.value });
    if (!alive || request !== listGeneration) return;
    items.value = data.items; total.value = data.total; totalPages.value = data.total_pages;
    if (!data.items.length && page.value > 1) { page.value--; await refresh(); }
  } catch (e) { if (alive && request === listGeneration) error.value = notifyError(errorKey(e)); }
  finally { if (alive && request === listGeneration) loading.value = false; }
}
async function closeEditor() {
  if (!await allowLeave() || !alive) return;
  editorGeneration++; editorOpen.value = false; editing.value = null;
  void restoreEditorFocus();
}
async function openEditor(item?: CatalogContent) {
  if (!await allowLeave() || !alive) return;
  editorTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  const request = ++editorGeneration;
  opening.value = true; error.value = '';
  try {
    const current = item ? await getCatalog(item.id) : null;
    if (!alive || request !== editorGeneration) return;
    editing.value = current;
    Object.assign(form, { title: current?.title ?? '', aliases: current?.aliases ?? '', category: current?.category ?? categories.value[0]?.code ?? '',
      region: current?.region ?? '', content_type: current?.content_type ?? 'tv', year: current?.year?.toString() ?? '', description: current?.description ?? '',
      status: current?.status ?? 'draft', disabled: current?.disabled ?? false, disabled_reason: current?.disabled_reason ?? '' });
    initial.value = JSON.stringify(form);  auditError.value = ''; audits.value = [];
    auditPage.value = 1; auditPages.value = 0; editorOpen.value = true;
    await nextTick();
    editorElement.value?.focus({ preventScroll: true });
    if (current) await loadAudits();
  } catch (e) { if (alive && request === editorGeneration) error.value = notifyError(errorKey(e)); }
  finally { if (alive && request === editorGeneration) opening.value = false; }
}
async function loadAudits() {
  if (!editing.value) return;
  const id = editing.value.id, request = editorGeneration, requestedPage = auditPage.value;
  auditError.value = '';
  try {
    const result = await getCatalogAudits(id, requestedPage);
    if (!alive || request !== editorGeneration || requestedPage !== auditPage.value) return;
    audits.value = result.items; auditPages.value = result.total_pages;
  } catch (e) { if (alive && request === editorGeneration) auditError.value = notifyError(errorKey(e)); }
}
async function save() {
  if (saving.value || opening.value) return;
  
  const year = form.year === '' ? null : Number(form.year);
  if (!form.title.trim()) { notifyError('catalogAdmin.errors.title'); return; }
  if (!categories.value.some(item => item.code === form.category)) { notifyError('catalogAdmin.errors.category'); return; }
  if (year !== null && (!Number.isInteger(year) || year < 1900 || year > 2100)) { notifyError('catalogAdmin.errors.year'); return; }
  if (editing.value && form.disabled && !form.disabled_reason.trim()) { notifyError('catalogAdmin.errors.reason'); return; }
  const payload: ContentInput = { title: form.title.trim(), aliases: form.aliases.trim(), content_type: form.content_type as ContentType,
    year, description: form.description.trim(), category: form.category, region: form.region.trim() };
  saving.value = true;
  try {
    if (editing.value) await updateCatalog(editing.value.id, { ...payload, version: editing.value.version,
      status: form.status as ContentStatus, disabled: form.disabled, disabled_reason: form.disabled ? form.disabled_reason.trim() : '' });
    else await createCatalog(payload);
    if (!alive) return;
    editorGeneration++; editorOpen.value = false;
    toasts.push({ message: t('catalogAdmin.saved'), tone: 'success' });
    await refresh(); void restoreEditorFocus();
  } catch (e) { if (alive) notifyError(errorKey(e)); }
  finally { saving.value = false; }
}
function valueLabel(key: string, value: unknown): string {
  if (value === null || value === '') return '—';
  if (key === 'disabled') return t(value ? 'catalogAdmin.yes' : 'catalogAdmin.no');
  if (key === 'category') return categoryLabel(String(value));
  if (key === 'kind' && te(`catalogDetail.kinds.${value}`)) return t(`catalogDetail.kinds.${value}`);
  if (key === 'media_type' && te(`catalogDetail.formats.${value}`)) return t(`catalogDetail.formats.${value}`);
  const translation = key === 'status' ? `catalogAdmin.statuses.${value}` : key === 'content_type' ? `catalogAdmin.types.${value}` : '';
  return translation && te(translation) ? t(translation) : String(value);
}
function auditAction(action: string) {
  return te(`catalogDetail.audit.${action}`) ? t(`catalogDetail.audit.${action}`) : t(action === 'create' ? 'catalogAdmin.created' : 'catalogAdmin.updated');
}
function auditField(key: string) {
  if (te(`catalogAdmin.fields.${key}`)) return t(`catalogAdmin.fields.${key}`);
  return te(`catalogDetail.fields.${key}`) ? t(`catalogDetail.fields.${key}`) : key;
}
</script>

<template>
  <AppPageShell :title="t('catalogAdmin.title')" :back-text="t('common.backHome')" :max-width="1040">
    <template #actions><BaseButton @click="$router.push('/admin/providers')">{{ t('catalogImport.providers') }}</BaseButton><BaseButton @click="$router.push('/admin/imports')">{{ t('catalogImport.jobs') }}</BaseButton><BaseButton variant="primary" :disabled="saving || opening || !categories.length" @click="openEditor()">{{ t('catalogAdmin.create') }}</BaseButton></template>
    <template #toolbar>
      <BaseCard class="toolbarCard">
        <form class="filters" @submit.prevent="refresh(true)">
          <BaseInput v-model="q" class="searchInput" maxlength="255" :aria-label="t('catalogAdmin.searchPlaceholder')" :placeholder="t('catalogAdmin.searchPlaceholder')" />
          <BaseSelect v-model="category" :options="categoryFilters" :label="t('catalogAdmin.fields.category')" :width="180" />
          <BaseSelect v-model="kind" :options="typeFilters" :label="t('catalogAdmin.fields.content_type')" :width="160" />
          <BaseSelect v-model="status" :options="statusFilters" :label="t('catalogAdmin.fields.status')" :width="160" />
          <BaseSelect v-model="enabled" :options="availabilityFilters" :label="t('catalogAdmin.fields.disabled')" :width="160" />
          <BaseButton type="submit" :loading="loading">{{ t('catalogAdmin.search') }}</BaseButton>
        </form>
      </BaseCard>
    </template>
    <p v-if="categoryError" role="alert" class="state error"><BaseButton @click="loadCategories">{{ t('catalogAdmin.retry') }}</BaseButton></p>
    <p v-else-if="!categoriesLoading && !categories.length" class="state">{{ t('catalogAdmin.categoryEmpty') }}</p>
    <BaseCard class="card">
      <div v-if="loading" role="status" class="state">{{ t('common.loading') }}</div>
      <div v-else-if="error" role="alert" class="state error"><BaseButton @click="refresh()">{{ t('catalogAdmin.retry') }}</BaseButton></div>
      <div v-else-if="!items.length" class="empty">
        <template v-if="q || category || kind || status || enabled">{{ t('catalogAdmin.noResults') }}</template>
        <template v-else><div class="emptyTitle">{{ t('catalogAdmin.emptyTitle') }}</div><div>{{ t('catalogAdmin.emptyHint') }}</div></template>
      </div>
      <div v-else class="resourceList">
        <RowListItem v-for="item in items" :key="item.id">
          <div class="resourceTitle">{{ item.title }}</div><div class="muted">{{ item.aliases || t('catalogAdmin.noAliases') }}</div>
          <div class="metadata"><span>{{ categoryLabel(item.category) }}</span><span>{{ t(`catalogAdmin.types.${item.content_type}`) }}</span><span>{{ item.year ?? t('catalogAdmin.unknown') }}</span></div>
          <template #right><div class="rowActions"><BasePill size="sm" :tone="item.status === 'published' ? 'accent' : 'muted'">{{ t(`catalogAdmin.statuses.${item.status}`) }}</BasePill>
            <BasePill v-if="item.disabled" size="sm">{{ t('catalogAdmin.disabled') }}</BasePill>
            <BaseButton @click="$router.push(`/admin/videos/${item.id}`)">{{ t('catalogDetail.title') }}</BaseButton>
            <BaseButton :disabled="saving || opening" @click="openEditor(item)">{{ t('catalogAdmin.edit') }}</BaseButton></div></template>
        </RowListItem>
      </div>
      <div class="pagination"><span class="muted">{{ t('catalogAdmin.pagination', { total, page, pages: Math.max(totalPages, 1) }) }}</span>
        <BaseButton :disabled="loading || page <= 1" @click="page--; refresh()">{{ t('catalogAdmin.previous') }}</BaseButton>
        <BaseButton :disabled="loading || page >= totalPages" @click="page++; refresh()">{{ t('catalogAdmin.next') }}</BaseButton></div>
    </BaseCard>

    <BaseDialog :model-value="editorOpen" :max-width="820" :z-index="80"
      :close-on-esc="!saving && !opening && !confirmOpen && !deleteOpen" :close-on-overlay="!saving && !opening && !confirmOpen && !deleteOpen"
      :aria-label="editing ? t('catalogAdmin.editTitle', { id: editing.id }) : t('catalogAdmin.newTitle')"
      @update:model-value="value => { if (!value) closeEditor(); }">
      <div ref="editorElement" class="editorViewport" tabindex="-1" @keydown="trapEditorFocus">
      <BaseCard class="card editorCard">
        <div class="sectionHeader"><h2>{{ editing ? t('catalogAdmin.editTitle', { id: editing.id }) : t('catalogAdmin.newTitle') }}</h2><BaseButton :disabled="saving || opening" @click="closeEditor">{{ t('catalogAdmin.close') }}</BaseButton></div>
        <form @submit.prevent="save"><fieldset :disabled="saving || opening">
          <div class="formGrid">
            <label class="field"><span>{{ t('catalogAdmin.fields.title') }} *</span><BaseInput v-model="form.title" required maxlength="255" /></label>
            <label class="field"><span>{{ t('catalogAdmin.fields.aliases') }}</span><BaseInput v-model="form.aliases" maxlength="1000" :placeholder="t('catalogAdmin.aliasesHint')" /></label>
            <BaseSelect v-model="form.category" :disabled="saving || opening" :label="t('catalogAdmin.fields.category')" :options="categoryOptions" />
            <BaseSelect v-model="form.content_type" :disabled="saving || opening" :label="t('catalogAdmin.fields.content_type')" :options="typeOptions" />
            <div class="field"><label for="catalog-year">{{ t('catalogAdmin.fields.year') }}</label><BaseNumberInput id="catalog-year" v-model="form.year" :min="1900" :max="2100" :step="1" :empty-value="currentYear" :disabled="saving || opening" :placeholder="t('catalogAdmin.yearHint')" /></div>
            <label class="field"><span>{{ t('catalogAdmin.fields.region') }}</span><BaseInput v-model="form.region" maxlength="16" :placeholder="t('catalogAdmin.regionHint')" /></label>
          </div>
          <label class="field"><span>{{ t('catalogAdmin.fields.description') }}</span><textarea v-model="form.description" rows="4" maxlength="10000" /></label>
          <template v-if="editing">
            <BaseSelect v-model="form.status" :disabled="saving || opening" :label="t('catalogAdmin.fields.status')" :options="statusOptions" :width="240" />
            <BaseSwitch v-model="form.disabled" class="checkbox" :disabled="saving || opening">{{ t('catalogAdmin.disable') }}</BaseSwitch>
            <label v-if="form.disabled" class="field"><span>{{ t('catalogAdmin.fields.disabled_reason') }} *</span><textarea v-model="form.disabled_reason" required maxlength="500" rows="2" /></label>
            <p class="muted">{{ t('catalogAdmin.disabledHint') }}</p>
          </template>
          <div class="itemActions"><BaseButton v-if="editing" class="deleteButton" variant="danger" :disabled="saving || opening" @click="deleteOpen = true">{{ t('catalogAdmin.delete') }}</BaseButton><BaseButton :disabled="saving || opening" @click="closeEditor">{{ t('common.cancel') }}</BaseButton><BaseButton type="submit" variant="primary" :loading="saving" :disabled="opening || !categories.length">{{ t('common.save') }}</BaseButton></div>
        </fieldset></form>
        <section v-if="editing" class="audit"><h3>{{ t('catalogAdmin.auditTitle') }}</h3>
          <p v-if="auditError" role="alert" class="error"><BaseButton @click="loadAudits">{{ t('catalogAdmin.retry') }}</BaseButton></p>
          <p v-else-if="!audits.length" class="muted">{{ t('catalogAdmin.auditEmpty') }}</p>
          <details v-for="entry in audits" :key="entry.id"><summary>{{ auditAction(entry.action) }} · {{ entry.actor_id === null ? t('catalogAdmin.deletedActor') : t('catalogAdmin.actor', { id: entry.actor_id }) }} · {{ formatLocalDateTime(entry.created_at) }}</summary>
            <dl><template v-for="(change, key) in entry.changes" :key="key"><dt>{{ auditField(String(key)) }}</dt><dd>{{ valueLabel(key, change.before) }} → {{ valueLabel(key, change.after) }}</dd></template></dl>
          </details>
          <div class="pagination"><BaseButton :disabled="auditPage <= 1" @click="auditPage--; loadAudits()">{{ t('catalogAdmin.previous') }}</BaseButton>
            <span class="muted">{{ t('catalogAdmin.auditPagination', { page: auditPage, pages: Math.max(auditPages, 1) }) }}</span><BaseButton :disabled="auditPage >= auditPages" @click="auditPage++; loadAudits()">{{ t('catalogAdmin.next') }}</BaseButton></div>
        </section>
      </BaseCard>
      </div>
    </BaseDialog>
    <BaseConfirmDialog v-if="confirmOpen" v-model="confirmOpen" :lock-scroll="false" :z-index="90" :title="t('catalogAdmin.unsavedTitle')" :message="t('catalogAdmin.unsavedMessage')" :confirm-text="t('catalogAdmin.discard')" :cancel-text="t('common.cancel')" variant="danger" @confirm="resolveLeave(true)" @cancel="resolveLeave(false)" />
    <BaseConfirmDialog v-if="deleteOpen" v-model="deleteOpen" :lock-scroll="false" :z-index="90" :title="t('catalogAdmin.delete')" :message="t('catalogAdmin.deleteMessage', { title: editing?.title })" :confirm-text="t('catalogAdmin.delete')" :cancel-text="t('common.cancel')" variant="danger" @confirm="removeResource" />
  </AppPageShell>
</template>

<style scoped>
.toolbarCard, .card { padding: 16px; }
.editorViewport { max-height: calc(100dvh - 32px - env(safe-area-inset-top) - env(safe-area-inset-bottom)); overflow-y: auto; overscroll-behavior: contain; outline: none; border-radius: var(--r-2); }
.editorCard { padding: 24px; box-shadow: var(--shadow-lg); }
.filters, .pagination, .metadata, .rowActions, .itemActions, .sectionHeader { display: flex; align-items: center; flex-wrap: wrap; gap: var(--s-3); }
.filters { align-items: flex-end; } .searchInput { flex: 1; min-width: 180px; }
.resourceList { display: grid; gap: var(--s-2); } .resourceTitle { font-size: 14px; font-weight: 650; overflow-wrap: anywhere; }
.deleteButton { margin-right: auto; }
.muted, .metadata { font-size: 12px; color: var(--c-text-muted); line-height: 1.6; overflow-wrap: anywhere; }
.metadata { margin-top: 8px; } .rowActions { justify-content: flex-end; } .pagination { justify-content: flex-end; margin-top: 16px; }
.state, .empty { padding: 18px 6px; color: var(--c-text-muted); } .empty { text-align: center; font-size: 12px; } .emptyTitle { margin-bottom: 6px; color: var(--c-text); font-size: 14px; }
.error { color: var(--c-danger); overflow-wrap: anywhere; } .sectionHeader { justify-content: space-between; margin-bottom: 16px; } h2, h3 { font-size: 15px; font-weight: 650; margin: 0; }
fieldset { border: 0; padding: 0; margin: 0; min-width: 0; } .formGrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px; }
.field { display: grid; gap: 6px; min-width: 0; margin-bottom: 12px; } .field > span, .field > label { color: var(--c-text); font-size: 12px; font-weight: 650; }
.field textarea { border: 1px solid var(--c-border); border-radius: var(--r-2); background: var(--c-surface); color: var(--c-text); font: inherit; resize: vertical; padding: 10px; }
.checkbox { display: flex; align-items: center; gap: var(--s-2); margin: 16px 0; font-size: 13px; } .itemActions { justify-content: flex-end; margin-top: 16px; }
.audit { border-top: 1px solid var(--c-border); margin-top: 24px; padding-top: 16px; } details { padding: 12px 0; border-bottom: 1px solid var(--c-border); font-size: 13px; }
summary { cursor: pointer; } dt { font-weight: 650; } dd { margin: 4px 0 14px; color: var(--c-text-muted); white-space: pre-wrap; overflow-wrap: anywhere; }
@media (max-width: 640px) { .formGrid { grid-template-columns: 1fr; } .rowActions { flex-direction: column; align-items: flex-end; gap: var(--s-2); } .filters > * { flex: 1 1 100%; } }
</style>
