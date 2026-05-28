from sqlalchemy import BigInteger, String, Integer, Float, DateTime, ForeignKey, Text, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from models.user import Base

class GamePlayer(Base):
    __tablename__ = "game_players"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=500)
    fuel: Mapped[int] = mapped_column(Integer, default=12)
    hull: Mapped[int] = mapped_column(Integer, default=100)
    hull_max: Mapped[int] = mapped_column(Integer, default=100)
    fuel_tank: Mapped[int] = mapped_column(Integer, default=12)
    engine_range: Mapped[int] = mapped_column(Integer, default=6)
    cargo_used: Mapped[int] = mapped_column(Integer, default=0)
    cargo_max: Mapped[int] = mapped_column(Integer, default=10)
    ship_name: Mapped[str] = mapped_column(String(64), default="Shuttle MK-1")
    location: Mapped[str] = mapped_column(String(64), default="K-9 Hub")
    total_jumps: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_text: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(64), nullable=False)
    credits_delta: Mapped[int] = mapped_column(Integer, default=0)
    fuel_delta: Mapped[int] = mapped_column(Integer, default=0)
    hull_delta: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
