import type { RoomRealtimeResourceStatus } from "@/infra/realtime/roomRealtime";

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

export type MediaEngineLogger = (event: string, data?: Record<string, unknown>) => void;

export function mapHealthToRealtimeStatus(
  mediaHealthState: MediaHealthState,
): RoomRealtimeResourceStatus {
  if (mediaHealthState === "error") return "error";
  if (mediaHealthState === "ready") return "ready";
  return "stalling";
}
