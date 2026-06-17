from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User

ROLE_LEVELS = {
    "guest": 0,
    "user": 1,
    "admin": 2,
    "owner": 3,
}


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_all_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


async def set_role(session: AsyncSession, target: User, new_role: str, actor: User) -> bool:
    actor_level = ROLE_LEVELS.get(actor.role, 0)
    target_level = ROLE_LEVELS.get(target.role, 0)
    new_level = ROLE_LEVELS.get(new_role, 0)

    # Owner неприкосновенен
    if target.role == "owner":
        return False

    # Admin не может трогать других Admin
    if actor.role == "admin" and target_level >= ROLE_LEVELS["admin"]:
        return False

    # Admin может назначать только user и guest
    if actor.role == "admin" and new_level >= ROLE_LEVELS["admin"]:
        return False

    target.role = new_role
    await session.commit()
    return True


async def set_active(session: AsyncSession, target: User, is_active: bool, actor: User) -> bool:
    # Owner неприкосновенен
    if target.role == "owner":
        return False

    # Admin не может трогать других Admin
    if actor.role == "admin" and target.role == "admin":
        return False

    target.is_active = is_active
    await session.commit()
    return True
