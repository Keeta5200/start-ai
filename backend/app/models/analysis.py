from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Analysis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analyses"

    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    video_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    video_storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)
    step_count: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    result_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="analyses")
