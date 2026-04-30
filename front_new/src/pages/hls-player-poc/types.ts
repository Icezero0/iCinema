import type { RoomRealtimePlayerStatus } from "@/infra/realtime/roomRealtime";

export const POC_ROOM_ID = 1;

export type SyncGateState = "locked" | "unlocked";
export type PlayerState = "idle" | "loading" | "playing" | "paused";
export type MediaHealthState = "unknown" | "ready" | "stalling" | "error";

export type PlaybackStateInput = {
  status: "playing" | "paused";
  position_seconds: number;
  playback_rate: number;
};

export type BufferedRange = {
  start: number;
  end: number;
};

export type PocLogEntry = {
  at: string;
  event: string;
  data: Record<string, unknown>;
};

export type PocLogger = (event: string, data?: Record<string, unknown>) => void;

export const SOURCE_RESET_PLAYBACK: PlaybackStateInput = {
  status: "paused",
  position_seconds: 0,
  playback_rate: 1,
};

export function mapHealthToRealtimeStatus(
  hasSource: boolean,
  mediaHealthState: MediaHealthState,
): RoomRealtimePlayerStatus {
  if (!hasSource || mediaHealthState === "unknown") return "stalling";
  if (mediaHealthState === "error") return "error";
  if (mediaHealthState === "stalling") return "stalling";
  return "ready";
}
