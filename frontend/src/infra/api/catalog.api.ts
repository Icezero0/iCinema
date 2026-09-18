import { http } from '@/infra/http/client';

export type ContentType = 'tv' | 'movie' | 'ova' | 'oad' | 'ona' | 'special';
export type ContentStatus = 'draft' | 'published' | 'withdrawn';
export type ContentInput = {
  title: string; aliases: string; category: string; region: string;
  content_type: ContentType; year: number | null; description: string;
};
export type CatalogContent = ContentInput & {
  id: number; status: ContentStatus; disabled: boolean; disabled_reason: string;
  version: number; created_at: string; updated_at: string;
};
export type ContentUpdate = ContentInput & Pick<CatalogContent, 'version' | 'status' | 'disabled' | 'disabled_reason'>;
export type CatalogAudit = {
  id: number; actor_id: number | null; action: string; created_at: string;
  changes: Record<string, { before: unknown; after: unknown }>;
};
export type Page<T> = { items: T[]; total: number; page: number; page_size: number; total_pages: number };
const base = '/admin/catalog/contents';
export type CatalogCategory = { code: string; name: string };
export async function listCategories() { return (await http.get<CatalogCategory[]>('/admin/catalog/categories')).data; }
export async function listCatalog(params: { q?: string; category?: string; status?: ContentStatus; disabled?: boolean; content_type?: ContentType; page: number }) {
  return (await http.get<Page<CatalogContent>>(base, { params })).data;
}
export async function getCatalog(id: number) { return (await http.get<CatalogContent>(`${base}/${id}`)).data; }
export async function createCatalog(payload: ContentInput) { return (await http.post<CatalogContent>(base, payload)).data; }
export async function updateCatalog(id: number, payload: ContentUpdate) { return (await http.put<CatalogContent>(`${base}/${id}`, payload)).data; }
export async function deleteCatalog(id: number, version: number) { await http.delete(`${base}/${id}`, { params: { version } }); }
export async function getCatalogAudits(id: number, page = 1) {
  return (await http.get<Page<CatalogAudit>>(`${base}/${id}/audits`, { params: { page } })).data;
}

export type CatalogState = { disabled: boolean; disabled_reason: string };
export type CatalogEpisode = CatalogState & { id: number; content_id: number; title: string; kind: 'episode' | 'special' | 'movie'; number: number; sort_order: number; available_line_count: number };
export type CatalogLine = CatalogState & { id: number; content_id: number; name: string; display_name: string; source_key: string; line_key: string; sort_order: number };
export type CatalogPlayback = CatalogState & { id: number; content_id: number; episode_id: number; line_id: number; source_label: string; url: string; media_type: 'hls' | 'direct' | 'page' };
export type CatalogGraph = { content: CatalogContent; episodes: CatalogEpisode[]; lines: CatalogLine[]; playbacks: CatalogPlayback[] };
export type CatalogEntity = 'episodes' | 'lines' | 'playbacks';
export type CatalogPreview = { url: string; media_type: 'hls' | 'direct' };
export async function getCatalogGraph(id: number) { return (await http.get<CatalogGraph>(`${base}/${id}/graph`)).data; }
export async function saveCatalogItem(contentId: number, entity: CatalogEntity, itemId: number | null, payload: Record<string, unknown>) {
  const url = `${base}/${contentId}/${entity}${itemId === null ? '' : `/${itemId}`}`;
  return (await (itemId === null ? http.post<CatalogGraph>(url, payload) : http.put<CatalogGraph>(url, payload))).data;
}
export async function getCatalogPreview(contentId: number, id: number) {
  return (await http.get<CatalogPreview>(`${base}/${contentId}/playbacks/${id}/preview`)).data;
}
