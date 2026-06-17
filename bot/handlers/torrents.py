import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models.user import User
from filters.roles import has_role
from services.torrent_service import (
    get_torrents, get_torrent, add_torrent_url, add_torrent_file,
    pause_torrent, resume_torrent, remove_torrent, STATUS_NAMES
)

router = Router()


class TorrentStates(StatesGroup):
    waiting_url = State()
    waiting_file = State()


def torrent_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список торрентов", callback_data="torrent_list")],
        [InlineKeyboardButton(text="🔗 Добавить по ссылке", callback_data="torrent_add_url")],
        [InlineKeyboardButton(text="📁 Добавить файл", callback_data="torrent_add_file")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])


def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


@router.callback_query(F.data == "menu_torrents")
async def cb_torrents(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🌊 Торренты:", reply_markup=torrent_menu())
    except Exception:
        await callback.message.answer("🌊 Торренты:", reply_markup=torrent_menu())


@router.callback_query(F.data == "torrent_list")
async def cb_torrent_list(callback: CallbackQuery):
    try:
        loop = asyncio.get_event_loop()
        torrents = await loop.run_in_executor(None, get_torrents)
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка подключения к Transmission:\n{e}", reply_markup=back_button("menu_torrents"))
        return
    if not torrents:
        await callback.message.edit_text("📋 Торрентов нет.", reply_markup=back_button("menu_torrents"))
        return
    buttons = []
    for t in torrents:
        buttons.append([InlineKeyboardButton(
            text=f"{t['progress']}% | {t['name'][:35]}",
            callback_data=f"torrent_view_{t['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_torrents")])
    await callback.message.edit_text("📋 Список торрентов:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("torrent_view_"))
async def cb_torrent_view(callback: CallbackQuery):
    torrent_id = int(callback.data.replace("torrent_view_", ""))
    loop = asyncio.get_event_loop()
    t = await loop.run_in_executor(None, lambda: get_torrent(torrent_id))
    if not t:
        await callback.answer("❌ Торрент не найден.")
        return
    status = STATUS_NAMES.get(t["status"], t["status"])
    text = (
        f"🌊 {t['name']}\n\n"
        f"Статус: {status}\n"
        f"Прогресс: {t['progress']}%\n"
        f"Размер: {t['size']} GB\n"
        f"⬇️ {t['speed_down']} KB/s | ⬆️ {t['speed_up']} KB/s\n"
        f"⏱ ETA: {t['eta']}"
    )
    buttons = []
    if t["status"] == "stopped":
        buttons.append([InlineKeyboardButton(text="▶️ Возобновить", callback_data=f"torrent_resume_{torrent_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="⏸ Пауза", callback_data=f"torrent_pause_{torrent_id}")])
    buttons.append([
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"torrent_delete_{torrent_id}"),
        InlineKeyboardButton(text="🗑+файлы", callback_data=f"torrent_deletef_{torrent_id}"),
    ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="torrent_list")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("torrent_pause_"))
async def cb_torrent_pause(callback: CallbackQuery):
    torrent_id = int(callback.data.replace("torrent_pause_", ""))
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: pause_torrent(torrent_id))
    await callback.answer("⏸ Остановлен.")
    callback.data = f"torrent_view_{torrent_id}"
    await cb_torrent_view(callback)


@router.callback_query(F.data.startswith("torrent_resume_"))
async def cb_torrent_resume(callback: CallbackQuery):
    torrent_id = int(callback.data.replace("torrent_resume_", ""))
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: resume_torrent(torrent_id))
    await callback.answer("▶️ Возобновлён.")
    callback.data = f"torrent_view_{torrent_id}"
    await cb_torrent_view(callback)


@router.callback_query(F.data.startswith("torrent_delete_"))
async def cb_torrent_delete(callback: CallbackQuery):
    torrent_id = int(callback.data.replace("torrent_delete_", ""))
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: remove_torrent(torrent_id, delete_files=False))
    await callback.message.edit_text("🗑 Торрент удалён.", reply_markup=back_button("torrent_list"))


@router.callback_query(F.data.startswith("torrent_deletef_"))
async def cb_torrent_deletef(callback: CallbackQuery):
    torrent_id = int(callback.data.replace("torrent_deletef_", ""))
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: remove_torrent(torrent_id, delete_files=True))
    await callback.message.edit_text("🗑 Торрент и файлы удалены.", reply_markup=back_button("torrent_list"))


@router.callback_query(F.data == "torrent_add_url")
async def cb_add_url(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TorrentStates.waiting_url)
    await state.update_data(prompt_id=callback.message.message_id)
    await callback.message.edit_text(
        "🔗 Отправь magnet-ссылку или URL на .torrent файл:",
        reply_markup=back_button("menu_torrents")
    )


@router.message(TorrentStates.waiting_url)
async def process_torrent_url(message: Message, state: FSMContext):
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
    url = message.text.strip()
    try:
        loop = asyncio.get_event_loop()
        t = await loop.run_in_executor(None, lambda: add_torrent_url(url))
        await message.answer(f"✅ Добавлен: {t['name']}", reply_markup=back_button("torrent_list"))
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=back_button("menu_torrents"))


@router.callback_query(F.data == "torrent_add_file")
async def cb_add_file(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TorrentStates.waiting_file)
    await state.update_data(prompt_id=callback.message.message_id)
    await callback.message.edit_text(
        "📁 Отправь .torrent файл:",
        reply_markup=back_button("menu_torrents")
    )


@router.message(TorrentStates.waiting_file, F.document)
async def process_torrent_file(message: Message, state: FSMContext):
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
    file = await message.bot.get_file(message.document.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    try:
        loop = asyncio.get_event_loop()
        t = await loop.run_in_executor(None, lambda: add_torrent_file(file_bytes.read()))
        await message.answer(f"✅ Добавлен: {t['name']}", reply_markup=back_button("torrent_list"))
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", reply_markup=back_button("menu_torrents"))
