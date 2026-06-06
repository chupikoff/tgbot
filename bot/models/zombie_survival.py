from sqlalchemy import BigInteger, String, Integer, Boolean, DateTime, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from models.user import Base

class ZSPlayer(Base):
    __tablename__ = "zs_players"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hp: Mapped[int] = mapped_column(Integer, default=100)
    hp_max: Mapped[int] = mapped_column(Integer, default=100)
    day: Mapped[int] = mapped_column(Integer, default=1)
    game_time: Mapped[int] = mapped_column(Integer, default=360)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class ZSBase(Base):
    __tablename__ = "zs_bases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    buildings: Mapped[dict] = mapped_column(JSON, default=dict)
    defense_level: Mapped[int] = mapped_column(Integer, default=0)

class ZSInventory(Base):
    __tablename__ = "zs_inventories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    resources: Mapped[dict] = mapped_column(JSON, default=dict)
    equipment: Mapped[dict] = mapped_column(JSON, default=dict)

class ZSNPC(Base):
    __tablename__ = "zs_npcs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="idle")
    location: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class ZSEvent(Base):
    __tablename__ = "zs_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class ZSImage(Base):
    __tablename__ = "zs_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    file_id: Mapped[str] = mapped_column(String(256), nullable=False)
    added_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
