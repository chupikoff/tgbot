import asyncio
import os
import glob
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()


class YoutubeStates(StatesGroup):
    waiting_url = State()


def back_button(cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=cb)]
    ])


@router.callback_query(F.data == "menu_youtube")
async def cb_youtube(callback: CallbackQuery, state: FSMContext):
    await state.set_state(YoutubeStates.waiting_url)
    await state.update_data(prompt_id=callback.message.message_id)
    try:
        await callback.message.edit_text(
            "📥 Отправь ссылку на YouTube или Instagram видео:",
            reply_markup=back_button("menu_main")
        )
    except Exception:
        await callback.message.answer(
            "📥 Отправь ссылку на YouTube или Instagram видео:",
            reply_markup=back_button("menu_main")
        )


@router.message(YoutubeStates.waiting_url)
async def process_youtube_url(message: Message, state: FSMContext):
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
    status_msg = await message.answer("⏳ Скачиваю видео...")

    try:
        import uuid
        uid = uuid.uuid4().hex
        output_template = f"/tmp/yt_{uid}.%(ext)s"

        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "-f", "best[ext=mp4]/best",
            "--max-filesize", "50m",
            "--no-playlist",
            "-o", output_template,
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            await status_msg.edit_text(
                f"❌ Ошибка скачивания:\n{stderr.decode()[:500]}",
                reply_markup=back_button("menu_main")
            )
            return

        # Ищем скачанный файл
        files = glob.glob(f"/tmp/yt_{uid}.*")
        if not files:
            await status_msg.edit_text("❌ Файл не найден после скачивания.", reply_markup=back_button("menu_main"))
            return

        filepath = files[0]
        await status_msg.edit_text("📤 Отправляю...")
        video = FSInputFile(filepath)
        sent = await message.answer_video(video)
        await status_msg.delete()
        os.remove(filepath)
        # Кнопка назад с удалением видео
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data=f"yt_back_{sent.message_id}")]
        ])
        await sent.edit_reply_markup(reply_markup=markup)

    except asyncio.TimeoutError:
        await status_msg.edit_text("❌ Таймаут — видео слишком большое или долго скачивается.", reply_markup=back_button("menu_main"))
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}", reply_markup=back_button("menu_main"))


@router.callback_query(F.data.startswith("yt_back_"))
async def cb_yt_back(callback: CallbackQuery, user):
    try:
        await callback.message.delete()
    except Exception:
        pass
    from handlers.start import start_text, main_menu
    await callback.message.answer(start_text(user), reply_markup=main_menu(user))
