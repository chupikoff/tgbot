import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models.user import User
from services.game_service import get_or_create_player, add_xp
from services.game_data import ABANDONED_SCENARIOS, TRAINING_OPTIONS, get_level_info
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

class AbandonedState(StatesGroup):
    in_scenario = State()

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

# ─── ТРЕНИРОВОЧНАЯ СТАНЦИЯ ───────────────────────────────────────────────────

@router.callback_query(F.data == "game_training")
async def cb_game_training(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)

    buttons = []
    for i, opt in enumerate(TRAINING_OPTIONS):
        affordable = "✅" if player.credits >= opt["cost"] else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{affordable} {opt['label']}",
            callback_data=f"game_train_{i}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_main")])

    level_info = get_level_info(player.xp)
    xp_text = f"{player.xp}/{level_info['xp_next']} XP" if level_info["xp_next"] else f"{player.xp} XP (макс)"

    try:
        await callback.message.edit_text(
            f"🎓 Training Hub\n\n"
            f"Здесь можно пройти тренировки и получить опыт за кредиты.\n\n"
            f"💰 Кредиты: {player.credits}\n"
            f"✨ Опыт: {xp_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"🎓 Training Hub\n\n"
            f"Здесь можно пройти тренировки и получить опыт за кредиты.\n\n"
            f"💰 Кредиты: {player.credits}\n"
            f"✨ Опыт: {xp_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data.startswith("game_train_"))
async def cb_game_train(callback: CallbackQuery, user: User, session: AsyncSession):
    idx = int(callback.data.replace("game_train_", ""))
    player = await get_or_create_player(session, user.telegram_id)
    opt = TRAINING_OPTIONS[idx]

    if player.credits < opt["cost"]:
        await callback.answer("❌ Недостаточно кредитов.")
        return

    player.credits -= opt["cost"]
    levels_gained = await add_xp(session, player, opt["xp"])
    await session.commit()

    level_text = f"\n\n🎉 Новый уровень! +{levels_gained * 2} очков характеристик!" if levels_gained > 0 else ""
    await callback.answer(f"✅ +{opt['xp']} XP!")
    await cb_game_training(callback, user, session)

# ─── ЗАБРОШЕННАЯ СТАНЦИЯ ─────────────────────────────────────────────────────

@router.callback_query(F.data == "game_abandoned")
async def cb_game_abandoned(callback: CallbackQuery, user: User, state: FSMContext, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)

    if player.explored_location == player.location:
        await callback.answer("🏚 Ты уже исследовал эту станцию. Прилети снова.")
        return

    scenario = random.choice(ABANDONED_SCENARIOS)
    await state.set_state(AbandonedState.in_scenario)
    await state.update_data(scenario_id=scenario["id"])

    buttons = []
    for choice in scenario["choices"]:
        buttons.append([InlineKeyboardButton(
            text=choice["label"],
            callback_data=f"game_ab_{choice['next']}"
        )])

    try:
        await callback.message.edit_text(
            f"🏚 Abandoned Post\n\n{scenario['intro']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"🏚 Abandoned Post\n\n{scenario['intro']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data.startswith("game_ab_"))
async def cb_game_ab_scene(callback: CallbackQuery, user: User, state: FSMContext, session: AsyncSession):
    scene_id = callback.data.replace("game_ab_", "")
    player = await get_or_create_player(session, user.telegram_id)

    if scene_id == "leave":
        player.explored_location = player.location
        await session.commit()
        await state.clear()
        try:
            await callback.message.edit_text(
                "🚀 Ты улетаешь. Может оно и к лучшему.",
                reply_markup=back_button("game_main")
            )
        except Exception:
            await callback.message.answer(
                "🚀 Ты улетаешь. Может оно и к лучшему.",
                reply_markup=back_button("game_main")
            )
        return

    data = await state.get_data()
    scenario_id = data.get("scenario_id")
    scenario = next((s for s in ABANDONED_SCENARIOS if s["id"] == scenario_id), None)

    if not scenario:
        await state.clear()
        await callback.answer("❌ Ошибка сценария.")
        return

    scene = scenario["scenes"].get(scene_id)
    if not scene:
        await state.clear()
        await callback.answer("❌ Сцена не найдена.")
        return

    if scene.get("final"):
        result = scene["result"]
        player.credits = max(0, player.credits + result["credits"])
        player.hull = max(0, min(player.hull + result["hull"], player.hull_max))
        player.explored_location = player.location
        xp = result.get("xp", 0)
        levels_gained = 0
        if xp > 0:
            levels_gained = await add_xp(session, player, xp)
        await session.commit()
        await state.clear()

        deltas = []
        if result["credits"] > 0:
            deltas.append(f"💰 +{result['credits']} кредитов")
        elif result["credits"] < 0:
            deltas.append(f"💰 {result['credits']} кредитов")
        if result["hull"] < 0:
            deltas.append(f"❤️ {result['hull']} корпуса")
        if xp > 0:
            deltas.append(f"✨ +{xp} XP")
        if levels_gained > 0:
            deltas.append(f"🎉 Новый уровень! +{levels_gained * 2} очков!")

        delta_text = "\n".join(deltas) if deltas else "Без изменений."

        text = (
            f"🏚 Abandoned Post\n\n"
            f"{scene['text']}\n\n"
            f"{delta_text}\n\n"
            f"❤️ {player.hull}/{player.hull_max} | ⛽ {player.fuel}/{player.fuel_tank} | 💰 {player.credits}"
        )

        if player.hull <= 0:
            from handlers.game import dead_menu
            text += "\n\n💀 Корабль уничтожен!"
            try:
                await callback.message.edit_text(text, reply_markup=dead_menu())
            except Exception:
                await callback.message.answer(text, reply_markup=dead_menu())
        else:
            try:
                await callback.message.edit_text(text, reply_markup=back_button("game_main"))
            except Exception:
                await callback.message.answer(text, reply_markup=back_button("game_main"))
        return

    buttons = []
    for choice in scene["choices"]:
        buttons.append([InlineKeyboardButton(
            text=choice["label"],
            callback_data=f"game_ab_{choice['next']}"
        )])

    try:
        await callback.message.edit_text(
            f"🏚 Abandoned Post\n\n{scene['text']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"🏚 Abandoned Post\n\n{scene['text']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
