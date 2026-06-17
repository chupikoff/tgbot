from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from filters.roles import has_role
from services.task_service import get_tasks, create_task, toggle_task, delete_task

router = Router()


class TaskStates(StatesGroup):
    waiting_text = State()


def tasks_menu(tasks: list) -> InlineKeyboardMarkup:
    buttons = []
    for t in tasks:
        icon = "✅" if t.is_done else "⬜"
        text = t.text[:40] + "..." if len(t.text) > 40 else t.text
        buttons.append([
            InlineKeyboardButton(text=f"{icon} {text}", callback_data=f"task_toggle_{t.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"task_delete_{t.id}"),
        ])
    buttons.append([InlineKeyboardButton(text="➕ Добавить", callback_data="task_add")])
    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


@router.callback_query(F.data == "menu_tasks")
async def cb_tasks(callback: CallbackQuery, user: User, session: AsyncSession):
    tasks = await get_tasks(session, user.telegram_id)
    text = "✅ Задачи:" if tasks else "✅ Задач пока нет."
    try:
        await callback.message.edit_text(text, reply_markup=tasks_menu(tasks))
    except Exception:
        await callback.message.answer(text, reply_markup=tasks_menu(tasks))


@router.callback_query(F.data == "task_add")
async def cb_task_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TaskStates.waiting_text)
    await state.update_data(prompt_id=callback.message.message_id)
    await callback.message.edit_text(
        "✅ Введи текст задачи:",
        reply_markup=back_button("menu_tasks")
    )


@router.message(TaskStates.waiting_text)
async def process_task_text(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    await create_task(session, user.telegram_id, message.text)
    tasks = await get_tasks(session, user.telegram_id)
    await message.answer("✅ Задача добавлена.", reply_markup=tasks_menu(tasks))


@router.callback_query(F.data.startswith("task_toggle_"))
async def cb_task_toggle(callback: CallbackQuery, user: User, session: AsyncSession):
    task_id = int(callback.data.replace("task_toggle_", ""))
    await toggle_task(session, task_id)
    tasks = await get_tasks(session, user.telegram_id)
    text = "✅ Задачи:" if tasks else "✅ Задач пока нет."
    await callback.message.edit_text(text, reply_markup=tasks_menu(tasks))


@router.callback_query(F.data.startswith("task_delete_"))
async def cb_task_delete(callback: CallbackQuery, user: User, session: AsyncSession):
    task_id = int(callback.data.replace("task_delete_", ""))
    await delete_task(session, task_id)
    tasks = await get_tasks(session, user.telegram_id)
    text = "✅ Задачи:" if tasks else "✅ Задач пока нет."
    await callback.message.edit_text(text, reply_markup=tasks_menu(tasks))
