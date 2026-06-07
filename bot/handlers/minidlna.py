import asyncio
import hashlib
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models.user import User
from services.services_service import get_service_status, restart_service, start_service, stop_service
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

PAGE_SIZE = 8

class MinidlnaStates(StatesGroup):
    entering_imdb = State()

def is_admin_or_above(user: User) -> bool:
    return user.role in ["owner", "admin"]

def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])

async def show_minidlna(callback: CallbackQuery, user: User):
    loop = asyncio.get_event_loop()
    status = await loop.run_in_executor(None, lambda: get_service_status("minidlna"))
    is_active = status == "active"
    icon = "🟢" if is_active else "🔴"

    from services.media_library_service import get_media_files
    files = await loop.run_in_executor(None, get_media_files)

    text = (
        f"📺 MiniDLNA\n\n"
        f"Статус: {icon} {status}\n"
        f"Медиапапка: /home/chpk/media\n"
        f"Фильмов: {len(files)}"
    )

    buttons = []
    if user.role == "owner":
        if is_active:
            buttons.append([InlineKeyboardButton(text="🔄 Перезапустить", callback_data="minidlna_restart")])
            buttons.append([InlineKeyboardButton(text="⏹ Остановить", callback_data="minidlna_stop")])
        else:
            buttons.append([InlineKeyboardButton(text="▶️ Запустить", callback_data="minidlna_start")])
    buttons.append([InlineKeyboardButton(text="🔍 Пересканировать", callback_data="minidlna_rescan")])
    buttons.append([InlineKeyboardButton(text="🎬 Библиотека фильмов", callback_data="minidlna_library_0")])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="menu_minidlna")])
    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "menu_minidlna")
async def cb_minidlna_main(callback: CallbackQuery, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    await show_minidlna(callback, user)

@router.callback_query(F.data == "minidlna_restart")
async def cb_minidlna_restart(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    await callback.message.edit_text("⏳ Перезапускаю MiniDLNA...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: restart_service("minidlna"))
    await callback.answer("✅ Перезапущен." if result == "OK" else f"❌ {result}")
    await show_minidlna(callback, user)

@router.callback_query(F.data == "minidlna_stop")
async def cb_minidlna_stop(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    await callback.message.edit_text("⏳ Останавливаю MiniDLNA...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: stop_service("minidlna"))
    await callback.answer("✅ Остановлен." if result == "OK" else f"❌ {result}")
    await show_minidlna(callback, user)

@router.callback_query(F.data == "minidlna_start")
async def cb_minidlna_start(callback: CallbackQuery, user: User):
    if user.role != "owner":
        await callback.answer("⛔ Только для владельца.")
        return
    await callback.message.edit_text("⏳ Запускаю MiniDLNA...")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, lambda: start_service("minidlna"))
    await callback.answer("✅ Запущен." if result == "OK" else f"❌ {result}")
    await show_minidlna(callback, user)

@router.callback_query(F.data == "minidlna_rescan")
async def cb_minidlna_rescan(callback: CallbackQuery, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, lambda: __import__("subprocess").run(
            ["sudo", "systemctl", "kill", "-s", "SIGHUP", "minidlna"],
            capture_output=True, text=True
        ))
        await callback.answer("✅ Пересканирование запущено.")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")
    await show_minidlna(callback, user)

@router.callback_query(F.data.startswith("minidlna_library_"))
async def cb_minidlna_library(callback: CallbackQuery, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    page = int(callback.data.replace("minidlna_library_", ""))
    loop = asyncio.get_event_loop()
    from services.media_library_service import get_media_files, parse_movie_name
    files = await loop.run_in_executor(None, get_media_files)

    total = len(files)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_files = files[start:end]
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    buttons = []
    for f in page_files:
        name, year = parse_movie_name(f)
        label = f"{name} ({year})" if year else name
        if len(label) > 40:
            label = label[:37] + "..."
        fh = hashlib.md5(f.encode()).hexdigest()[:8]
        buttons.append([InlineKeyboardButton(text=f"🎬 {label}", callback_data=f"movie_{fh}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"minidlna_library_{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"minidlna_library_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_minidlna")])

    text = f"🎬 Библиотека фильмов ({total}) — стр. {page+1}/{total_pages}"
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("movie_setimdb_"))
async def cb_movie_setimdb(callback: CallbackQuery, user: User, state: FSMContext):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    file_hash = callback.data.replace("movie_setimdb_", "")
    await state.update_data(file_hash=file_hash)
    await state.set_state(MinidlnaStates.entering_imdb)
    await callback.message.edit_text(
        "🔗 Введи IMDB ссылку или ID фильма\n\nПример:\nhttps://www.imdb.com/title/tt1170358/\nили просто: tt1170358",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"movie_{file_hash}")]
        ])
    )

@router.callback_query(F.data.startswith("movie_"))
async def cb_movie_info(callback: CallbackQuery, user: User, session: AsyncSession):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    file_hash = callback.data.replace("movie_", "")
    loop = asyncio.get_event_loop()
    from services.media_library_service import get_media_files, parse_movie_name, search_omdb, search_omdb_by_id, format_movie_info, get_imdb_override
    files = await loop.run_in_executor(None, get_media_files)

    target_file = None
    for f in files:
        if hashlib.md5(f.encode()).hexdigest()[:8] == file_hash:
            target_file = f
            break

    if not target_file:
        await callback.answer("❌ Файл не найден.")
        return

    name, year = parse_movie_name(target_file)
    await callback.message.edit_text(f"⏳ Ищу информацию о {name}...")

    override = await get_imdb_override(session, target_file)
    if override and override.get("imdb_id"):
        data = await loop.run_in_executor(None, lambda: search_omdb_by_id(override["imdb_id"]))
    else:
        data = await loop.run_in_executor(None, lambda: search_omdb(name, year))

    buttons = [
        [InlineKeyboardButton(text="🔗 Указать IMDB вручную", callback_data=f"movie_setimdb_{file_hash}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="minidlna_library_0")],
    ]

    if data:
        text = format_movie_info(data)
        poster = data.get("Poster", "N/A")
        if poster and poster != "N/A":
            try:
                await callback.message.delete()
                await callback.message.answer_photo(
                    poster,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
                )
                return
            except Exception:
                pass
        try:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception:
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        text = f"🎬 {name}\n\nИнформация не найдена.\nУкажи IMDB ссылку вручную."
        try:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception:
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.message(MinidlnaStates.entering_imdb)
async def process_imdb_input(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    file_hash = data.get("file_hash")
    await state.clear()

    from services.media_library_service import get_media_files, set_imdb_override, search_omdb_by_id, format_movie_info
    import hashlib as hl
    loop = asyncio.get_event_loop()
    files = await loop.run_in_executor(None, get_media_files)

    target_file = None
    for f in files:
        if hl.md5(f.encode()).hexdigest()[:8] == file_hash:
            target_file = f
            break

    if not target_file:
        await message.answer("❌ Файл не найден.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="minidlna_library_0")]
        ]))
        return

    imdb_id = await set_imdb_override(session, target_file, message.text, user.telegram_id)
    data_info = await loop.run_in_executor(None, lambda: search_omdb_by_id(imdb_id))

    buttons = [[InlineKeyboardButton(text="◀️ Назад", callback_data="minidlna_library_0")]]

    if data_info:
        text = format_movie_info(data_info)
        poster = data_info.get("Poster", "N/A")
        if poster and poster != "N/A":
            try:
                await message.answer_photo(poster, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
                return
            except Exception:
                pass
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await message.answer(f"✅ IMDB ID {imdb_id} сохранён, но информация не найдена.", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
