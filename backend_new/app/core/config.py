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

    # 数据目录 / DB
    data_dir: str = Field("../data", alias="DATA_DIR")
    db_filename: str = Field("iCinema.db", alias="DB_FILENAME")

    # 上传目录
    upload_dir: str | None = Field(default=None, alias="UPLOAD_DIR")
    avatar_subdir: str = Field("avatars", alias="AVATAR_SUBDIR")

    # JWT
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # 头像文件路径前缀
    avatar_public_prefix: str = Field("/avatar", alias="AVATAR_PUBLIC_PREFIX")

    # WS
    ws_auth_timeout_seconds: int = 30

    # CORS
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- derived paths ----------
    @property
    def data_dir_path(self) -> Path:
        return Path(self.data_dir).resolve()

    @property
    def db_path(self) -> Path:
        return (self.data_dir_path / self.db_filename).resolve()

    @property
    def database_url(self) -> str:
        # sqlite+aiosqlite: absolute path
        return f"sqlite+aiosqlite:///{self.db_path.as_posix()}"

    @property
    def upload_dir_path(self) -> Path:
        if self.upload_dir:
            return Path(self.upload_dir).resolve()
        return (self.data_dir_path / "upload").resolve()

    @property
    def avatar_dir_path(self) -> Path:
        return (self.upload_dir_path / self.avatar_subdir).resolve()

@lru_cache
def get_settings() -> Settings:
    return Settings()