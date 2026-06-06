from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models.user import User
from services.media_service import (
    get_all_media, get_media, add_media, delete_media, search_media,
    update_media, get_all_categories, get_category, create_category, delete_category
)
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

PAGE_SIZE = 7

class MediaStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_file = State()
    waiting_search = State()
    waiting_new_category = State()
    editing_title = State()
    editing_description = State()
    editing_file = State()

def has_media_access(user: User) -> bool:
    return user.role in ["owner", "admin", "user"]

def is_admin_or_above(user: User) -> bool:
    return user.role in ["owner", "admin"]

def media_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Все видео", callback_data="media_list_0")],
        [InlineKeyboardButton(text="📂 Категории", callback_data="media_categories")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="media_search")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

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

# ─── СПИСОК ВИДЕО ────────────────────────────────────────────────────────────

async def show_media_list(callback: CallbackQuery, user: User, session: AsyncSession, page: int = 0, category_id: int | None = None):
    media_list = await get_all_media(session, category_id)
    total = len(media_list)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_items = media_list[start:end]
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    buttons = []
    for m in page_items:
        icon = "🎬" if m.file_type == "video" else "📄"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {m.title}",
            callback_data=f"media_view_{m.id}"
        )])

    nav = []
    cat_suffix = f"_{category_id}" if category_id else "_0cat"
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"media_list_{page-1}{cat_suffix}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"media_list_{page+1}{cat_suffix}"))
    if nav:
        buttons.append(nav)

    if is_admin_or_above(user):
        buttons.append([InlineKeyboardButton(text="➕ Добавить видео", callback_data="media_add")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="media_main")])

    page_text = f" (стр. {page+1}/{total_pages})" if total_pages > 1 else ""
    text = f"🎬 Видео ({total}){page_text}:" if media_list else "🎬 Видео пока нет."
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        await callback.message.answer(text, reply_markup=markup)

@router.callback_query(F.data.startswith("media_list_"))
async def cb_media_list(callback: CallbackQuery, user: User, session: AsyncSession):
    parts = callback.data.replace("media_list_", "").split("_")
    page = int(parts[0])
    category_id = int(parts[1]) if len(parts) > 1 and parts[1] != "0cat" else None
    await show_media_list(callback, user, session, page, category_id)

# ─── ПРОСМОТР ВИДЕО ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("media_view_"))
async def cb_media_view(callback: CallbackQuery, user: User, session: AsyncSession):
    media_id = int(callback.data.split("_")[2])
    media = await get_media(session, media_id)
    if not media:
        await callback.answer("❌ Видео не найдено.")
        return

    cat = await get_category(session, media.category_id) if media.category_id else None
    cat_text = f"📂 {cat.name}" if cat else "без категории"
    caption = f"🎬 {media.title}\n📂 {cat_text}"
    if media.description:
        caption += f"\n\n{media.description}"

    buttons = []
    if is_admin_or_above(user):
        buttons.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"media_edit_{media_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"media_delete_{media_id}")
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="media_list_0")])

    await callback.message.answer_video(
        media.file_id,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

# ─── ДОБАВЛЕНИЕ ВИДЕО ────────────────────────────────────────────────────────

@router.callback_query(F.data == "media_add")
async def cb_media_add(callback: CallbackQuery, state: FSMContext, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    try:
        await callback.message.edit_text("🎬 Введи название видео:", reply_markup=back_button("media_list_0"))
    except Exception:
        await callback.message.answer("🎬 Введи название видео:", reply_markup=back_button("media_list_0"))
    await state.set_state(MediaStates.waiting_title)

@router.message(MediaStates.waiting_title)
async def process_media_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(MediaStates.waiting_description)
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="media_skip_description")]
    ])
    await message.answer("📝 Введи описание видео (или пропусти):", reply_markup=buttons)

@router.message(MediaStates.waiting_description)
async def process_media_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(MediaStates.waiting_file)
    await message.answer("🎬 Теперь перешли видео из Telegram:")

@router.callback_query(F.data == "media_skip_description")
async def cb_skip_description(callback: CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(MediaStates.waiting_file)
    await callback.message.edit_text("🎬 Теперь перешли видео из Telegram:")

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

    categories = await get_all_categories(session)
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(text=f"📂 {cat.name}", callback_data=f"media_setcat_{cat.id}")])
    buttons.append([InlineKeyboardButton(text="➕ Новая категория", callback_data="media_newcat")])
    buttons.append([InlineKeyboardButton(text="⏭ Без категории", callback_data="media_setcat_0")])

    await state.update_data(file_id=file_id, file_type=file_type)
    await message.answer("📂 Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "media_newcat")
async def cb_media_newcat(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📂 Введи название новой категории:")
    await state.set_state(MediaStates.waiting_new_category)

@router.message(MediaStates.waiting_new_category)
async def process_new_category(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    cat = await create_category(session, message.text, user.telegram_id)
    if data.get("creating_cat_only"):
        await state.clear()
        await message.answer(
            f"✅ Категория '{cat.name}' создана!",
            reply_markup=back_button("media_categories")
        )
        return
    await state.clear()
    media = await add_media(
        session, data["title"], data["file_id"], data["file_type"],
        user.telegram_id, data.get("description"), cat.id
    )
    await message.answer(
        f"✅ Видео '{media.title}' добавлено в категорию '{cat.name}'!",
        reply_markup=back_button("media_list_0")
    )

@router.callback_query(F.data.startswith("media_setcat_"))
async def cb_media_setcat(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    cat_id_str = callback.data.replace("media_setcat_", "")
    cat_id = int(cat_id_str) if cat_id_str != "0" else None
    data = await state.get_data()

    if "note_id" in data:
        return

    await state.clear()
    media = await add_media(
        session, data["title"], data["file_id"], data["file_type"],
        user.telegram_id, data.get("description"), cat_id
    )
    await callback.message.edit_text(
        f"✅ Видео '{media.title}' добавлено!",
        reply_markup=back_button("media_list_0")
    )

# ─── РЕДАКТИРОВАНИЕ ВИДЕО ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("media_edit_"), lambda c: c.data.split("_")[2].isdigit())
async def cb_media_edit(callback: CallbackQuery, user: User, session: AsyncSession):
    media_id = int(callback.data.split("_")[2])
    media = await get_media(session, media_id)
    if not media:
        await callback.answer("❌ Видео не найдено.")
        return

    cat = await get_category(session, media.category_id) if media.category_id else None
    cat_text = cat.name if cat else "нет"
    desc_text = media.description[:50] + "..." if media.description and len(media.description) > 50 else media.description or "нет"

    buttons = [
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"media_edit_title_{media_id}")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"media_edit_desc_{media_id}")],
        [InlineKeyboardButton(text="🎬 Заменить видео", callback_data=f"media_edit_file_{media_id}")],
        [InlineKeyboardButton(text="📂 Изменить категорию", callback_data=f"media_edit_cat_{media_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"media_view_{media_id}")],
    ]
    try:
        await callback.message.edit_text(
            f"✏️ Редактирование: {media.title}\n\n"
            f"📝 Описание: {desc_text}\n"
            f"📂 Категория: {cat_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"✏️ Редактирование: {media.title}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data.startswith("media_edit_title_"))
async def cb_edit_title(callback: CallbackQuery, state: FSMContext):
    media_id = int(callback.data.split("_")[3])
    await state.update_data(media_id=media_id)
    await state.set_state(MediaStates.editing_title)
    await callback.message.edit_text("✏️ Введи новое название:")

@router.message(MediaStates.editing_title)
async def process_edit_title(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    media = await update_media(session, data["media_id"], title=message.text)
    await message.answer(f"✅ Название изменено на '{media.title}'!", reply_markup=back_button("media_list_0"))

@router.callback_query(F.data.startswith("media_edit_desc_"))
async def cb_edit_desc(callback: CallbackQuery, state: FSMContext):
    media_id = int(callback.data.split("_")[3])
    await state.update_data(media_id=media_id)
    await state.set_state(MediaStates.editing_description)
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить описание", callback_data="media_clear_desc")]
    ])
    await callback.message.edit_text("📝 Введи новое описание:", reply_markup=buttons)

@router.message(MediaStates.editing_description)
async def process_edit_desc(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    await update_media(session, data["media_id"], description=message.text)
    await message.answer("✅ Описание обновлено!", reply_markup=back_button("media_list_0"))

@router.callback_query(F.data == "media_clear_desc")
async def cb_clear_desc(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    await update_media(session, data["media_id"], description="")
    await callback.message.edit_text("✅ Описание удалено!", reply_markup=back_button("media_list_0"))

@router.callback_query(F.data.startswith("media_edit_file_"))
async def cb_edit_file(callback: CallbackQuery, state: FSMContext):
    media_id = int(callback.data.split("_")[3])
    await state.update_data(media_id=media_id)
    await state.set_state(MediaStates.editing_file)
    await callback.message.edit_text("🎬 Отправь новое видео:")

@router.message(MediaStates.editing_file)
async def process_edit_file(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    if message.video:
        file_id = message.video.file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        await message.answer("❌ Отправь видео или файл.")
        return
    await state.clear()
    await update_media(session, data["media_id"], file_id=file_id)
    await message.answer("✅ Видео заменено!", reply_markup=back_button("media_list_0"))

@router.callback_query(F.data.startswith("media_edit_cat_"))
async def cb_edit_cat(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    media_id = int(callback.data.split("_")[3])
    await state.update_data(media_id=media_id, editing_cat=True)
    categories = await get_all_categories(session)
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(text=f"📂 {cat.name}", callback_data=f"media_updatecat_{media_id}_{cat.id}")])
    buttons.append([InlineKeyboardButton(text="➕ Новая категория", callback_data=f"media_newcat_edit_{media_id}")])
    buttons.append([InlineKeyboardButton(text="🗑 Убрать категорию", callback_data=f"media_updatecat_{media_id}_0")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"media_edit_{media_id}")])
    try:
        await callback.message.edit_text("📂 Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer("📂 Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("media_updatecat_"))
async def cb_update_cat(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.replace("media_updatecat_", "").split("_")
    media_id = int(parts[0])
    cat_id = int(parts[1]) if parts[1] != "0" else None
    await update_media(session, media_id, category_id=cat_id if cat_id else 0)
    await callback.answer("✅ Категория обновлена!")
    await cb_media_edit(callback, None, session)

# ─── УДАЛЕНИЕ ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("media_delete_"))
async def cb_media_delete(callback: CallbackQuery, user: User, session: AsyncSession):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    media_id = int(callback.data.split("_")[2])
    deleted = await delete_media(session, media_id)
    if deleted:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer("🗑 Видео удалено.", reply_markup=back_button("media_list_0"))
    else:
        await callback.answer("❌ Видео не найдено.")

# ─── КАТЕГОРИИ ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "media_categories")
async def cb_media_categories(callback: CallbackQuery, user: User, session: AsyncSession):
    categories = await get_all_categories(session)
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(
            text=f"📂 {cat.name}",
            callback_data=f"media_cat_view_{cat.id}"
        )])
    if is_admin_or_above(user):
        buttons.append([InlineKeyboardButton(text="➕ Новая категория", callback_data="media_cat_new")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="media_main")])
    text = "📂 Категории видео:" if categories else "📂 Категорий пока нет."
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("media_cat_view_"))
async def cb_cat_view(callback: CallbackQuery, user: User, session: AsyncSession):
    cat_id = int(callback.data.split("_")[3])
    cat = await get_category(session, cat_id)
    if not cat:
        await callback.answer("❌ Категория не найдена.")
        return
    media_list = await get_all_media(session, cat_id)
    buttons = []
    for m in media_list:
        buttons.append([InlineKeyboardButton(text=f"🎬 {m.title}", callback_data=f"media_view_{m.id}")])
    if is_admin_or_above(user):
        buttons.append([InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"media_cat_delete_{cat_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="media_categories")])
    text = f"📂 {cat.name}\n\nВидео: {len(media_list)}"
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "media_cat_new")
async def cb_cat_new(callback: CallbackQuery, state: FSMContext, user: User):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    await state.update_data(creating_cat_only=True)
    await state.set_state(MediaStates.waiting_new_category)
    await callback.message.edit_text("📂 Введи название новой категории:")

@router.callback_query(F.data.startswith("media_cat_delete_"))
async def cb_cat_delete(callback: CallbackQuery, user: User, session: AsyncSession):
    if not is_admin_or_above(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    cat_id = int(callback.data.split("_")[3])
    await delete_category(session, cat_id)
    await callback.answer("✅ Категория удалена.")
    await cb_media_categories(callback, user, session)

# ─── ПОИСК ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "media_search")
async def cb_media_search(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_text("🔍 Введи название для поиска:", reply_markup=back_button("media_main"))
    except Exception:
        await callback.message.answer("🔍 Введи название для поиска:", reply_markup=back_button("media_main"))
    await state.set_state(MediaStates.waiting_search)

@router.message(MediaStates.waiting_search)
async def process_media_search(message: Message, state: FSMContext, user: User, session: AsyncSession):
    await state.clear()
    results = await search_media(session, message.text)
    if not results:
        await message.answer("🔍 Ничего не найдено.", reply_markup=back_button("media_main"))
        return
    buttons = []
    for m in results:
        icon = "🎬" if m.file_type == "video" else "📄"
        buttons.append([InlineKeyboardButton(text=f"{icon} {m.title}", callback_data=f"media_view_{m.id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="media_main")])
    await message.answer(f"🔍 Найдено: {len(results)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
