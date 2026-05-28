from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from datetime import datetime

async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

async def create_user(session: AsyncSession, telegram_id: int, username: str | None, full_name: str | None, role: str = "guest") -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
        role=role
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None, full_name: str | None, is_owner: bool = False) -> User:
    user = await get_user(session, telegram_id)
    if not user:
        role = "owner" if is_owner else "guest"
        user = await create_user(session, telegram_id, username, full_name, role)
    else:
        user.last_seen = datetime.utcnow()
        user.username = username
        user.full_name = full_name
        await session.commit()
    return user

async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User))
    return result.scalars().all()

async def set_user_role(session: AsyncSession, telegram_id: int, role: str) -> User | None:
    user = await get_user(session, telegram_id)
    if user:
        user.role = role
        await session.commit()
    return user

async def set_user_active(session: AsyncSession, telegram_id: int, is_active: bool) -> User | None:
    user = await get_user(session, telegram_id)
    if user:
        user.is_active = is_active
        await session.commit()
    return user
