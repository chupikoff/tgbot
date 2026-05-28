from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models.user import User
from services.note_service import (
    get_notes, get_note, create_note, delete_note, update_note,
    get_categories, get_category, create_category, delete_category,
    search_notes
)
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

class NoteStates(StatesGroup):
    waiting_title = State()
    waiting_content = State()
    waiting_search = State()
    waiting_new_category = State()
    editing_title = State()
    editing_content = State()

def has_notes_access(user: User) -> bool:
    return user.role in ["owner", "admin", "user"]

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Мои заметки", callback_data="notes_my")],
        [InlineKeyboardButton(text="🌐 Общие заметки", callback_data="notes_shared")],
        [InlineKeyboardButton(text="📂 Категории", callback_data="notes_categories")],
        [InlineKeyboardButton(text="🔍 Поиск", callback_data="notes_search")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ])

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

@router.message(Command("notes"))
async def cmd_notes(message: Message, user: User):
    if not has_notes_access(user):
        await message.answer("⛔ Недостаточно прав.")
        return
    await message.answer("📒 Меню заметок:", reply_markup=main_menu())

@router.callback_query(F.data == "notes_main")
async def cb_main_menu(callback: CallbackQuery, user: User):
    await callback.message.edit_text("📒 Меню заметок:", reply_markup=main_menu())

@router.callback_query(F.data == "notes_my")
async def cb_my_notes(callback: CallbackQuery, user: User, session: AsyncSession):
    notes = await get_notes(session, user.telegram_id, is_shared=False)
    categories = await get_categories(session, user.telegram_id)
    buttons = []
    if notes:
        for note in notes:
            cat = next((c for c in categories if c.id == note.category_id), None)
            cat_name = f" [{cat.name}]" if cat else ""
            buttons.append([InlineKeyboardButton(
                text=f"📄 {note.title}{cat_name}",
                callback_data=f"note_view_{note.id}"
            )])
    buttons.append([InlineKeyboardButton(text="➕ Новая заметка", callback_data="note_new")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_main")])
    text = "📝 Мои заметки:" if notes else "📝 У тебя пока нет заметок."
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "note_new")
async def cb_new_note(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(is_shared=False)
    await callback.message.edit_text("📝 Введи заголовок заметки:", reply_markup=back_button("notes_my"))
    await state.set_state(NoteStates.waiting_title)

@router.callback_query(F.data == "note_new_shared")
async def cb_new_shared_note(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(is_shared=True)
    await callback.message.edit_text("🌐 Введи заголовок общей заметки:", reply_markup=back_button("notes_shared"))
    await state.set_state(NoteStates.waiting_title)

@router.message(NoteStates.waiting_title)
async def process_title(message: Message, state: FSMContext, user: User, session: AsyncSession):
    await state.update_data(title=message.text)
    await state.set_state(NoteStates.waiting_content)
    await message.answer("📝 Теперь введи текст заметки:")

@router.message(NoteStates.waiting_content)
async def process_content(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    is_shared = data.get("is_shared", False)
    await state.update_data(content=message.text)
    categories = await get_categories(session, user.telegram_id)
    personal_cats = [c for c in categories if not c.is_shared]
    shared_cats = [c for c in categories if c.is_shared]
    relevant_cats = shared_cats if is_shared else personal_cats
    buttons = []
    for cat in relevant_cats:
        buttons.append([InlineKeyboardButton(text=f"📂 {cat.name}", callback_data=f"note_setcat_{cat.id}")])
    buttons.append([InlineKeyboardButton(text="➕ Новая категория", callback_data="note_newcat")])
    buttons.append([InlineKeyboardButton(text="⏭ Без категории", callback_data="note_setcat_0")])
    await message.answer("📂 Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "note_newcat")
async def cb_new_category_for_note(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📂 Введи название новой категории:")
    await state.set_state(NoteStates.waiting_new_category)

@router.message(NoteStates.waiting_new_category)
async def process_new_category(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    is_shared = data.get("is_shared", False)
    title = data.get("title")
    content = data.get("content")
    category = await create_category(session, message.text, user.telegram_id, is_shared=is_shared)
    if title and content:
        note = await create_note(session, title, content, user.telegram_id, is_shared=is_shared, category_id=category.id)
        await state.clear()
        back = "notes_shared" if is_shared else "notes_my"
        await message.answer(
            f"✅ Заметка '{note.title}' создана в категории '{category.name}'!",
            reply_markup=back_button(back)
        )
    else:
        await state.clear()
        await message.answer(
            f"✅ Категория '{category.name}' создана!",
            reply_markup=back_button("notes_categories")
        )

@router.callback_query(F.data.startswith("note_setcat_"))
async def cb_set_category(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    cat_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    await state.clear()
    category_id = cat_id if cat_id != 0 else None
    is_shared = data.get("is_shared", False)
    note = await create_note(session, data["title"], data["content"], user.telegram_id, is_shared=is_shared, category_id=category_id)
    back = "notes_shared" if is_shared else "notes_my"
    await callback.message.edit_text(
        f"✅ Заметка '{note.title}' створена!",
        reply_markup=back_button(back)
    )

@router.callback_query(F.data.startswith("note_view_"))
async def cb_view_note(callback: CallbackQuery, user: User, session: AsyncSession):
    note_id = int(callback.data.split("_")[2])
    note = await get_note(session, note_id)
    if not note:
        await callback.answer("❌ Заметка не найдена.")
        return
    if not note.is_shared and note.owner_id != user.telegram_id:
        await callback.answer("⛔ Нет доступа.")
        return
    categories = await get_categories(session, user.telegram_id)
    cat = next((c for c in categories if c.id == note.category_id), None)
    cat_name = f"📂 {cat.name}" if cat else "без категории"
    text = (
        f"📄 {note.title}\n"
        f"📂 Категория: {cat_name}\n"
        f"📅 {note.created_at.strftime('%d.%m.%Y')}\n\n"
        f"{note.content}"
    )
    buttons = []
    if note.owner_id == user.telegram_id or user.role in ["owner", "admin"]:
        buttons.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"note_edit_{note.id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"note_delete_{note.id}")
        ])
    back = "notes_shared" if note.is_shared else "notes_my"
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back)])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("note_delete_"))
async def cb_delete_note(callback: CallbackQuery, user: User, session: AsyncSession):
    note_id = int(callback.data.split("_")[2])
    note = await get_note(session, note_id)
    if not note:
        await callback.answer("❌ Заметка не найдена.")
        return
    if note.owner_id != user.telegram_id and user.role not in ["owner", "admin"]:
        await callback.answer("⛔ Нет доступа.")
        return
    back = "notes_shared" if note.is_shared else "notes_my"
    await delete_note(session, note_id)
    await callback.message.edit_text("🗑 Заметка удалена.", reply_markup=back_button(back))

@router.callback_query(F.data.startswith("note_edit_"))
async def cb_edit_note(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    note_id = int(callback.data.split("_")[2])
    note = await get_note(session, note_id)
    if not note or (note.owner_id != user.telegram_id and user.role not in ["owner", "admin"]):
        await callback.answer("⛔ Нет доступа.")
        return
    await state.update_data(note_id=note_id, is_shared=note.is_shared)
    await callback.message.edit_text(f"✏️ Редактирование: '{note.title}'\n\nВведи новый заголовок или /skip чтобы оставить прежний:")
    await state.set_state(NoteStates.editing_title)

@router.message(NoteStates.editing_title)
async def process_edit_title(message: Message, state: FSMContext):
    if message.text != "/skip":
        await state.update_data(new_title=message.text)
    await message.answer("✏️ Введи новый текст или /skip чтобы оставить прежний:")
    await state.set_state(NoteStates.editing_content)

@router.message(NoteStates.editing_content)
async def process_edit_content(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    new_title = data.get("new_title")
    new_content = message.text if message.text != "/skip" else None
    is_shared = data.get("is_shared", False)
    note = await update_note(session, data["note_id"], title=new_title, content=new_content)
    back = "notes_shared" if is_shared else "notes_my"
    await message.answer(
        f"✅ Заметка '{note.title}' обновлена!",
        reply_markup=back_button(back)
    )

@router.callback_query(F.data == "notes_shared")
async def cb_shared_notes(callback: CallbackQuery, user: User, session: AsyncSession):
    notes = await get_notes(session, user.telegram_id, is_shared=True)
    categories = await get_categories(session, user.telegram_id)
    buttons = []
    if notes:
        for note in notes:
            cat = next((c for c in categories if c.id == note.category_id), None)
            cat_name = f" [{cat.name}]" if cat else ""
            buttons.append([InlineKeyboardButton(
                text=f"🌐 {note.title}{cat_name}",
                callback_data=f"note_view_{note.id}"
            )])
    buttons.append([InlineKeyboardButton(text="➕ Новая общая заметка", callback_data="note_new_shared")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_main")])
    text = "🌐 Общие заметки:" if notes else "🌐 Общих заметок пока нет."
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "notes_categories")
async def cb_categories(callback: CallbackQuery, user: User, session: AsyncSession):
    categories = await get_categories(session, user.telegram_id)
    buttons = []
    if categories:
        for cat in categories:
            shared = " 🌐" if cat.is_shared else ""
            buttons.append([InlineKeyboardButton(
                text=f"📂 {cat.name}{shared}",
                callback_data=f"cat_view_{cat.id}"
            )])
    buttons.append([InlineKeyboardButton(text="➕ Новая категория", callback_data="cat_new")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_main")])
    text = "📂 Твои категории:" if categories else "📂 Категорий пока нет."
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("cat_view_"))
async def cb_view_category(callback: CallbackQuery, user: User, session: AsyncSession):
    cat_id = int(callback.data.split("_")[2])
    category = await get_category(session, cat_id)
    if not category:
        await callback.answer("❌ Категория не найдена.")
        return
    notes = await get_notes(session, user.telegram_id, is_shared=category.is_shared)
    cat_notes = [n for n in notes if n.category_id == cat_id]
    buttons = []
    for note in cat_notes:
        buttons.append([InlineKeyboardButton(text=f"📄 {note.title}", callback_data=f"note_view_{note.id}")])
    if category.owner_id == user.telegram_id or user.role in ["owner", "admin"]:
        buttons.append([InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"cat_delete_{cat_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_categories")])
    text = f"📂 {category.name}\n\nЗаметок: {len(cat_notes)}"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "cat_new")
async def cb_new_cat(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(is_shared=False, title=None, content=None)
    await callback.message.edit_text("📂 Введи название новой категории:")
    await state.set_state(NoteStates.waiting_new_category)

@router.callback_query(F.data.startswith("cat_delete_"))
async def cb_delete_category(callback: CallbackQuery, user: User, session: AsyncSession):
    cat_id = int(callback.data.split("_")[2])
    category = await get_category(session, cat_id)
    if not category:
        await callback.answer("❌ Категория не найдена.")
        return
    if category.owner_id != user.telegram_id and user.role not in ["owner", "admin"]:
        await callback.answer("⛔ Нет доступа.")
        return
    await delete_category(session, cat_id)
    await callback.message.edit_text("🗑 Категория удалена.", reply_markup=back_button("notes_categories"))

@router.callback_query(F.data == "notes_search")
async def cb_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔍 Введи текст для поиска:", reply_markup=back_button("notes_main"))
    await state.set_state(NoteStates.waiting_search)

@router.message(NoteStates.waiting_search)
async def process_search(message: Message, state: FSMContext, user: User, session: AsyncSession):
    await state.clear()
    notes = await search_notes(session, user.telegram_id, message.text)
    if not notes:
        await message.answer("🔍 Ничего не найдено.", reply_markup=back_button("notes_main"))
        return
    buttons = []
    for note in notes:
        icon = "🌐" if note.is_shared else "📄"
        buttons.append([InlineKeyboardButton(text=f"{icon} {note.title}", callback_data=f"note_view_{note.id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="notes_main")])
    await message.answer(f"🔍 Найдено заметок: {len(notes)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
