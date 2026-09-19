from sqlalchemy import Float, ForeignKey, Integer, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OmofunCache(Base):
    __tablename__ = "omofun_cache"

    work_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    parsed_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="empty", server_default="empty")
    error: Mapped[str] = mapped_column(String(64), default="", server_default=text("''"))
    token: Mapped[str] = mapped_column(String(32), default="", server_default=text("''"))
    lease_until: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    attempted_at: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    parsing_title: Mapped[str] = mapped_column(String(255), default="", server_default=text("''"))
