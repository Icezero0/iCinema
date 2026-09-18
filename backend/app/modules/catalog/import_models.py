from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, Index, text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CatalogProvider(Base):
    __tablename__ = "catalog_providers"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    abbreviation: Mapped[str] = mapped_column(String(32), default="", server_default=text("''"))
    endpoint: Mapped[str] = mapped_column(String(255))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[str] = mapped_column(ForeignKey("catalog_categories.code"))
    upstream_category: Mapped[int] = mapped_column(Integer)
    play_from: Mapped[str] = mapped_column(String(64), server_default=text("''"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    next_request_at: Mapped[float] = mapped_column(default=0.0)


class CatalogSource(Base):
    __tablename__ = "catalog_sources"
    __table_args__ = (UniqueConstraint("provider_id", "upstream_id", name="uq_catalog_source_identity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("catalog_providers.id"))
    upstream_id: Mapped[int] = mapped_column(Integer)
    content_id: Mapped[int] = mapped_column(ForeignKey("catalog_contents.id"), index=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CatalogImportJob(Base):
    __tablename__ = "catalog_import_jobs"
    __table_args__ = (
        Index("uq_catalog_active_import", "provider_id", unique=True,
              sqlite_where=text("status IN ('queued', 'running')")),
        {"sqlite_autoincrement": True},
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("catalog_providers.id"))
    provider_version: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="preview")
    start_page: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer)
    items: Mapped[list] = mapped_column(JSON, default=list)
    query: Mapped[dict] = mapped_column(JSON, default=dict, server_default=text("'{}'"))
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    lease_token: Mapped[str] = mapped_column(String(36), default="")
    lease_until: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
