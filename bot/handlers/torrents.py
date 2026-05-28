from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models.user import User
from services.torrent_service import (
    get_torrents, get_torrent, add_torrent_by_url,
    add_torrent_by_file, remove_torrent, pause_torrent,
    resume_torrent, STATUS_NAMES
)
import traceback

router = Router()

class TorrentStates(StatesGroup):
    waiting_url = State()
    waiting_file = State()

def has_torrent_access(user: User) -> bool:
    return user.role in ["owner", "admin"]

def torrent_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список торрентов", callback_data="torrent_list")],
        [InlineKeyboardButton(text="🔗 Добавить по ссылке", callback_data="torrent_add_url")],
        [InlineKeyboardButton(text="📁 Добавить файл", callback_data="torrent_add_file")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

@router.message(Command("torrents"))
async def cmd_torrents(message: Message, user: User):
    if not has_torrent_access(user):
        await message.answer("⛔ Недостаточно прав.")
        return
    await message.answer("🌊 Меню торрентов:", reply_markup=torrent_menu())

@router.callback_query(F.data == "torrent_main")
async def cb_torrent_main(callback: CallbackQuery, user: User):
    await callback.message.edit_text("🌊 Меню торрентов:", reply_markup=torrent_menu())

@router.callback_query(F.data == "torrent_list")
async def cb_torrent_list(callback: CallbackQuery, user: User):
    try:
        torrents = get_torrents()
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Не удалось подключиться к Transmission.\n{str(e)}",
            reply_markup=back_button("torrent_main")
        )
        return
    if not torrents:
        await callback.message.edit_text("📋 Торрентов нет.", reply_markup=back_button("torrent_main"))
        return
    buttons = []
    for t in torrents:
        progress = f"{t['progress']}%"
        buttons.append([InlineKeyboardButton(
            text=f"{progress} | {t['name'][:35]}",
            callback_data=f"torrent_view_{t['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="torrent_main")])
    await callback.message.edit_text("📋 Список торрентов:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("torrent_view_"))
async def cb_torrent_view(callback: CallbackQuery, user: User):
    torrent_id = int(callback.data.split("_")[2])
    try:
        t = get_torrent(torrent_id)
    except Exception:
        await callback.answer("❌ Ошибка подключения к Transmission.")
        return
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
async def cb_torrent_pause(callback: CallbackQuery, user: User):
    torrent_id = int(callback.data.split("_")[2])
    try:
        pause_torrent(torrent_id)
        await callback.answer("⏸ Торрент остановлен.")
    except Exception:
        await callback.answer("❌ Ошибка.")
        return
    await cb_torrent_view(callback, user)

@router.callback_query(F.data.startswith("torrent_resume_"))
async def cb_torrent_resume(callback: CallbackQuery, user: User):
    torrent_id = int(callback.data.split("_")[2])
    try:
        resume_torrent(torrent_id)
        await callback.answer("▶️ Торрент возобновлён.")
    except Exception:
        await callback.answer("❌ Ошибка.")
        return
    await cb_torrent_view(callback, user)

@router.callback_query(F.data.startswith("torrent_delete_"))
async def cb_torrent_delete(callback: CallbackQuery, user: User):
    torrent_id = int(callback.data.split("_")[2])
    try:
        remove_torrent(torrent_id, delete_files=False)
        await callback.answer("🗑 Торрент удалён.")
    except Exception:
        await callback.answer("❌ Ошибка.")
        return
    await callback.message.edit_text(
        "🗑 Торрент удалён из списка. Файлы сохранены.",
        reply_markup=back_button("torrent_list")
    )

@router.callback_query(F.data.startswith("torrent_deletef_"))
async def cb_torrent_deletef(callback: CallbackQuery, user: User):
    torrent_id = int(callback.data.split("_")[2])
    try:
        remove_torrent(torrent_id, delete_files=True)
        await callback.answer("🗑 Торрент и файлы удалены.")
    except Exception:
        await callback.answer("❌ Ошибка.")
        return
    await callback.message.edit_text(
        "🗑 Торрент и все файлы удалены.",
        reply_markup=back_button("torrent_list")
    )

@router.callback_query(F.data == "torrent_add_url")
async def cb_add_url(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔗 Отправь magnet-ссылку или прямую ссылку на .torrent файл:",
        reply_markup=back_button("torrent_main")
    )
    await state.set_state(TorrentStates.waiting_url)

@router.message(TorrentStates.waiting_url)
async def process_torrent_url(message: Message, state: FSMContext, user: User):
    await state.clear()
    url = message.text.strip()
    if not url.startswith("magnet:") and not url.startswith("http"):
        await message.answer("❌ Неверный формат. Отправь magnet-ссылку или http ссылку.")
        return
    try:
        torrent = add_torrent_by_url(url)
        await message.answer(
            f"✅ Торрент добавлен!\n📄 {torrent['name']}",
            reply_markup=back_button("torrent_list")
        )
    except Exception as e:
        print(traceback.format_exc())
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.callback_query(F.data == "torrent_add_file")
async def cb_add_file(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📁 Отправь .torrent файл:",
        reply_markup=back_button("torrent_main")
    )
    await state.set_state(TorrentStates.waiting_file)

@router.message(TorrentStates.waiting_file)
async def process_torrent_file(message: Message, state: FSMContext, user: User):
    await state.clear()
    if not message.document:
        await message.answer("❌ Отправь файл с расширением .torrent")
        return
    if not message.document.file_name.endswith(".torrent"):
        await message.answer("❌ Файл должен иметь расширение .torrent")
        return
    try:
        file = await message.bot.get_file(message.document.file_id)
        downloaded = await message.bot.download_file(file.file_path)
        file_content = downloaded.read()
        torrent = add_torrent_by_file(file_content)
        await message.answer(
            f"✅ Торрент добавлен!\n📄 {torrent['name']}",
            reply_markup=back_button("torrent_list")
        )
    except Exception as e:
        print(traceback.format_exc())
        await message.answer(f"❌ Ошибка: {str(e)}")
