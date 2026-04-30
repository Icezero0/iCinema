import type { ComputedRef, Ref } from "vue";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";
import { isHlsUrl } from "./mediaUtils";
import type {
  BufferedRange,
  MediaHealthState,
  PlaybackStateInput,
  PlayerState,
} from "./types";

export type MediaEngineKind = "hls" | "direct_video" | "local_video";

export type MediaEngineSource =
  | {
      sourceType: "external_url";
      engineKind: Extract<MediaEngineKind, "hls" | "direct_video">;
      url: string;
    }
  | {
      sourceType: "local_file";
      engineKind: Extract<MediaEngineKind, "local_video">;
      file: File;
    };

export type MediaEngineLoadInput =
  | {
      sourceType: "external_url";
      externalUrl: string;
      localFile?: null;
    }
  | {
      sourceType: "local_file";
      externalUrl?: "";
      localFile: File;
    };

export type MediaEngine = {
  readonly sourceType: Ref<MediaEngineSource["sourceType"] | "none">;
  readonly engineKind: Ref<MediaEngineSource["engineKind"] | "none">;
  readonly videoRef: Ref<HTMLVideoElement | null>;
  readonly sourceUrl: Ref<string>;
  readonly appliedUrl: Ref<string>;
  readonly playerState: Ref<PlayerState>;
  readonly mediaHealthState: Ref<MediaHealthState>;
  readonly errorMessage: Ref<string>;
  readonly currentTime: Ref<number>;
  readonly duration: Ref<number>;
  readonly bufferedRanges: Ref<BufferedRange[]>;
  readonly seekableRanges: Ref<BufferedRange[]>;
  readonly canSeek: ComputedRef<boolean>;
  readonly seekRestrictionMessage: Ref<string>;
  readonly volume: Ref<number>;
  readonly timelineLabel: ComputedRef<string>;
  readonly progressPercent: ComputedRef<number>;
  readonly bufferedProgressPercent: ComputedRef<number>;
  readonly bufferedRangePercents: ComputedRef<Array<{
    startPercent: number;
    endPercent: number;
  }>>;
  readonly bufferAhead: ComputedRef<number>;
  collectMediaMetrics: () => Record<string, unknown>;
  loadSource: (
    source: MediaEngineLoadInput | string,
    playback?: PlaybackStateInput | null,
  ) => Promise<void>;
  applyPlayback: (
    playback: PlaybackStateInput | null,
    options: { syncPosition: boolean },
  ) => Promise<void>;
  seekToPercent: (value: number) => number | null;
  setVolume: (value: number) => void;
  handleVideoEvent: (eventName: string) => void;
  handleVideoError: () => void;
  handleTimeUpdate: () => void;
  handleProgress: () => void;
};

export function classifyMediaEngineSource(
  input: MediaEngineLoadInput,
): MediaEngineSource | null {
  if (input.sourceType === "local_file") {
    return {
      sourceType: "local_file",
      engineKind: "local_video",
      file: input.localFile,
    };
  }

  const url = input.externalUrl.trim();
  if (!url) return null;

  return {
    sourceType: "external_url",
    engineKind: isHlsUrl(url) ? "hls" : "direct_video",
    url,
  };
}

export function toMediaEngineLoadInput(
  sourceType: RoomVideoSourceType,
  externalUrl: string,
  localFile: File | null,
): MediaEngineLoadInput | null {
  if (sourceType === "local_file" && localFile) {
    return {
      sourceType,
      localFile,
    };
  }

  if (sourceType === "external_url") {
    return {
      sourceType,
      externalUrl,
      localFile: null,
    };
  }

  return null;
}
