export type ChatDanmakuSegment =
  | { type: "text"; text: string }
  | { type: "qface"; emojiId: string; src: string; alt: string };

export type ChatDanmakuItem = {
  id: string;
  lane: number;
  createdAt: number;
  estimatedWidth: number;
  avatarUrl?: string | null;
  avatarName: string;
  segments: ChatDanmakuSegment[];
};

export type RoomDanmakuSettings = {
  enabled: boolean;
  opacity: number;
  speed: number;
};

export const ROOM_DANMAKU_LANES = 7;

export const DEFAULT_ROOM_DANMAKU_SETTINGS: RoomDanmakuSettings = {
  enabled: true,
  opacity: 0.8,
  speed: 1,
};
