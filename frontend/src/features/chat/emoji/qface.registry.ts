import qfaceIndex from "./data/qface.index.json";
import { qfaceEmojiAllowlist } from "./qface.allowlist";
import type { QfaceDefinition, QfaceEmojiRecord } from "./qface.types";

const QFACE_BASE_URL = "https://koishi.js.org/QFace/";

function buildAssetUrl(path: string) {
  return new URL(path, QFACE_BASE_URL).toString();
}

function pickAssetUrl(record: QfaceEmojiRecord, type: number) {
  const asset = record.assets.find((item) => item.type === type);
  return asset ? buildAssetUrl(asset.path) : undefined;
}

function normalizeLabel(describe: string) {
  return describe.trim() || "";
}

const allowlistOrder = new Map<string, number>(
  qfaceEmojiAllowlist.map((id, index) => [id, index] as const),
);
const rawRecords = (qfaceIndex as QfaceEmojiRecord[]).filter((record) => {
  if (record.isHide) return false;
  return allowlistOrder.has(record.emojiId);
}).sort(
  (a, b) =>
    (allowlistOrder.get(a.emojiId) ?? Number.MAX_SAFE_INTEGER) -
    (allowlistOrder.get(b.emojiId) ?? Number.MAX_SAFE_INTEGER),
);

export const qfaceCatalog: QfaceDefinition[] = rawRecords.map((record) => ({
  id: record.emojiId,
  label: normalizeLabel(record.describe),
  staticUrl: pickAssetUrl(record, 0),
  animatedUrl: pickAssetUrl(record, 2),
}));

const qfaceMap = new Map(qfaceCatalog.map((emoji) => [emoji.id, emoji]));

export function getQfaceById(id: string) {
  return qfaceMap.get(id);
}

export function getQfaceUrl(id: string) {
  const emoji = getQfaceById(id);
  return emoji?.animatedUrl || emoji?.staticUrl;
}

export function getQfaceLabel(id: string) {
  return getQfaceById(id)?.label || id;
}
