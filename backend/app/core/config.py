from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 基础
    app_name: str = Field("iCinema Backend v2", alias="APP_NAME")
    app_env: str = Field("development", alias="APP_ENV")
    debug: bool = Field(True, alias="DEBUG")
    api_v1_prefix: str = "/api/v1"
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    log_sql: bool = Field(False, alias="LOG_SQL")
    log_access_exclude_paths: list[str] = Field(
        default_factory=lambda: ["/health"],
        alias="LOG_ACCESS_EXCLUDE_PATHS",
    )
    log_uvicorn_access: bool = Field(False, alias="LOG_UVICORN_ACCESS")
    log_uvicorn_level: str = Field("WARNING", alias="LOG_UVICORN_LEVEL")

    # 数据目录 / DB
    data_dir: str = Field("../data", alias="DATA_DIR")
    db_filename: str = Field("iCinema.db", alias="DB_FILENAME")

    # 上传目录
    upload_dir: str | None = Field(default=None, alias="UPLOAD_DIR")
    avatar_subdir: str = Field("avatars", alias="AVATAR_SUBDIR")
    image_subdir: str = Field("images", alias="IMAGE_SUBDIR")
    sticker_subdir: str = Field("stickers", alias="STICKER_SUBDIR")
    video_subdir: str = Field("videos", alias="VIDEO_SUBDIR")
    feedback_image_subdir: str = Field("feedback", alias="FEEDBACK_IMAGE_SUBDIR")

    # JWT
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # 文件路径前缀
    avatar_public_prefix: str = Field("/avatar", alias="AVATAR_PUBLIC_PREFIX")
    image_public_prefix: str = Field("/image", alias="IMAGE_PUBLIC_PREFIX")
    sticker_public_prefix: str = Field("/sticker", alias="STICKER_PUBLIC_PREFIX")
    video_public_prefix: str = Field("/video", alias="VIDEO_PUBLIC_PREFIX")

    # Emoji catalog（远程）
    emoji_catalog_url: str = Field(
        "https://koishi.js.org/QFace/assets/qq_emoji/_index.json",
        alias="EMOJI_CATALOG_URL",
    )
    emoji_public_base_url: str = Field(
        "https://koishi.js.org/QFace/",
        alias="EMOJI_PUBLIC_BASE_URL",
    )
    emoji_catalog_cache_ttl_seconds: int = Field(
        3600,
        alias="EMOJI_CATALOG_CACHE_TTL_SECONDS",
    )
    emoji_catalog_timeout_seconds: int = Field(
        10,
        alias="EMOJI_CATALOG_TIMEOUT_SECONDS",
    )

    # WS
    ws_auth_timeout_seconds: int = Field(
        10, alias="WS_AUTH_TIMEOUT_SECONDS", ge=1
    )

    # CORS
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def data_dir_path(self) -> Path:
        return Path(self.data_dir).resolve()

    @property
    def db_path(self) -> Path:
        return (self.data_dir_path / self.db_filename).resolve()

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path.as_posix()}"

    @property
    def alembic_database_url(self) -> str:
        return self.database_url.replace("+aiosqlite", "")

    @property
    def upload_dir_path(self) -> Path:
        if self.upload_dir:
            return Path(self.upload_dir).resolve()
        return (self.data_dir_path / "upload").resolve()

    @property
    def avatar_dir_path(self) -> Path:
        return (self.upload_dir_path / self.avatar_subdir).resolve()

    @property
    def image_dir_path(self) -> Path:
        return (self.upload_dir_path / self.image_subdir).resolve()

    @property
    def sticker_dir_path(self) -> Path:
        return (self.upload_dir_path / self.sticker_subdir).resolve()

    @property
    def video_dir_path(self) -> Path:
        return (self.upload_dir_path / self.video_subdir).resolve()

    @property
    def feedback_image_dir_path(self) -> Path:
        return (self.upload_dir_path / self.feedback_image_subdir).resolve()

@lru_cache
def get_settings() -> Settings:
    return Settings()
