export type QfaceAsset = {
  type: number;
  name: string;
  path: string;
};

export type QfaceEmojiRecord = {
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
  assets: QfaceAsset[];
};

export type QfaceDefinition = {
  id: string;
  label: string;
  staticUrl?: string;
  animatedUrl?: string;
};
