const BVID_IN_TEXT = /(^|[^A-Za-z0-9])[Bb][Vv]([A-Za-z0-9]{10})(?![A-Za-z0-9])/;
const VIDEO_PATH = /^\/video\/[Bb][Vv]([A-Za-z0-9]{10})\/?$/;
const URL_IN_TEXT = /https?:\/\/[^\s<>"'【】]+/g;

export type BilibiliVideoInput = { bvid: string; page: number };

export function extractBilibiliVideoInput(input: string): BilibiliVideoInput | null {
  for (const rawUrl of input.match(URL_IN_TEXT) ?? []) {
    try {
      const url = new URL(rawUrl.replace(/[，。！？；、]+$/u, ""));
      if (url.hostname !== "bilibili.com" && !url.hostname.endsWith(".bilibili.com")) continue;
      const match = VIDEO_PATH.exec(url.pathname);
      if (!match) continue;
      const rawPage = url.searchParams.get("p");
      const page = rawPage && /^[1-9]\d{0,3}$/.test(rawPage) ? Number(rawPage) : 1;
      return { bvid: `BV${match[1]}`, page };
    } catch {
      // A malformed URL may still contain a standalone BV ID.
    }
  }
  const match = BVID_IN_TEXT.exec(input);
  return match ? { bvid: `BV${match[2]}`, page: 1 } : null;
}

export function extractBilibiliBvid(input: string): string | null {
  return extractBilibiliVideoInput(input)?.bvid ?? null;
}
