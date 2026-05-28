from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from models.user import User
from services.monitoring import format_status_message

router = Router()

def is_admin_or_above(user: User) -> bool:
    return user.role in ["owner", "admin"]

@router.message(Command("status"))
async def cmd_status(message: Message, user: User):
    if not is_admin_or_above(user):
        await message.answer("⛔ Недостаточно прав.")
        return

    status = format_status_message()
    await message.answer(status)
