export const qfaceEmojiAllowlist = ["0", "1", "2", "3", "4", "5"] as const;

export type AllowedQFaceEmojiId = typeof qfaceEmojiAllowlist[number];
