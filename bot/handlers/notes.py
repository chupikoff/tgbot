from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from filters.roles import has_role
from services.note_service import (
    get_notes, get_note, create_note, delete_note, update_note,
    get_categories, get_category, create_category, delete_category, search_notes
)

router = Router()


class NoteStates(StatesGroup):
    waiting_title = State()
    waiting_content = State()
    waiting_category = State()
    waiting_image = State()
    waiting_new_category = State()
    waiting_search = State()
    editing_title = State()
    editing_content = State()
    editing_image = State()


def notes_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Мои заметки", callback_data="notes_my")],
        [InlineKeyboardButton(text="🌐 Общие заметки", callback_data="notes_shared")],
        [InlineKeyboardButton(text="📂 Категории", callback_data="notes_categories")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="notes_search")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])


def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


def format_note(note, category=None) -> str:
    cat_str = f"\n#{category.name}" if category else ""
    return f"{note.title}\n\n{note.content}{cat_str}"


def note_buttons(note, user: User, back: str) -> InlineKeyboardMarkup:
    buttons = []
    if note.owner_id == user.telegram_id or user.role in ["admin", "owner"]:
        buttons.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"note_edit_{note.id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"note_delete_{note.id}"),
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "notes_main")
async def cb_notes_main(callback: CallbackQuery):
    try:
        await callback.message.edit_text("📒 Заметки:", reply_markup=notes_menu())
    except Exception:
        await callback.message.answer("📒 Заметки:", reply_markup=notes_menu())


@router.callback_query(F.data == "menu_notes")
async def cb_menu_notes(callback: CallbackQuery):
    try:
        await callback.message.edit_text("📒 Заметки:", reply_markup=notes_menu())
    except Exception:
        await callback.message.answer("📒 Заметки:", reply_markup=notes_menu())


@router.callback_query(F.data == "notes_my")
async def cb_my_notes(callback: CallbackQuery, user: User, session: AsyncSession):
    notes = await get_notes(session, user.telegram_id, is_shared=False)
    categories = await get_categories(session, user.telegram_id)
    buttons = []
    for note in notes:
        cat = next((c for c in categories if c.id == note.category_id), None)
        img = " 🖼" if note.image_file_id else ""
        buttons.append([InlineKeyboardButton(
            text=f"📄 {note.title}{img}",
            callback_data=f"note_view_{note.id}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Новая заметка", callback_data="note_new")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_main")])
    text = "📝 Мои заметки:" if notes else "📝 Заметок пока нет."
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "notes_shared")
async def cb_shared_notes(callback: CallbackQuery, user: User, session: AsyncSession):
    notes = await get_notes(session, user.telegram_id, is_shared=True)
    categories = await get_categories(session, user.telegram_id)
    buttons = []
    for note in notes:
        cat = next((c for c in categories if c.id == note.category_id), None)
        img = " 🖼" if note.image_file_id else ""
        buttons.append([InlineKeyboardButton(
            text=f"🌐 {note.title}{img}",
            callback_data=f"note_view_{note.id}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Новая общая заметка", callback_data="note_new_shared")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_main")])
    text = "🌐 Общие заметки:" if notes else "🌐 Общих заметок пока нет."
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "notes_categories")
async def cb_categories(callback: CallbackQuery, user: User, session: AsyncSession):
    categories = await get_categories(session, user.telegram_id)
    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(
            text=f"📂 {cat.name}",
            callback_data=f"cat_view_{cat.id}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Новая категория", callback_data="cat_new")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_main")])
    text = "📂 Категории:" if categories else "📂 Категорий пока нет."
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("cat_view_"))
async def cb_view_category(callback: CallbackQuery, user: User, session: AsyncSession):
    cat_id = int(callback.data.replace("cat_view_", ""))
    category = await get_category(session, cat_id)
    if not category:
        await callback.answer("❌ Категория не найдена.")
        return
    notes = await get_notes(session, user.telegram_id, is_shared=category.is_shared)
    cat_notes = [n for n in notes if n.category_id == cat_id]
    buttons = []
    for note in cat_notes:
        img = " 🖼" if note.image_file_id else ""
        buttons.append([InlineKeyboardButton(
            text=f"📄 {note.title}{img}",
            callback_data=f"note_view_{note.id}"
        )])
    if category.owner_id == user.telegram_id or user.role in ["admin", "owner"]:
        buttons.append([InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"cat_delete_{cat_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_categories")])
    text = f"📂 {category.name}\n\nЗаметок: {len(cat_notes)}"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("cat_delete_"))
async def cb_delete_category(callback: CallbackQuery, user: User, session: AsyncSession):
    cat_id = int(callback.data.replace("cat_delete_", ""))
    category = await get_category(session, cat_id)
    if not category:
        await callback.answer("❌ Категория не найдена.")
        return
    if category.owner_id != user.telegram_id and user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Нет доступа.")
        return
    await delete_category(session, cat_id)
    await callback.message.edit_text("🗑 Категория удалена.", reply_markup=back_button("notes_categories"))


@router.callback_query(F.data == "cat_new")
async def cb_new_category(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NoteStates.waiting_new_category)
    await state.update_data(prompt_id=callback.message.message_id, for_note=False)
    await callback.message.edit_text("📂 Введи название категории:", reply_markup=back_button("notes_categories"))


@router.message(NoteStates.waiting_new_category)
async def process_new_category(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    is_shared = data.get("is_shared", False)
    category = await create_category(session, message.text, user.telegram_id, is_shared=is_shared)

    if data.get("for_note"):
        await state.update_data(category_id=category.id)
        await state.set_state(NoteStates.waiting_image)
        msg = await message.answer(
            f"✅ Категория '{category.name}' создана!\n\n🖼 Прикрепи фото или нажми Пропустить:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_skip_image")]
            ])
        )
        await state.update_data(prompt_id=msg.message_id)
    else:
        await state.clear()
        await message.answer(f"✅ Категория '{category.name}' создана!", reply_markup=back_button("notes_categories"))


@router.callback_query(F.data == "note_new")
async def cb_new_note(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(is_shared=False)
    await state.set_state(NoteStates.waiting_title)
    await state.update_data(prompt_id=callback.message.message_id)
    await callback.message.edit_text("📝 Введи заголовок заметки:", reply_markup=back_button("notes_my"))


@router.callback_query(F.data == "note_new_shared")
async def cb_new_shared_note(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(is_shared=True)
    await state.set_state(NoteStates.waiting_title)
    await state.update_data(prompt_id=callback.message.message_id)
    await callback.message.edit_text("🌐 Введи заголовок общей заметки:", reply_markup=back_button("notes_shared"))


@router.message(NoteStates.waiting_title)
async def process_title(message: Message, state: FSMContext):
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
    await state.set_state(NoteStates.waiting_content)
    msg = await message.answer("📝 Введи текст заметки:")
    await state.update_data(prompt_id=msg.message_id)


@router.message(NoteStates.waiting_content)
async def process_content(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    await state.update_data(content=message.text)
    await state.set_state(NoteStates.waiting_category)

    is_shared = data.get("is_shared", False)
    categories = await get_categories(session, user.telegram_id)
    relevant = [c for c in categories if c.is_shared == is_shared]

    buttons = []
    for cat in relevant:
        buttons.append([InlineKeyboardButton(text=f"📂 {cat.name}", callback_data=f"note_setcat_{cat.id}")])
    buttons.append([InlineKeyboardButton(text="➕ Новая категория", callback_data="note_newcat")])
    buttons.append([InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_setcat_0")])

    msg = await message.answer("📂 Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.update_data(prompt_id=msg.message_id)


@router.callback_query(F.data == "note_newcat")
async def cb_note_newcat(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NoteStates.waiting_new_category)
    await state.update_data(prompt_id=callback.message.message_id, for_note=True)
    await callback.message.edit_text("📂 Введи название новой категории:")


@router.callback_query(F.data.startswith("note_setcat_"))
async def cb_set_category(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    cat_id = int(callback.data.replace("note_setcat_", ""))
    await state.update_data(category_id=cat_id if cat_id != 0 else None)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await state.set_state(NoteStates.waiting_image)
    msg = await callback.message.answer(
        "🖼 Прикрепи фото или нажми Пропустить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_skip_image")]
        ])
    )
    await state.update_data(prompt_id=msg.message_id)


@router.callback_query(F.data == "note_skip_image")
async def cb_skip_image(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    is_shared = data.get("is_shared", False)
    note = await create_note(
        session, data["title"], data["content"], user.telegram_id,
        is_shared=is_shared, category_id=data.get("category_id"),
    )
    back = "notes_shared" if is_shared else "notes_my"
    await callback.message.answer(f"✅ Заметка '{note.title}' создана!", reply_markup=back_button(back))


@router.message(NoteStates.waiting_image, F.photo)
async def process_image(message: Message, state: FSMContext, user: User, session: AsyncSession):
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
    is_shared = data.get("is_shared", False)
    file_id = message.photo[-1].file_id
    note = await create_note(
        session, data["title"], data["content"], user.telegram_id,
        is_shared=is_shared, category_id=data.get("category_id"),
        image_file_id=file_id
    )
    back = "notes_shared" if is_shared else "notes_my"
    await message.answer(f"✅ Заметка '{note.title}' создана!", reply_markup=back_button(back))


@router.callback_query(F.data.startswith("note_view_"))
async def cb_view_note(callback: CallbackQuery, user: User, session: AsyncSession):
    note_id = int(callback.data.replace("note_view_", ""))
    note = await get_note(session, note_id)
    if not note:
        await callback.answer("❌ Заметка не найдена.")
        return
    if not note.is_shared and note.owner_id != user.telegram_id:
        await callback.answer("⛔ Нет доступа.")
        return
    category = await get_category(session, note.category_id) if note.category_id else None
    text = format_note(note, category)
    back = "notes_shared" if note.is_shared else "notes_my"
    markup = note_buttons(note, user, back)

    if note.image_file_id:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(note.image_file_id, caption=text, reply_markup=markup)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except Exception:
            await callback.message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("note_delete_"))
async def cb_delete_note(callback: CallbackQuery, user: User, session: AsyncSession):
    note_id = int(callback.data.replace("note_delete_", ""))
    note = await get_note(session, note_id)
    if not note:
        await callback.answer("❌ Заметка не найдена.")
        return
    if note.owner_id != user.telegram_id and user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Нет доступа.")
        return
    back = "notes_shared" if note.is_shared else "notes_my"
    await delete_note(session, note_id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("🗑 Заметка удалена.", reply_markup=back_button(back))


@router.callback_query(F.data == "notes_search")
async def cb_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NoteStates.waiting_search)
    await state.update_data(prompt_id=callback.message.message_id)
    await callback.message.edit_text("🔍 Введи текст для поиска:", reply_markup=back_button("notes_main"))


@router.message(NoteStates.waiting_search)
async def process_search(message: Message, state: FSMContext, user: User, session: AsyncSession):
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
    notes = await search_notes(session, user.telegram_id, message.text)
    if not notes:
        await message.answer("🔍 Ничего не найдено.", reply_markup=back_button("notes_main"))
        return
    buttons = []
    for note in notes:
        img = " 🖼" if note.image_file_id else ""
        buttons.append([InlineKeyboardButton(
            text=f"📄 {note.title}{img}",
            callback_data=f"note_view_{note.id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_main")])
    await message.answer(f"🔍 Найдено: {len(notes)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("note_edit_") & ~F.data.contains("skip") & ~F.data.contains("setcat") & ~F.data.contains("remove"))
async def cb_edit_note(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    note_id = int(callback.data.replace("note_edit_", ""))
    note = await get_note(session, note_id)
    if not note:
        await callback.answer("❌ Заметка не найдена.")
        return
    if note.owner_id != user.telegram_id and user.role not in ["admin", "owner"]:
        await callback.answer("⛔ Нет доступа.")
        return
    await state.update_data(
        note_id=note_id,
        is_shared=note.is_shared,
        prompt_id=callback.message.message_id
    )
    await state.set_state(NoteStates.editing_title)
    await callback.message.edit_text(
        f"✏️ Текущий заголовок: {note.title}\n\nВведи новый или нажми Пропустить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_edit_skip_title")]
        ])
    )


@router.callback_query(F.data == "note_edit_skip_title")
async def cb_edit_skip_title(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    note = await get_note(session, data["note_id"])
    await state.set_state(NoteStates.editing_content)
    await callback.message.edit_text(
        f"📝 Текущий текст:\n{note.content}\n\nВведи новый или нажми Пропустить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_edit_skip_content")]
        ])
    )


@router.message(NoteStates.editing_title)
async def process_edit_title(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    await state.update_data(new_title=message.text)
    note = await get_note(session, data["note_id"])
    await state.set_state(NoteStates.editing_content)
    msg = await message.answer(
        f"📝 Текущий текст:\n{note.content}\n\nВведи новый или нажми Пропустить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_edit_skip_content")]
        ])
    )
    await state.update_data(prompt_id=msg.message_id)


@router.callback_query(F.data == "note_edit_skip_content")
async def cb_edit_skip_content(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    note = await get_note(session, data["note_id"])
    is_shared = data.get("is_shared", False)
    categories = await get_categories(session, note.owner_id)
    relevant = [c for c in categories if c.is_shared == is_shared]
    buttons = []
    for cat in relevant:
        buttons.append([InlineKeyboardButton(text=f"📂 {cat.name}", callback_data=f"note_edit_setcat_{cat.id}")])
    buttons.append([InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_edit_skip_cat")])
    await state.set_state(NoteStates.waiting_category)
    await callback.message.edit_text("📂 Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.message(NoteStates.editing_content)
async def process_edit_content(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    try:
        await message.bot.delete_message(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass
    await state.update_data(new_content=message.text)
    note = await get_note(session, data["note_id"])
    is_shared = data.get("is_shared", False)
    categories = await get_categories(session, note.owner_id)
    relevant = [c for c in categories if c.is_shared == is_shared]
    buttons = []
    for cat in relevant:
        buttons.append([InlineKeyboardButton(text=f"📂 {cat.name}", callback_data=f"note_edit_setcat_{cat.id}")])
    buttons.append([InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_edit_skip_cat")])
    await state.set_state(NoteStates.waiting_category)
    msg = await message.answer("📂 Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.update_data(prompt_id=msg.message_id)


@router.callback_query(F.data.startswith("note_edit_setcat_"))
async def cb_edit_setcat(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.replace("note_edit_setcat_", ""))
    await state.update_data(new_category_id=cat_id)
    await state.set_state(NoteStates.editing_image)
    await callback.message.edit_text(
        "🖼 Отправь новое фото или нажми Пропустить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_edit_skip_image")],
            [InlineKeyboardButton(text="🗑 Удалить фото", callback_data="note_edit_remove_image")],
        ])
    )


@router.callback_query(F.data == "note_edit_skip_cat")
async def cb_edit_skip_cat(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NoteStates.editing_image)
    await callback.message.edit_text(
        "🖼 Отправь новое фото или нажми Пропустить:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="note_edit_skip_image")],
            [InlineKeyboardButton(text="🗑 Удалить фото", callback_data="note_edit_remove_image")],
        ])
    )


@router.callback_query(F.data == "note_edit_skip_image")
async def cb_edit_skip_image(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    await update_note(
        session, data["note_id"],
        title=data.get("new_title"),
        content=data.get("new_content"),
        category_id=data.get("new_category_id", -1),
    )
    back = "notes_shared" if data.get("is_shared") else "notes_my"
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("✅ Заметка обновлена!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=back)]
    ]))


@router.callback_query(F.data == "note_edit_remove_image")
async def cb_edit_remove_image(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    await update_note(
        session, data["note_id"],
        title=data.get("new_title"),
        content=data.get("new_content"),
        category_id=data.get("new_category_id", -1),
        remove_image=True,
    )
    back = "notes_shared" if data.get("is_shared") else "notes_my"
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer("✅ Заметка обновлена!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=back)]
    ]))


@router.message(NoteStates.editing_image, F.photo)
async def process_edit_image(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    try:
        await message.delete()
    except Exception:
        pass
    file_id = message.photo[-1].file_id
    await update_note(
        session, data["note_id"],
        title=data.get("new_title"),
        content=data.get("new_content"),
        category_id=data.get("new_category_id", -1),
        image_file_id=file_id,
    )
    back = "notes_shared" if data.get("is_shared") else "notes_my"
    await message.answer("✅ Заметка обновлена!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=back)]
    ]))
