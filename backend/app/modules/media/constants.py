from enum import StrEnum


class MediaAssetType(StrEnum):
    AVATAR = "avatar"
    IMAGE = "image"
    STICKER = "sticker"
    VIDEO = "video"
    FEEDBACK_IMAGE = "feedback_image"


class MediaAssetStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DELETED = "deleted"


class StickerLibrarySource(StrEnum):
    UPLOAD = "upload"
    COLLECT = "collect"
    FROM_IMAGE = "from_image"


class EmojiProvider(StrEnum):
    QFACE = "qface"
