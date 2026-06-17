from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from filters.roles import has_role
from services.reminder_service import get_reminders, create_reminder, delete_reminder
from datetime import datetime

router = Router()


class ReminderStates(StatesGroup):
    waiting_text = State()
    waiting_time = State()


def reminders_menu(reminders: list) -> InlineKeyboardMarkup:
    buttons = []
    for r in reminders:
        time_str = r.remind_at.strftime("%d.%m %H:%M")
        text = r.text[:30] + "..." if len(r.text) > 30 else r.text
        buttons.append([
            InlineKeyboardButton(text=f"⏰ {time_str} — {text}", callback_data=f"reminder_view_{r.id}"),
        ])
    buttons.append([InlineKeyboardButton(text="➕ Добавить", callback_data="reminder_add")])
    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


@router.callback_query(F.data == "menu_reminders")
async def cb_reminders(callback: CallbackQuery, user: User, session: AsyncSession):
    reminders = await get_reminders(session, user.telegram_id)
    text = "⏰ Напоминания:" if reminders else "⏰ Напоминаний пока нет."
    try:
        await callback.message.edit_text(text, reply_markup=reminders_menu(reminders))
    except Exception:
        await callback.message.answer(text, reply_markup=reminders_menu(reminders))


@router.callback_query(F.data == "reminder_add")
async def cb_reminder_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReminderStates.waiting_text)
    await state.update_data(prompt_id=callback.message.message_id)
    await callback.message.edit_text(
        "⏰ Введи текст напоминания:",
        reply_markup=back_button("menu_reminders")
    )


@router.message(ReminderStates.waiting_text)
async def process_reminder_text(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    await state.update_data(text=message.text)
    await state.set_state(ReminderStates.waiting_time)
    from datetime import datetime
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    msg = await message.answer(
        f"📅 Введи дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ\nСейчас: {now}",
        reply_markup=back_button("menu_reminders")
    )
    await state.update_data(prompt_id=msg.message_id)


@router.message(ReminderStates.waiting_time)
async def process_reminder_time(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    try:
        remind_at = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        msg = await message.answer(
            "❌ Неверный формат. Попробуй: 25.12.2025 15:00",
            reply_markup=back_button("menu_reminders")
        )
        await state.update_data(prompt_id=msg.message_id)
        return
    await state.clear()
    await create_reminder(session, user.telegram_id, data["text"], remind_at)
    reminders = await get_reminders(session, user.telegram_id)
    await message.answer("✅ Напоминание создано.", reply_markup=reminders_menu(reminders))


@router.callback_query(F.data.startswith("reminder_view_"))
async def cb_reminder_view(callback: CallbackQuery, session: AsyncSession):
    reminder_id = int(callback.data.replace("reminder_view_", ""))
    from services.reminder_service import get_reminder
    reminder = await get_reminder(session, reminder_id)
    if not reminder:
        await callback.answer("❌ Напоминание не найдено.")
        return
    time_str = reminder.remind_at.strftime("%d.%m.%Y %H:%M")
    text = f"⏰ {time_str}\n\n{reminder.text}"
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"reminder_delete_{reminder_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_reminders")],
    ])
    await callback.message.edit_text(text, reply_markup=buttons)


@router.callback_query(F.data.startswith("reminder_delete_"))
async def cb_reminder_delete(callback: CallbackQuery, user: User, session: AsyncSession):
    reminder_id = int(callback.data.replace("reminder_delete_", ""))
    await delete_reminder(session, reminder_id)
    reminders = await get_reminders(session, user.telegram_id)
    text = "⏰ Напоминания:" if reminders else "⏰ Напоминаний пока нет."
    await callback.message.edit_text(text, reply_markup=reminders_menu(reminders))
