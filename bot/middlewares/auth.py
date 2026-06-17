from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy import select
from models.user import User
from config import settings

ROLE_LEVELS = {
    "guest": 0,
    "user": 1,
    "admin": 2,
    "owner": 3,
}

HANDLER_MIN_ROLES = {
    "notes": "user",
    "media": "user",
    "tasks": "user",
    "reminders": "user",
    "youtube": "user",
    "monitoring": "admin",
    "torrents": "admin",
    "docker": "admin",
    "backup": "admin",
    "users": "admin",
}


class AuthMiddleware(BaseMiddleware):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, (Message, CallbackQuery)):
            user_tg = event.from_user
        else:
            return await handler(event, data)

        if not user_tg:
            return await handler(event, data)

        async with self.session_factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_tg.id)
            )
            user = result.scalar_one_or_none()

            if user is None:
                role = "owner" if user_tg.id == settings.ADMIN_TG_ID else "guest"
                user = User(
                    telegram_id=user_tg.id,
                    username=user_tg.username,
                    full_name=user_tg.full_name,
                    role=role,
                    is_active=True,
                )
                session.add(user)
                await session.commit()
            else:
                updated = False
                if user.username != user_tg.username:
                    user.username = user_tg.username
                    updated = True
                if user.full_name != user_tg.full_name:
                    user.full_name = user_tg.full_name
                    updated = True
                if user_tg.id == settings.ADMIN_TG_ID and user.role != "owner":
                    user.role = "owner"
                    updated = True
                if updated:
                    await session.commit()

            if not user.is_active:
                if isinstance(event, Message):
                    await event.answer("⛔ У тебя нет доступа к этому боту.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⛔ У тебя нет доступа.", show_alert=True)
                return

            data["user"] = user
            data["session"] = session
            return await handler(event, data)
