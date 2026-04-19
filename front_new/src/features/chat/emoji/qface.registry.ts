import qfaceIndex from "./data/qface.index.json";
import { qfaceEmojiAllowlist } from "./qface.allowlist";
import type { ChatEmojiDefinition, QFaceEmojiRecord } from "./qface.types";

const QFACE_BASE_URL = "https://koishi.js.org/QFace/";

function buildAssetUrl(path: string) {
  return new URL(path, QFACE_BASE_URL).toString();
}

function pickAssetUrl(record: QFaceEmojiRecord, type: number) {
  const asset = record.assets.find((item) => item.type === type);
  return asset ? buildAssetUrl(asset.path) : undefined;
}

function normalizeLabel(describe: string) {
  return describe.trim() || "";
}

const allowlistOrder = new Map(
  qfaceEmojiAllowlist.map((id, index) => [id, index] as const),
);
const rawRecords = (qfaceIndex as QFaceEmojiRecord[]).filter((record) => {
  if (record.isHide) return false;
  return allowlistOrder.has(record.emojiId);
}).sort(
  (a, b) =>
    (allowlistOrder.get(a.emojiId) ?? Number.MAX_SAFE_INTEGER) -
    (allowlistOrder.get(b.emojiId) ?? Number.MAX_SAFE_INTEGER),
);

export const chatEmojiCatalog: ChatEmojiDefinition[] = rawRecords.map((record) => ({
  id: record.emojiId,
  label: normalizeLabel(record.describe),
  staticUrl: pickAssetUrl(record, 0),
  animatedUrl: pickAssetUrl(record, 2),
}));

const chatEmojiMap = new Map(chatEmojiCatalog.map((emoji) => [emoji.id, emoji]));

export function getChatEmojiById(id: string) {
  return chatEmojiMap.get(id);
}

export function getChatEmojiUrl(id: string) {
  const emoji = getChatEmojiById(id);
  return emoji?.animatedUrl || emoji?.staticUrl;
}

export function getChatEmojiLabel(id: string) {
  return getChatEmojiById(id)?.label || id;
}
