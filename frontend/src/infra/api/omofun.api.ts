import { http } from '@/infra/http/client';

export type OmofunLine = { id: string; source: string; label: string; url: string; media_type: 'hls' };
export type OmofunEpisode = { id: string; number: string; title: string; lines: OmofunLine[]; skipped_lines: number };
export type OmofunResult = {
  work_id: string; version: number;
  snapshot: { title: string; episodes: OmofunEpisode[] } | null;
  parsed_at: number | null; expires_at: number | null; stale: boolean;
  state: 'empty' | 'parsing' | 'ready' | 'failed'; error: string;
  completed: number; total: number; retry_after: number;
};
export async function resolveOmofun(value: string, force = false) {
  return (await http.post<OmofunResult>('/omofun/resolve', { value, force })).data;
}
export async function getOmofun(workId: string) {
  return (await http.get<OmofunResult>(`/omofun/${encodeURIComponent(workId)}`)).data;
}
export type RoomOmofunState = {
  state: OmofunResult['state']; work_id: string | null; revision: string | null;
  result: OmofunResult | null; progress: OmofunResult | null;
};
export async function getRoomOmofun(roomId: number) {
  return (await http.get<RoomOmofunState>(`/omofun/rooms/${roomId}`)).data;
}
export async function resolveRoomOmofun(roomId: number, value: string, force = false) {
  return (await http.post<RoomOmofunState>(`/omofun/rooms/${roomId}/resolve`, { value, force })).data;
}
