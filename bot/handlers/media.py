import asyncio
import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from services.media_service import (
    get_all_media, get_media, create_media, delete_media,
    get_categories, create_category, get_media_files, get_file_hash, get_omdb_info,
    search_omdb_by_title, get_library_info, save_library_info,
    get_library_info_by_filename, save_library_info_by_filename,
    get_display_name, save_display_name
)
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings

router = Router()
PAGE_SIZE = 10


class MediaStates(StatesGroup):
    waiting_title = State()
    waiting_video = State()
    waiting_imdb = State()
    waiting_rename = State()


def media_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 Видеотека", callback_data="media_list_0")],
        [InlineKeyboardButton(text="🎬 Библиотека фильмов", callback_data="media_library_0")],
        [InlineKeyboardButton(text="🔄 Пересканировать", callback_data="media_rescan")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])


def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


@router.callback_query(F.data == "menu_media")
async def cb_media(callback: CallbackQuery):
    try:
        await callback.message.edit_text("🎬 Медиатека:", reply_markup=media_menu())
    except Exception:
        await callback.message.answer("🎬 Медиатека:", reply_markup=media_menu())


async def show_media_list(callback: CallbackQuery, session: AsyncSession, page: int = 0):
    media_items = await get_all_media(session)
    total = len(media_items)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = media_items[start:end]
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    buttons = []
    for m in page_items:
        buttons.append([InlineKeyboardButton(
            text=f"🎥 {m.title}",
            callback_data=f"media_view_{m.id}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"media_list_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"media_list_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text="➕ Добавить видео", callback_data="media_add")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_media")])

    text = f"📁 Видеотека ({total}) — стр. {page+1}/{total_pages}" if media_items else "📁 Видео пока нет."
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("media_list_"))
async def cb_media_list(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.replace("media_list_", ""))
    await show_media_list(callback, session, page)


@router.callback_query(F.data.startswith("media_view_"))
async def cb_media_view(callback: CallbackQuery, user: User, session: AsyncSession):
    media_id = int(callback.data.replace("media_view_", ""))
    media = await get_media(session, media_id)
    if not media:
        await callback.answer("❌ Не найдено.")
        return
    text = f"🎥 {media.title}"
    if media.description:
        text += f"\n\n{media.description}"
    buttons = []
    if user.role in ["admin", "owner"]:
        buttons.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"media_delete_{media_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="media_list_0")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    if media.file_id:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_video(media.file_id, caption=text, reply_markup=markup)
    elif media.file_path and os.path.exists(media.file_path):
        try:
            await callback.message.delete()
        except Exception:
            pass
        video = FSInputFile(media.file_path)
        await callback.message.answer_video(video, caption=text, reply_markup=markup)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except Exception:
            await callback.message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("media_delete_"))
async def cb_media_delete(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Нет доступа.")
        return
    media_id = int(callback.data.replace("media_delete_", ""))
    await delete_media(session, media_id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("🗑 Видео удалено.", reply_markup=back_button("media_list_0"))


@router.callback_query(F.data == "media_add")
async def cb_media_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MediaStates.waiting_title)
    await state.update_data(prompt_id=callback.message.message_id)
    await callback.message.edit_text("🎥 Введи название видео:", reply_markup=back_button("media_list_0"))


@router.message(MediaStates.waiting_title)
async def process_media_title(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    await state.update_data(title=message.text)
    await state.set_state(MediaStates.waiting_video)
    msg = await message.answer("📤 Отправь видео файл:")
    await state.update_data(prompt_id=msg.message_id)


@router.message(MediaStates.waiting_video, F.video)
async def process_media_video(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass

    status_msg = await message.answer("⏳ Сохраняю видео...")
    file = await message.bot.get_file(message.video.file_id)
    filename = f"{data['title'].replace(' ', '_')}.mp4"
    file_path = os.path.join(settings.MEDIA_DIR, filename)
    await message.bot.download_file(file.file_path, destination=file_path)

    try:
        await message.delete()
    except Exception:
        pass

    media = await create_media(
        session, data["title"], user.telegram_id,
        file_id=message.video.file_id,
        file_path=file_path,
    )
    await state.clear()
    await status_msg.edit_text(f"✅ Видео '{media.title}' сохранено!", reply_markup=back_button("media_list_0"))


@router.callback_query(F.data == "media_rescan")
async def cb_media_rescan(callback: CallbackQuery):
    import subprocess
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: subprocess.run(
            ["sudo", "systemctl", "kill", "-s", "SIGHUP", "minidlna"], timeout=5
        ))
        await callback.answer("✅ Пересканирование запущено.")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data.startswith("media_library_"))
async def cb_media_library(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.replace("media_library_", ""))
    loop = asyncio.get_event_loop()
    files = await loop.run_in_executor(None, get_media_files)

    total = len(files)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_files = files[start:end]
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    buttons = []
    for f in page_files:
        fh = get_file_hash(f["path"])
        icon = "📁" if f.get("is_dir") else "🎬"
        display = await get_display_name(session, f["path"])
        label = (display or f["clean_name"])[:45]
        buttons.append([InlineKeyboardButton(text=f"{icon} {label}", callback_data=f"movie_{fh}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"media_library_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"media_library_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_media")])

    text = f"🎬 Библиотека ({total}) — стр. {page+1}/{total_pages}"
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("movie_") & ~F.data.startswith("movie_setimdb_") & ~F.data.startswith("movie_rename_"))
async def cb_movie_info(callback: CallbackQuery, session: AsyncSession):
    file_hash = callback.data.replace("movie_", "")
    loop = asyncio.get_event_loop()
    files = await loop.run_in_executor(None, get_media_files)
    file_info = next((f for f in files if get_file_hash(f["path"]) == file_hash), None)
    if not file_info:
        await callback.answer("❌ Файл не найден.")
        return

    display = await get_display_name(session, file_info["path"])
    saved = await get_library_info_by_filename(session, file_info["path"])

    if display:
        title_str = display
    elif saved and saved.get("title"):
        title_str = f"{saved['title']} ({saved['year']})" if saved.get("year") else saved["title"]
    else:
        title_str = file_info["name"]

    if saved and saved.get("rating"):
        text = (
            f"🎬 {title_str}\n\n"
            f"⭐ {saved['rating']}\n"
            f"🎭 {saved['genre']}\n"
            f"⏱ {saved['runtime']}\n\n"
            f"{saved['plot'] or ''}"
        )
    else:
        text = f"🎬 {title_str}"

    buttons = [
        [InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"movie_rename_{file_hash}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="media_library_0")],
    ]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("movie_setimdb_"))
async def cb_movie_setimdb(callback: CallbackQuery, state: FSMContext):
    file_hash = callback.data.replace("movie_setimdb_", "")
    await state.set_state(MediaStates.waiting_imdb)
    await state.update_data(file_hash=file_hash, prompt_id=callback.message.message_id)
    await callback.message.edit_text(
        "🔗 Введи IMDB ссылку или ID\nПример: tt1170358",
        reply_markup=back_button(f"movie_{file_hash}")
    )


@router.message(MediaStates.waiting_imdb)
async def process_imdb(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    fh = data.get("file_hash", "")
    await state.clear()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass

    imdb_input = message.text.strip()
    if "imdb.com" in imdb_input:
        import re
        match = re.search(r'tt\d+', imdb_input)
        imdb_id = match.group(0) if match else None
    else:
        imdb_id = imdb_input

    if not imdb_id:
        await message.answer("❌ Неверный формат.", reply_markup=back_button("media_library_0"))
        return

    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, lambda: get_omdb_info(imdb_id))

    if not info:
        await message.answer("❌ Фильм не найден в OMDB.", reply_markup=back_button("media_library_0"))
        return

    files2 = await loop.run_in_executor(None, get_media_files)
    file_info2 = next((f for f in files2 if get_file_hash(f["path"]) == fh), None)
    filename = file_info2["path"] if file_info2 else fh
    await save_library_info_by_filename(session, filename, imdb_id, info, message.from_user.id)

    text = (
        f"🎬 {info.get('Title')} ({info.get('Year')})\n\n"
        f"⭐ {info.get('imdbRating')}\n"
        f"🎭 {info.get('Genre')}\n"
        f"⏱ {info.get('Runtime')}\n\n"
        f"{info.get('Plot', '')}"
    )
    await message.answer(text, reply_markup=back_button("media_library_0"))


@router.callback_query(F.data.startswith("movie_rename_"))
async def cb_movie_rename(callback: CallbackQuery, state: FSMContext):
    file_hash = callback.data.replace("movie_rename_", "")
    await state.set_state(MediaStates.waiting_rename)
    await state.update_data(file_hash=file_hash, prompt_id=callback.message.message_id)
    await callback.message.edit_text(
        "✏️ Введи название для отображения:",
        reply_markup=back_button(f"movie_{file_hash}")
    )


@router.message(MediaStates.waiting_rename)
async def process_rename(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    fh = data.get("file_hash", "")
    await state.clear()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass

    loop = asyncio.get_event_loop()
    files = await loop.run_in_executor(None, get_media_files)
    file_info = next((f for f in files if get_file_hash(f["path"]) == fh), None)
    if not file_info:
        await message.answer("❌ Файл не найден.", reply_markup=back_button("media_library_0"))
        return

    await save_display_name(session, file_info["path"], message.text, user.telegram_id)
    await message.answer(f"✅ Название сохранено: {message.text}", reply_markup=back_button("media_library_0"))
