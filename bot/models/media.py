from sqlalchemy import BigInteger, String, DateTime, Text, Integer, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from models.user import Base


class MediaCategory(Base):
    __tablename__ = "media_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    media: Mapped[list["Media"]] = relationship("Media", back_populates="category")


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False, default="video")
    added_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("media_categories.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped["MediaCategory | None"] = relationship("MediaCategory", back_populates="media")


class MediaLibraryInfo(Base):
    __tablename__ = "media_library_info"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_hash: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    imdb_id: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    year: Mapped[str | None] = mapped_column(String(16), nullable=True)
    rating: Mapped[str | None] = mapped_column(String(16), nullable=True)
    genre: Mapped[str | None] = mapped_column(String(256), nullable=True)
    runtime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    plot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
