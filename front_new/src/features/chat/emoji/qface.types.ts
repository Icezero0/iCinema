export type QFaceAsset = {
  type: number;
  name: string;
  path: string;
};

export type QFaceEmojiRecord = {
  emojiId: string;
  describe: string;
  qzoneCode: string;
  qcid: number;
  emojiType: number;
  aniStickerPackId: number;
  aniStickerId: number;
  associateWords: string[];
  isHide: boolean;
  startTime: string;
  endTime: string;
  animationWidth: number;
  animationHeigh: number;
  assets: QFaceAsset[];
};

export type ChatEmojiDefinition = {
  id: string;
  label: string;
  staticUrl?: string;
  animatedUrl?: string;
};
