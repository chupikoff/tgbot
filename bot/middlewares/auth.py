from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from services.user_service import get_or_create_user
from config import settings

class AuthMiddleware(BaseMiddleware):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            user_tg = event.from_user
        elif isinstance(event, CallbackQuery):
            user_tg = event.from_user
        else:
            return await handler(event, data)

        if not user_tg:
            return await handler(event, data)

        is_owner = user_tg.id == settings.ADMIN_TG_ID

        async with self.session_factory() as session:
            user = await get_or_create_user(
                session=session,
                telegram_id=user_tg.id,
                username=user_tg.username,
                full_name=user_tg.full_name,
                is_owner=is_owner
            )

            if not user.is_active:
                if isinstance(event, Message):
                    await event.answer("⛔ У тебя нет доступа к этому боту.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⛔ У тебя нет доступа к этому боту.", show_alert=True)
                return

            data["user"] = user
            data["session"] = session
            return await handler(event, data)
