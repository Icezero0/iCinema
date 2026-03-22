from enum import StrEnum


class MediaAssetType(StrEnum):
    AVATAR = "avatar"
    IMAGE = "image"
    STICKER = "sticker"
    VIDEO = "video"


class MediaAssetStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DELETED = "deleted"


class StickerLibrarySource(StrEnum):
    UPLOAD = "upload"
    COLLECT = "collect"


class EmojiProvider(StrEnum):
    QFACE = "qface"