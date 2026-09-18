<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { onBeforeRouteLeave } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { listProviders, saveProvider, checkProvider, type Provider } from '@/infra/api/catalog-imports.api';
import { listCategories, type CatalogCategory } from '@/infra/api/catalog.api';
import { getBackendErrorReason } from '@/infra/http/client';
import { useToastsStore } from '@/stores/toasts.store';
import AppPageShell from '@/ui/layout/AppPageShell.vue';
import BaseCard from '@/ui/base/BaseCard.vue';
import BaseButton from '@/ui/base/BaseButton.vue';
import BaseInput from '@/ui/base/BaseInput.vue';
import BaseNumberInput from '@/ui/base/BaseNumberInput.vue';
import BaseSwitch from '@/ui/base/BaseSwitch.vue';
import BaseSelect from '@/ui/base/BaseSelect.vue';
import BaseConfirmDialog from '@/ui/base/BaseConfirmDialog.vue';

const { t, te } = useI18n();
const toasts = useToastsStore();
function notify(key: string, tone: 'success' | 'danger') { toasts.push({ message: t(key), tone }); }
const provider = ref<Provider | null>(null), categories = ref<CatalogCategory[]>([]);
const providers = ref<Provider[]>([]);
const providerOptions = computed(() => providers.value.map(item => ({ value: String(item.id), label: item.name })));
const upstreamCategory = computed({ get: () => provider.value?.upstream_category ? String(provider.value.upstream_category) : '', set: value => { if (provider.value) provider.value.upstream_category = Number(value); } });
const busy = ref(false), initial = ref('');
const confirmOpen = ref(false);
let alive = true, resolveConfirm: ((value: boolean) => void) | null = null;
const dirty = computed(() => provider.value !== null && JSON.stringify(provider.value) !== initial.value);
const options = computed(() => categories.value.map(row => ({ value: row.code, label: te(`catalogAdmin.categories.${row.code}`) ? t(`catalogAdmin.categories.${row.code}`) : row.name })));
function errorKey(e: unknown) { const key = `catalogImport.errors.${getBackendErrorReason(e)}`; return te(key) ? key : 'catalogAdmin.errors.request'; }
async function load() {
  busy.value = true;
  try { const [rows, cats] = await Promise.all([listProviders(), listCategories()]); if (!alive) return; providers.value = rows; provider.value = rows.length ? { ...rows[0]! } : null; categories.value = cats; initial.value = JSON.stringify(provider.value); }
  catch (e) { if (alive) notify(errorKey(e), 'danger'); }
  finally { busy.value = false; }
}
async function save() {
  if (!provider.value || busy.value) return;
  busy.value = true;
  try { const item = await saveProvider(provider.value); if (!alive) return; providers.value = [...providers.value.filter(row => row.id !== item.id), item].sort((a, b) => a.id - b.id); provider.value = { ...item }; initial.value = JSON.stringify(item); notify('catalogImport.saved', 'success'); }
  catch (e) { if (alive) notify(errorKey(e), 'danger'); }
  finally { busy.value = false; }
}
async function check() {
  if (!provider.value || busy.value || dirty.value) return;
  busy.value = true;
  try { await checkProvider(provider.value.id); if (alive) notify('catalogImport.checkPassed', 'success'); }
  catch (e) { if (alive) notify(errorKey(e), 'danger'); }
  finally { busy.value = false; }
}
function resolveLeave(value: boolean) { const resolve = resolveConfirm; resolveConfirm = null; confirmOpen.value = false; resolve?.(value); }
function allowLeave(): boolean | Promise<boolean> {
  if (busy.value || resolveConfirm) return false;
  if (!dirty.value) return true;
  confirmOpen.value = true;
  return new Promise<boolean>(resolve => { resolveConfirm = resolve; });
}
onBeforeRouteLeave(allowLeave);
async function selectProvider(value: string) {
  if (!await allowLeave() || !alive) return;
  const item = providers.value.find(row => String(row.id) === value);
  if (item) { provider.value = { ...item }; initial.value = JSON.stringify(provider.value); }
}
async function newProvider() {
  if (!await allowLeave() || !alive) return;
    provider.value = { id: 0, code: '', name: '', abbreviation: '', endpoint: '', enabled: true, category: categories.value[0]?.code ?? '', upstream_category: 0, play_from: '', version: 1 };
  initial.value = JSON.stringify(provider.value);
}
function beforeUnload(e: BeforeUnloadEvent) { if (dirty.value) { e.preventDefault(); e.returnValue = ''; } }
onMounted(() => { void load(); window.addEventListener('beforeunload', beforeUnload); });
onBeforeUnmount(() => { alive = false; resolveLeave(false); window.removeEventListener('beforeunload', beforeUnload); });
</script>

<template>
  <AppPageShell :title="t('catalogImport.providers')" back-to="/admin/videos" :back-text="t('catalogAdmin.title')" :max-width="1040">
    <template #actions><BaseButton :disabled="busy" @click="newProvider">{{ t('catalogImport.addProvider') }}</BaseButton></template>
    <div class="panels">
    <p v-if="!provider && busy">{{ t('common.loading') }}</p>
    <BaseButton v-if="!provider && !busy" @click="load">{{ t('catalogAdmin.retry') }}</BaseButton>
    <BaseSelect v-if="providers.length" :model-value="provider?.id ? String(provider.id) : ''" :options="providerOptions" :label="t('catalogImport.selectProvider')" :placeholder="t('catalogImport.newProvider')" :disabled="busy" @update:model-value="selectProvider" />
    <template v-if="provider">
      <BaseCard class="card"><form @submit.prevent="save"><fieldset :disabled="busy">
        <h2>{{ t('catalogImport.configuration') }}</h2>
        <div class="grid">
          <label class="field"><span>{{ t('catalogImport.providerName') }}</span><BaseInput v-model="provider.name" required maxlength="100" /></label>
          <label class="field"><span>{{ t('catalogImport.providerAbbreviation') }}</span><BaseInput v-model="provider.abbreviation" maxlength="32" /></label>
          <label class="field"><span>{{ t('catalogImport.providerCode') }}</span><BaseInput v-model="provider.code" :readonly="!!provider.id" required maxlength="32" pattern="[a-z][a-z0-9_-]*" /></label>
          <BaseSelect v-model="provider.category" :disabled="busy" :label="t('catalogImport.categoryMapping')" :options="options" />
          <div class="field"><label for="upstream-category">{{ t('catalogImport.upstreamCategory') }}</label><BaseNumberInput id="upstream-category" v-model="upstreamCategory" :disabled="busy" :min="1" :max="999999" required /></div>
          <label class="field"><span>{{ t('catalogImport.playFrom') }}</span><BaseInput v-model="provider.play_from" required maxlength="64" pattern="[a-zA-Z0-9_-]+" /></label>
          <label class="field wide"><span>{{ t('catalogImport.endpoint') }}</span><BaseInput v-model="provider.endpoint" type="url" required maxlength="255" placeholder="https://…" /></label>
        </div>
        <BaseSwitch v-model="provider.enabled" :disabled="busy">{{ t('catalogImport.enabled') }}</BaseSwitch>
        <div class="actions"><BaseButton :disabled="busy || dirty || !provider.enabled || !provider.id" @click="check">{{ t('catalogImport.check') }}</BaseButton><BaseButton type="submit" variant="primary" :disabled="busy || !dirty">{{ t('common.save') }}</BaseButton></div>
      </fieldset></form></BaseCard>
    </template>
    </div>
    <BaseConfirmDialog v-if="confirmOpen" v-model="confirmOpen" :title="t('catalogAdmin.unsavedTitle')" :message="t('catalogAdmin.unsavedMessage')" :confirm-text="t('catalogAdmin.discard')" :cancel-text="t('common.cancel')" @confirm="resolveLeave(true)" @cancel="resolveLeave(false)" />
  </AppPageShell>
</template>

<style scoped>
.panels { display: grid; gap: 20px; }
.card { padding: 24px; } h2 { font-size: 16px; margin: 0 0 16px; } fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; } .wide { grid-column: 1 / -1; }
.field { display: grid; gap: 8px; font-size: 13px; min-width: 0; } code { overflow-wrap: anywhere; color: var(--c-text-muted); }
.actions { display: flex; gap: var(--s-3); justify-content: flex-end; flex-wrap: wrap; margin-top: 20px; }
.muted { font-size: 13px; color: var(--c-text-muted); line-height: 1.7; } .error { color: var(--c-danger); }
@media (max-width: 640px) { .grid { grid-template-columns: 1fr; } .card { padding: 16px; } }
</style>
