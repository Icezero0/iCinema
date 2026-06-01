from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.site.constants import SiteRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    site_role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=SiteRole.USER,
        server_default=SiteRole.USER,
    )

    auto_accept: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
