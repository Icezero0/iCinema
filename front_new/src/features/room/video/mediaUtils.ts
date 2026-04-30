import type { BufferedRange } from "./types";

export function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) return "00:00";

  const total = Math.floor(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = total % 60;
  const mm = String(minutes).padStart(2, "0");
  const ss = String(rest).padStart(2, "0");

  return hours > 0 ? `${hours}:${mm}:${ss}` : `${mm}:${ss}`;
}

export function isHlsUrl(url: string) {
  return url.split(/[?#]/, 1)[0]?.toLowerCase().endsWith(".m3u8") ?? false;
}

export function readBufferedRanges(video: HTMLVideoElement | null): BufferedRange[] {
  if (!video) return [];

  return Array.from({ length: video.buffered.length }, (_item, index) => ({
    start: Number(video.buffered.start(index).toFixed(3)),
    end: Number(video.buffered.end(index).toFixed(3)),
  }));
}

export function readSeekableRanges(video: HTMLVideoElement | null): BufferedRange[] {
  if (!video) return [];

  return Array.from({ length: video.seekable.length }, (_item, index) => ({
    start: Number(video.seekable.start(index).toFixed(3)),
    end: Number(video.seekable.end(index).toFixed(3)),
  }));
}
