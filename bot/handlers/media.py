from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models.user import User
from services.media_service import get_all_media, get_media, add_media, delete_media, search_media
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

PAGE_SIZE = 7

class MediaStates(StatesGroup):
    waiting_title = State()
    waiting_file = State()
    waiting_search = State()

def has_media_access(user: User) -> bool:
    return user.role in ["owner", "admin", "user"]

def is_admin_or_above(user: User) -> bool:
    return user.role in ["owner", "admin"]

def media_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Список видео", callback_data="media_list_0")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="media_search")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

async def show_media_list(target, user: User, session: AsyncSession, page: int = 0):
    media_list = await get_all_media(session)
    total = len(media_list)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = media_list[start:end]
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

    buttons = []
    for m in page_items:
        icon = "🎬" if m.file_type == "video" else "📄"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {m.title}",
            callback_data=f"media_view_{m.id}"
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"media_list_{page - 1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"media_list_{page + 1}"))
    if nav:
        buttons.append(nav)

    if is_admin_or_above(user):
        buttons.append([InlineKeyboardButton(text="➕ Добавить видео", callback_data="media_add")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="media_main")])

    page_text = f" (стр. {page + 1}/{total_pages})" if total_pages > 1 else ""
    text = f"🎬 Видео ({total}){page_text}:" if media_list else "🎬 Видео пока нет."
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    if hasattr(target, "message"):
        try:
            await target.message.edit_text(text, reply_markup=markup)
        except Exception:
            await target.message.answer(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)

@router.message(Command("media"))
async def cmd_media(message: Message, user: User):
    if not has_media_access(user):
        await message.answer("⛔ Недостаточно прав.")
        return
    await message.answer("🎬 Медиатека:", reply_markup=media_menu())

@router.callback_query(F.data == "media_main")
async def cb_media_main(callback: CallbackQuery, user: User):
    try:
        await callback.message.edit_text("🎬 Медиатека:", reply_markup=media_menu())
    except Exception:
        await callback.message.answer("🎬 Медиатека:", reply_markup=media_menu())

@router.callback_query(F.data.startswith("media_list_"))
async def cb_media_list(callback: CallbackQuery, user: User, session: AsyncSession):
    page = int(callback.data.split("_")[2])
    await show_media_list(callback, user, session, page)

@router.callback_query(F.data == "media_list")
async def cb_media_list_default(callback: CallbackQuery, user: User, session: AsyncSession):
    await show_media_list(callback, user, session, 0)

@router.callback_query(F.data.startswith("media_view_"))
async def cb_media_view(callback: CallbackQuery, user: User, session: AsyncSession):
    media_id = int(callback.data.split("_")[2])
    media = await get_media(session, media_id)

    if not media:
        await callback.answer("❌ Видео не найдено.")
        return

    buttons = []
    if is_admin_or_above(user):
        buttons.append([InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"media_delete_{media_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="media_list_0")])

    await callback.message.answer_video(
        media.file_id,
        caption=f"🎬 {media.title}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("media_delete_"))
async def cb_media_delete(callback: CallbackQuery, user: User, session: AsyncSession):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return

    media_id = int(callback.data.split("_")[2])
    deleted = await delete_media(session, media_id)

    if deleted:
        await callback.message.delete()
        await callback.message.answer(
            "🗑 Видео удалено.",
            reply_markup=back_button("media_list_0")
        )
    else:
        await callback.answer("❌ Видео не найдено.")

@router.callback_query(F.data == "media_add")
async def cb_media_add(callback: CallbackQuery, state: FSMContext, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    try:
        await callback.message.edit_text(
            "🎬 Введи название видео:",
            reply_markup=back_button("media_list_0")
        )
    except Exception:
        await callback.message.answer(
            "🎬 Введи название видео:",
            reply_markup=back_button("media_list_0")
        )
    await state.set_state(MediaStates.waiting_title)

@router.message(MediaStates.waiting_title)
async def process_media_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(MediaStates.waiting_file)
    await message.answer("🎬 Теперь перешли видео из Telegram:")

@router.message(MediaStates.waiting_file)
async def process_media_file(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()

    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    else:
        await message.answer("❌ Отправь видео или файл.")
        return

    await state.clear()
    media = await add_media(session, data["title"], file_id, file_type, user.telegram_id)
    await message.answer(
        f"✅ Видео '{media.title}' добавлено в медиатеку!",
        reply_markup=back_button("media_list_0")
    )

@router.callback_query(F.data == "media_search")
async def cb_media_search(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text(
            "🔍 Введи название для поиска:",
            reply_markup=back_button("media_main")
        )
    except Exception:
        await callback.message.answer(
            "🔍 Введи название для поиска:",
            reply_markup=back_button("media_main")
        )
    await state.set_state(MediaStates.waiting_search)

@router.message(MediaStates.waiting_search)
async def process_media_search(message: Message, state: FSMContext, user: User, session: AsyncSession):
    await state.clear()
    results = await search_media(session, message.text)

    if not results:
        await message.answer(
            "🔍 Ничего не найдено.",
            reply_markup=back_button("media_main")
        )
        return

    buttons = []
    for m in results:
        icon = "🎬" if m.file_type == "video" else "📄"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {m.title}",
            callback_data=f"media_view_{m.id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="media_main")])
    await message.answer(
        f"🔍 Найдено: {len(results)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
