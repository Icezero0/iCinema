import wsClient from "@/infra/realtime/wsClient";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";

export type RoomRealtimeResourceStatus = "ready" | "stalling" | "error";
export type RoomRealtimePlaybackStatus = "playing" | "paused";

export type RoomRealtimeVideoSourceState = {
  room_id: number;
  source_type: RoomVideoSourceType;
  external_url: string | null;
  file_hash: string | null;
};

export type RoomRealtimePlaybackState = {
  room_id: number;
  status: RoomRealtimePlaybackStatus;
  position_seconds: number;
  anchor_ts_ms: number;
  playback_rate: number;
};

export type RoomRealtimeUserResourceState = {
  room_id: number;
  user_id: number;
  status: RoomRealtimeResourceStatus;
  reported_at_ms: number;
  position_seconds?: number | null;
  error_code?: string | null;
  error_message?: string | null;
};

export type RoomRealtimeUserResourceStatesState = {
  room_id: number;
  user_resource_states: RoomRealtimeUserResourceState[];
};

export type RoomRealtimePresenceState = {
  room_id: number;
  present_user_ids: number[];
};

export type RoomRealtimeSnapshot = {
  room_id: number;
  present_user_ids: number[];
  room_video_source: RoomRealtimeVideoSourceState | null;
  playback: RoomRealtimePlaybackState | null;
  user_resource_states: RoomRealtimeUserResourceStatesState | null;
};

export type RoomRealtimeSessionClosed = {
  room_id: number;
  reason: "entered_elsewhere" | "left_room" | "removed_from_room" | "room_deleted";
};

export type RoomRealtimeVideoSourceSetPayload =
  | {
      source_type: "external_url";
      external_url: string;
      anchor_ts_ms: number;
    }
  | {
      source_type: "local_file";
      file_hash: string;
      anchor_ts_ms: number;
    };

export type RoomRealtimePlaybackCommandPayload = {
  position_seconds: number;
  anchor_ts_ms: number;
  playback_rate?: number;
};

export type RoomRealtimeResourceStatusPayload = {
  status: RoomRealtimeResourceStatus;
  reported_at_ms: number;
  position_seconds?: number | null;
  error_code?: string | null;
  error_message?: string | null;
};

export type RoomRealtimeVideoSourceSetResponse = {
  room_video_source?: RoomRealtimeVideoSourceState | null;
  playback?: RoomRealtimePlaybackState | null;
  user_resource_states?: RoomRealtimeUserResourceStatesState | null;
};

export type RoomRealtimePlaybackResponse = {
  playback?: RoomRealtimePlaybackState | null;
};

export type RoomRealtimeResourceStatusResponse = {
  user_resource_states?: RoomRealtimeUserResourceStatesState | null;
  playback?: RoomRealtimePlaybackState | null;
  auto_action?: "playback_pause" | "playback_play" | null;
};

export type RoomRealtimePresenceGetResponse = {
  presence?: RoomRealtimePresenceState | null;
};

export type RoomRealtimeVideoRuntimeGetResponse = {
  room_video_source?: RoomRealtimeVideoSourceState | null;
  playback?: RoomRealtimePlaybackState | null;
  user_resource_states?: RoomRealtimeUserResourceStatesState | null;
};

export function enterRoomRealtime(roomId: number) {
  return wsClient.command<RoomRealtimeSnapshot>("room_enter", {
    room_id: roomId,
  });
}

export function leaveRoomRealtime(roomId: number) {
  return wsClient.command<void>("room_leave", {
    room_id: roomId,
  });
}

export function getRoomRealtimePresence() {
  return wsClient.command<RoomRealtimePresenceGetResponse, null>("room_presence_get", null);
}

export function getRoomRealtimeVideoRuntime() {
  return wsClient.command<RoomRealtimeVideoRuntimeGetResponse, null>("room_video_runtime_get", null);
}

export function setRoomRealtimeVideoSource(payload: RoomRealtimeVideoSourceSetPayload) {
  return wsClient.command<RoomRealtimeVideoSourceSetResponse>(
    "room_video_source_set",
    payload,
  );
}

export function sendRoomRealtimePlaybackPlay(payload: RoomRealtimePlaybackCommandPayload) {
  return wsClient.command<RoomRealtimePlaybackResponse>("playback_play", {
    ...payload,
    playback_rate: payload.playback_rate ?? 1,
  });
}

export function sendRoomRealtimePlaybackPause(payload: RoomRealtimePlaybackCommandPayload) {
  return wsClient.command<RoomRealtimePlaybackResponse>("playback_pause", {
    ...payload,
    playback_rate: payload.playback_rate ?? 1,
  });
}

export function sendRoomRealtimePlaybackSeek(payload: Omit<RoomRealtimePlaybackCommandPayload, "playback_rate">) {
  return wsClient.command<RoomRealtimePlaybackResponse>("playback_seek", payload);
}

export function sendRoomRealtimeUserResourceStatus(payload: RoomRealtimeResourceStatusPayload) {
  return wsClient.command<RoomRealtimeResourceStatusResponse>(
    "user_resource_status",
    payload,
  );
}
