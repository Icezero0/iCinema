import { ref, watch, type ComputedRef } from "vue";
import {
  DEFAULT_ROOM_DANMAKU_SETTINGS,
  type RoomDanmakuSettings,
} from "@/features/room/danmaku/types";

const STORAGE_PREFIX = "icinema:room-danmaku";

function clampNumber(value: unknown, min: number, max: number, fallback: number) {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function storageKey(roomId: number) {
  return `${STORAGE_PREFIX}:${roomId}`;
}

function normalizeSettings(value: Partial<RoomDanmakuSettings> | null | undefined): RoomDanmakuSettings {
  return {
    enabled:
      typeof value?.enabled === "boolean"
        ? value.enabled
        : DEFAULT_ROOM_DANMAKU_SETTINGS.enabled,
    opacity: clampNumber(
      value?.opacity,
      0.35,
      1,
      DEFAULT_ROOM_DANMAKU_SETTINGS.opacity,
    ),
    speed: clampNumber(
      value?.speed,
      0.5,
      2,
      DEFAULT_ROOM_DANMAKU_SETTINGS.speed,
    ),
  };
}

function loadSettings(roomId: number) {
  if (!roomId) return { ...DEFAULT_ROOM_DANMAKU_SETTINGS };

  try {
    const raw = localStorage.getItem(storageKey(roomId));
    if (!raw) return { ...DEFAULT_ROOM_DANMAKU_SETTINGS };
    return normalizeSettings(JSON.parse(raw));
  } catch {
    return { ...DEFAULT_ROOM_DANMAKU_SETTINGS };
  }
}

function saveSettings(roomId: number, settings: RoomDanmakuSettings) {
  if (!roomId) return;

  try {
    localStorage.setItem(storageKey(roomId), JSON.stringify(settings));
  } catch {
    // Local preferences are best-effort.
  }
}

export function useRoomDanmakuSettings(roomId: ComputedRef<number>) {
  const settings = ref<RoomDanmakuSettings>(loadSettings(roomId.value));

  function setEnabled(value: boolean) {
    settings.value = normalizeSettings({ ...settings.value, enabled: value });
    saveSettings(roomId.value, settings.value);
  }

  function setOpacity(value: number) {
    settings.value = normalizeSettings({ ...settings.value, opacity: value });
    saveSettings(roomId.value, settings.value);
  }

  function setSpeed(value: number) {
    settings.value = normalizeSettings({ ...settings.value, speed: value });
    saveSettings(roomId.value, settings.value);
  }

  watch(roomId, (nextRoomId) => {
    settings.value = loadSettings(nextRoomId);
  });

  return {
    danmakuSettings: settings,
    setDanmakuEnabled: setEnabled,
    setDanmakuOpacity: setOpacity,
    setDanmakuSpeed: setSpeed,
  };
}
