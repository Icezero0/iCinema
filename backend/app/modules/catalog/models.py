from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CatalogCategory(Base):
    __tablename__ = "catalog_categories"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class CatalogContent(Base):
    __tablename__ = "catalog_contents"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    aliases: Mapped[str] = mapped_column(String(1000), default="")
    category: Mapped[str] = mapped_column(String(32), default="japanese_animation")
    region: Mapped[str] = mapped_column(String(16), default="")
    content_type: Mapped[str] = mapped_column(String(32))
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    disabled_reason: Mapped[str] = mapped_column(String(500), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CatalogAudit(Base):
    __tablename__ = "catalog_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("catalog_contents.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(32))
    changes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CatalogEpisode(Base):
    __tablename__ = "catalog_episodes"
    __table_args__ = (
        UniqueConstraint("content_id", "kind", "number", name="uq_catalog_episode_identity"),
        UniqueConstraint("id", "content_id", name="uq_catalog_episode_content"),
        {"sqlite_autoincrement": True},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("catalog_contents.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16), default="episode")
    number: Mapped[float] = mapped_column(default=1)
    sort_order: Mapped[float] = mapped_column(default=0)
    disabled: Mapped[bool] = mapped_column(default=False)
    disabled_reason: Mapped[str] = mapped_column(String(500), default="")


class CatalogLine(Base):
    __tablename__ = "catalog_lines"
    __table_args__ = (
        UniqueConstraint("content_id", "source_key", "line_key", name="uq_catalog_line_identity"),
        UniqueConstraint("id", "content_id", name="uq_catalog_line_content"),
        {"sqlite_autoincrement": True},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("catalog_contents.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    source_key: Mapped[str] = mapped_column(String(64))
    line_key: Mapped[str] = mapped_column(String(64))
    sort_order: Mapped[int] = mapped_column(default=0)
    disabled: Mapped[bool] = mapped_column(default=False)
    disabled_reason: Mapped[str] = mapped_column(String(500), default="")


class CatalogPlayback(Base):
    __tablename__ = "catalog_playbacks"
    __table_args__ = (
        ForeignKeyConstraint(["episode_id", "content_id"], ["catalog_episodes.id", "catalog_episodes.content_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["line_id", "content_id"], ["catalog_lines.id", "catalog_lines.content_id"], ondelete="CASCADE"),
        UniqueConstraint("episode_id", "line_id", name="uq_catalog_playback_mapping"),
        {"sqlite_autoincrement": True},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column(Integer, index=True)
    episode_id: Mapped[int] = mapped_column(Integer)
    line_id: Mapped[int] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(String(4096))
    media_type: Mapped[str] = mapped_column(String(16))
    source_label: Mapped[str] = mapped_column(String(255), default="")
    disabled: Mapped[bool] = mapped_column(default=False)
    disabled_reason: Mapped[str] = mapped_column(String(500), default="")
