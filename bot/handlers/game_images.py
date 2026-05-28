from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models.user import User
from services.game_image_service import get_image, set_image, get_all_images, delete_image
from services.game_data import LOCATIONS
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

VALID_KEYS = ["map"] + list(LOCATIONS.keys())

class GameImageStates(StatesGroup):
    waiting_key = State()
    waiting_image = State()

def is_owner(user: User) -> bool:
    return user.role == "owner"

def game_images_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список изображений", callback_data="gimg_list")],
        [InlineKeyboardButton(text="➕ Добавить изображение", callback_data="gimg_add")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")],
    ])

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

@router.message(Command("gameimages"))
async def cmd_game_images(message: Message, user: User):
    if not is_owner(user):
        await message.answer("⛔ Только для владельца.")
        return
    await message.answer("🖼 Управление изображениями игры:", reply_markup=game_images_menu())

@router.callback_query(F.data == "gimg_main")
async def cb_gimg_main(callback: CallbackQuery, user: User):
    try:
        await callback.message.edit_text("🖼 Управление изображениями игры:", reply_markup=game_images_menu())
    except Exception:
        await callback.message.answer("🖼 Управление изображениями игры:", reply_markup=game_images_menu())

@router.callback_query(F.data == "gimg_list")
async def cb_gimg_list(callback: CallbackQuery, user: User, session: AsyncSession):
    images = await get_all_images(session)

    if not images:
        try:
            await callback.message.edit_text(
                "🖼 Изображений пока нет.",
                reply_markup=back_button("gimg_main")
            )
        except Exception:
            await callback.message.answer(
                "🖼 Изображений пока нет.",
                reply_markup=back_button("gimg_main")
            )
        return

    buttons = []
    for img in images:
        buttons.append([InlineKeyboardButton(
            text=f"🖼 {img.key}",
            callback_data=f"gimg_view_{img.key}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="gimg_main")])

    try:
        await callback.message.edit_text(
            f"🖼 Изображения ({len(images)}):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"🖼 Изображения ({len(images)}):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data.startswith("gimg_view_"))
async def cb_gimg_view(callback: CallbackQuery, user: User, session: AsyncSession):
    key = callback.data.replace("gimg_view_", "")
    image = await get_image(session, key)

    if not image:
        await callback.answer("❌ Изображение не найдено.")
        return

    buttons = [
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"gimg_delete_{key}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="gimg_list")],
    ]

    await callback.message.answer_photo(
        image.file_id,
        caption=f"🖼 Ключ: {key}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("gimg_delete_"))
async def cb_gimg_delete(callback: CallbackQuery, user: User, session: AsyncSession):
    if not is_owner(user):
        await callback.answer("⛔ Только для владельца.")
        return
    key = callback.data.replace("gimg_delete_", "")
    deleted = await delete_image(session, key)
    if deleted:
        await callback.message.delete()
        await callback.message.answer(
            f"🗑 Изображение '{key}' удалено.",
            reply_markup=back_button("gimg_list")
        )
    else:
        await callback.answer("❌ Изображение не найдено.")

@router.callback_query(F.data == "gimg_add")
async def cb_gimg_add(callback: CallbackQuery, state: FSMContext, user: User):
    if not is_owner(user):
        await callback.answer("⛔ Только для владельца.")
        return

    keys_text = "\n".join([f"• {k}" for k in VALID_KEYS])
    try:
        await callback.message.edit_text(
            f"🖼 Введи ключ изображения:\n\n{keys_text}",
            reply_markup=back_button("gimg_main")
        )
    except Exception:
        await callback.message.answer(
            f"🖼 Введи ключ изображения:\n\n{keys_text}",
            reply_markup=back_button("gimg_main")
        )
    await state.set_state(GameImageStates.waiting_key)

@router.message(GameImageStates.waiting_key)
async def process_image_key(message: Message, state: FSMContext):
    key = message.text.strip()
    if key not in VALID_KEYS:
        await message.answer(
            f"❌ Неверный ключ. Доступные ключи:\n" + "\n".join([f"• {k}" for k in VALID_KEYS])
        )
        return
    await state.update_data(key=key)
    await state.set_state(GameImageStates.waiting_image)
    await message.answer(f"🖼 Теперь отправь изображение для '{key}':")

@router.message(GameImageStates.waiting_image)
async def process_image_file(message: Message, state: FSMContext, user: User, session: AsyncSession):
    if not message.photo:
        await message.answer("❌ Отправь изображение.")
        return

    data = await state.get_data()
    key = data["key"]
    file_id = message.photo[-1].file_id

    await set_image(session, key, file_id, user.telegram_id)
    await state.clear()
    await message.answer(
        f"✅ Изображение для '{key}' сохранено!",
        reply_markup=back_button("gimg_main")
    )
