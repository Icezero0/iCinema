import { http } from '@/infra/http/client';

export type Provider = { id: number; code: string; name: string; abbreviation: string; endpoint: string; enabled: boolean; category: string; upstream_category: number; play_from: string; version: number };
export type ImportItem = { upstream_id: number; title: string; status: string; reason: string; content_id: number | null; warnings: string[]; entries: number; key: string; blocked: boolean; match: string; line_count: number; episode_count: number; new_episodes: number; sources: { provider_id: number; provider_name: string; upstream_id: number; title: string; updated: string; episode_count: number; warnings: string[] }[] };
export type DiscoveryQuery = { phase?: string; complete?: boolean; scanned?: number; page?: number; provider_index?: number; providers?: { id: number; name: string }[]; failures?: { name: string; reason: string }[]; criteria?: { name: string; category: string; updated_from: string | null; updated_to: string | null } };
export type ImportJob = { id: number; provider_id: number; provider_version: number; status: string; start_page: number; page_count: number; items: ImportItem[]; warnings: string[]; created_at: string; updated_at: string; query: DiscoveryQuery };
export async function discoverWorks(criteria: { name: string; category: string; updated_from: string | null; updated_to: string | null }) {
  return (await http.post<ImportJob>('/admin/imports/discover', criteria)).data;
}
export async function selectWorks(id: number, keys: string[]) {
  return (await http.post<ImportJob>(`/admin/imports/${id}/select`, { keys })).data;
}
export type ImportPage = { items: ImportJob[]; total: number; page: number; total_pages: number };
export async function listProviders() { return (await http.get<Provider[]>('/admin/providers')).data; }
export async function saveProvider(item: Provider) {
  const { id, code, ...payload } = item;
  if (!id) return (await http.post<Provider>('/admin/providers', { ...payload, code })).data;
  return (await http.put<Provider>(`/admin/providers/${id}`, payload)).data;
}
export async function checkProvider(id: number) {
  return (await http.post<{ ok: boolean; category_name: string }>(`/admin/providers/${id}/check`, {}, { timeout: 90000 })).data;
}
export async function previewImport(id: number, start_page: number, page_count: number, max_items: number) {
  return (await http.post<ImportJob>(`/admin/providers/${id}/preview`, { start_page, page_count, max_items }, { timeout: 180000 })).data;
}
export async function listImports(page = 1) { return (await http.get<ImportPage>('/admin/imports', { params: { page } })).data; }
export async function getImport(id: number) { return (await http.get<ImportJob>(`/admin/imports/${id}`)).data; }
export async function importAction(id: number, action: 'start' | 'retry' | 'cancel') {
  return (await http.post<ImportJob>(`/admin/imports/${id}/${action}`)).data;
}
