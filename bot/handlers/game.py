from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from models.game import GamePlayer
from services.game_service import get_or_create_player, fly_to, refuel, repair, buy_upgrade, get_player_events, reset_player, spend_skill_point, self_repair, evacuate
from services.game_data import get_reachable_locations, get_location_system, LOCATIONS, SYSTEMS, ENGINES, FUEL_TANKS, HULLS, FUEL_PRICE, REPAIR_PRICE, MINING_DATA, get_mining_result, get_level_info, get_effective_engine_range, get_trade_discount, get_mechanic_repair, SKILL_MAX, XP_REWARDS, can_evacuate, get_min_fuel_needed
from services.game_image_service import get_image
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

def has_game_access(user: User) -> bool:
    return user.role in ["owner", "admin", "user"]

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

def game_main_menu(player: GamePlayer = None) -> InlineKeyboardMarkup:
    buttons = []
    buttons.append([InlineKeyboardButton(text="🚀 Полететь", callback_data="game_fly")])

    if player:
        location = LOCATIONS.get(player.location, {})
        if location.get("has_hangar"):
            buttons.append([InlineKeyboardButton(text="🔧 Ангар", callback_data="game_hangar")])
        if location.get("has_shop"):
            buttons.append([InlineKeyboardButton(text="🛒 Магазин", callback_data="game_shop")])
        if location.get("type") == "uninhabited" and player.location in MINING_DATA and player.mined_location != player.location:
            buttons.append([InlineKeyboardButton(text="⛏ Добыть ресурсы", callback_data="game_mine")])
        if location.get("type") == "training":
            buttons.append([InlineKeyboardButton(text="🎓 Тренировки", callback_data="game_training")])
        if location.get("type") == "abandoned" and player.explored_location != player.location:
            buttons.append([InlineKeyboardButton(text="🏚 Исследовать станцию", callback_data="game_abandoned")])
        if player.skill_mechanic > 0 and player.hull < player.hull_max:
            buttons.append([InlineKeyboardButton(text="🔩 Починить корабль", callback_data="game_self_repair")])
        if can_evacuate(player):
            buttons.append([InlineKeyboardButton(text="🆘 Эвакуация (60% кредитов)", callback_data="game_evacuate")])

        min_fuel = get_min_fuel_needed(player.location)
        min_fuel_cost = min_fuel * FUEL_PRICE
        if player.fuel == 0 and player.credits < min_fuel_cost:
            buttons.append([InlineKeyboardButton(text="💀 Нет выхода — начать заново", callback_data="game_reset_confirm")])

    buttons.append([InlineKeyboardButton(text="🛸 Корабль", callback_data="game_ship")])
    buttons.append([InlineKeyboardButton(text="📊 Характеристики", callback_data="game_skills")])
    buttons.append([InlineKeyboardButton(text="🗺 Карта", callback_data="game_map")])
    buttons.append([InlineKeyboardButton(text="📜 Журнал", callback_data="game_log")])
    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_player_status(player: GamePlayer) -> str:
    location = LOCATIONS.get(player.location, {})
    system = location.get("system", "???")
    level_info = get_level_info(player.xp)
    effective_range = get_effective_engine_range(player)

    xp_text = f"{player.xp}/{level_info['xp_next']} XP" if level_info["xp_next"] else f"{player.xp} XP (макс)"
    skill_points_text = f" (+{player.skill_points} очков!)" if player.skill_points > 0 else ""

    return (
        f"🛸 {player.ship_name}\n"
        f"📍 {player.location} [{system}]\n\n"
        f"❤️ Корпус: {player.hull}/{player.hull_max}\n"
        f"⛽ Топливо: {player.fuel}/{player.fuel_tank}\n"
        f"💰 Кредиты: {player.credits}\n"
        f"🔧 Двигатель: range {effective_range}\n"
        f"📦 Грузовой отсек: {player.cargo_used}/{player.cargo_max}\n"
        f"🌌 Прыжков: {player.total_jumps}\n\n"
        f"{level_info['title']} | {xp_text}{skill_points_text}"
    )

def dead_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Начать заново", callback_data="game_reset_confirm")],
    ])

@router.message(Command("game"))
async def cmd_game(message: Message, user: User, session: AsyncSession):
    if not has_game_access(user):
        await message.answer("⛔ Недостаточно прав.")
        return
    player = await get_or_create_player(session, user.telegram_id)
    await message.answer(
        f"🌌 Добро пожаловать в космос, пилот!\n\n{format_player_status(player)}",
        reply_markup=game_main_menu(player)
    )

@router.callback_query(F.data == "game_main")
async def cb_game_main(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    if player.hull <= 0:
        try:
            await callback.message.edit_text(
                "💀 Корабль уничтожен.\n\nТвой корабль не выдержал повреждений.",
                reply_markup=dead_menu()
            )
        except Exception:
            await callback.message.answer(
                "💀 Корабль уничтожен.\n\nТвой корабль не выдержал повреждений.",
                reply_markup=dead_menu()
            )
        return
    text = format_player_status(player)
    try:
        await callback.message.edit_text(text, reply_markup=game_main_menu(player))
    except Exception:
        await callback.message.answer(text, reply_markup=game_main_menu(player))

@router.callback_query(F.data == "game_ship")
async def cb_game_ship(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    effective_range = get_effective_engine_range(player)
    discount = get_trade_discount(player)
    text = (
        f"🛸 {player.ship_name}\n\n"
        f"❤️ Корпус: {player.hull}/{player.hull_max}\n"
        f"⛽ Топливный бак: {player.fuel}/{player.fuel_tank}\n"
        f"🔧 Дальность двигателя: {effective_range} pc\n"
        f"📦 Грузовой отсек: {player.cargo_used}/{player.cargo_max}\n\n"
        f"💰 Кредиты: {player.credits}\n"
        f"🌌 Всего прыжков: {player.total_jumps}\n"
    )
    if discount > 0:
        text += f"🤝 Торговая скидка: {int(discount * 100)}%\n"
    try:
        await callback.message.edit_text(text, reply_markup=back_button("game_main"))
    except Exception:
        await callback.message.answer(text, reply_markup=back_button("game_main"))

@router.callback_query(F.data == "game_skills")
async def cb_game_skills(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    level_info = get_level_info(player.xp)

    if level_info["xp_next"]:
        needed = level_info["xp_next"] - player.xp
        xp_text = f"{player.xp}/{level_info['xp_next']} XP (ещё {needed})"
    else:
        xp_text = f"{player.xp} XP (макс уровень)"

    text = (
        f"📊 Характеристики\n\n"
        f"{level_info['title']}\n"
        f"Опыт: {xp_text}\n"
        f"Свободных очков: {player.skill_points}\n\n"
        f"🤝 Торговля: {player.skill_trade}/{SKILL_MAX} — скидка {player.skill_trade * 5}%\n"
        f"🛡 Инженер: {player.skill_engineer}/{SKILL_MAX} — +{player.skill_engineer * 10}% корпуса, -{player.skill_engineer * 5}% урона\n"
        f"🔩 Механик: {player.skill_mechanic}/{SKILL_MAX} — ремонт {player.skill_mechanic * 5} hp в космосе\n"
        f"🚀 Пилот: {player.skill_pilot}/{SKILL_MAX} — +{player.skill_pilot} pc к дальности\n"
    )

    buttons = []
    if player.skill_points > 0:
        skills = [
            ("trade",    "🤝 Торговля", player.skill_trade),
            ("engineer", "🛡 Инженер",  player.skill_engineer),
            ("mechanic", "🔩 Механик",  player.skill_mechanic),
            ("pilot",    "🚀 Пилот",    player.skill_pilot),
        ]
        for skill_key, skill_name, skill_val in skills:
            if skill_val < SKILL_MAX:
                buttons.append([InlineKeyboardButton(
                    text=f"+ {skill_name} ({skill_val}/{SKILL_MAX})",
                    callback_data=f"game_skill_{skill_key}"
                )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_main")])
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("game_skill_"))
async def cb_game_skill(callback: CallbackQuery, user: User, session: AsyncSession):
    skill = callback.data.replace("game_skill_", "")
    player = await get_or_create_player(session, user.telegram_id)
    result = await spend_skill_point(session, player, skill)
    if result["success"]:
        await callback.answer("✅ Характеристика улучшена!")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_game_skills(callback, user, session)

@router.callback_query(F.data == "game_self_repair")
async def cb_game_self_repair(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    result = await self_repair(session, player)
    if result["success"]:
        await callback.answer(f"🔩 Починено {result['amount']} hp. Потрачено 1 топливо.")
    else:
        await callback.answer(f"❌ {result['error']}")
    text = format_player_status(player)
    try:
        await callback.message.edit_text(text, reply_markup=game_main_menu(player))
    except Exception:
        await callback.message.answer(text, reply_markup=game_main_menu(player))

@router.callback_query(F.data == "game_evacuate")
async def cb_game_evacuate(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    cost = int(player.credits * 0.6)
    buttons = [
        [InlineKeyboardButton(text=f"✅ Подтвердить ({cost} cr)", callback_data="game_evacuate_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="game_main")],
    ]
    try:
        await callback.message.edit_text(
            f"🆘 Эвакуация\n\n"
            f"Стоимость: {cost} cr (60% от {player.credits} cr)\n\n"
            f"✅ Доставка на ближайшую станцию\n"
            f"✅ Полная заправка бака ({player.fuel_tank} ед.)\n\n"
            f"Минимум для эвакуации: 200 cr",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"🆘 Эвакуация\n\nСтоимость: {cost} cr\nДоставка на станцию + полная заправка.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data == "game_evacuate_confirm")
async def cb_game_evacuate_confirm(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    result = await evacuate(session, player)
    if result["success"]:
        text = (
            f"🆘 Эвакуация выполнена!\n\n"
            f"Доставлен на: {result['station']}\n"
            f"Стоимость: {result['cost']} cr\n"
            f"Бак заправлен полностью.\n\n"
            f"❤️ {player.hull}/{player.hull_max} | ⛽ {player.fuel}/{player.fuel_tank} | 💰 {player.credits}"
        )
        try:
            await callback.message.edit_text(text, reply_markup=game_main_menu(player))
        except Exception:
            await callback.message.answer(text, reply_markup=game_main_menu(player))
    else:
        await callback.answer(f"❌ {result['error']}")

@router.callback_query(F.data == "game_mine")
async def cb_game_mine(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    mining = MINING_DATA.get(player.location)

    if not mining:
        await callback.answer("🚫 Здесь нельзя добывать ресурсы.")
        return
    if player.mined_location == player.location:
        await callback.answer("⛏ Ты уже добывал здесь. Прилети снова чтобы добыть ещё.")
        return
    if player.fuel < mining["fuel_cost"]:
        await callback.answer(f"❌ Недостаточно топлива. Нужно {mining['fuel_cost']} ед.")
        return

    result = get_mining_result(player.location)
    player.fuel -= result["fuel_cost"]
    player.credits = max(0, player.credits + result["credits"])
    player.hull = max(0, min(player.hull + result["hull"], player.hull_max))
    player.mined_location = player.location

    from services.game_service import add_xp
    xp = XP_REWARDS.get("mining", 5)
    levels_gained = await add_xp(session, player, xp)
    await session.commit()

    credits_text = f"💰 +{result['credits']} кредитов" if result["credits"] > 0 else ""
    hull_text = f"❤️ {result['hull']} корпуса" if result["hull"] < 0 else ""
    delta_parts = [x for x in [credits_text, hull_text] if x]
    delta_text = "\n".join(delta_parts) if delta_parts else "Без изменений."
    xp_text = f"\n✨ +{xp} XP"
    if levels_gained > 0:
        xp_text += f"\n🎉 Новый уровень! +{levels_gained * 2} очков характеристик!"

    text = (
        f"⛏ Добыча на {player.location}\n\n"
        f"{result['text']}\n\n"
        f"{delta_text}{xp_text}\n\n"
        f"❤️ {player.hull}/{player.hull_max} | ⛽ {player.fuel}/{player.fuel_tank} | 💰 {player.credits}"
    )

    if player.hull <= 0:
        try:
            await callback.message.edit_text(f"{text}\n\n💀 Корабль уничтожен!", reply_markup=dead_menu())
        except Exception:
            await callback.message.answer(f"{text}\n\n💀 Корабль уничтожен!", reply_markup=dead_menu())
        return

    buttons = [[InlineKeyboardButton(text="◀️ Назад", callback_data="game_main")]]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "game_fly")
async def cb_game_fly(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    current_system = get_location_system(player.location)

    buttons = [
        [InlineKeyboardButton(text=f"🌍 В пределах системы {current_system}", callback_data="game_fly_internal")],
        [InlineKeyboardButton(text="🌟 Межсистемный прыжок", callback_data="game_fly_systems")],
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_main")])

    text = f"🚀 Куда летим?\n📍 Сейчас: {player.location} [{current_system}]\n⛽ Топливо: {player.fuel}/{player.fuel_tank}"
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "game_fly_internal")
async def cb_game_fly_internal(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    effective_range = get_effective_engine_range(player)
    destinations = get_reachable_locations(player.location, effective_range, player.fuel)

    buttons = []
    for d in destinations["internal"]:
        loc = d["location"]
        icon = "🟢" if d["can_reach"] else "🔴"
        type_icon = {"station": "🛸", "planet": "🌍", "uninhabited": "🪨", "abandoned": "🏚", "training": "🎓"}.get(loc.get("type"), "❓")
        fuel_text = f"⛽{d['fuel_cost']}"
        if d["can_reach"]:
            buttons.append([InlineKeyboardButton(
                text=f"{icon} {type_icon} {d['name']} [{d['distance']} pc] {fuel_text}",
                callback_data=f"game_jump_{d['name']}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                text=f"{icon} {type_icon} {d['name']} [{d['distance']} pc] {fuel_text}",
                callback_data="game_cant_reach"
            )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_fly")])
    current_system = get_location_system(player.location)
    text = f"📍 Система {current_system}\n⛽ Топливо: {player.fuel}/{player.fuel_tank}"
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "game_fly_systems")
async def cb_game_fly_systems(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    effective_range = get_effective_engine_range(player)
    destinations = get_reachable_locations(player.location, effective_range, player.fuel)

    buttons = []
    for s in destinations["systems"]:
        icon = "🟢" if s["can_reach"] else "🔴"
        fuel_text = f"⛽{s['fuel_cost']}"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} 🌟 {s['name']} [{s['distance']} pc] {fuel_text}",
            callback_data=f"game_system_{s['name']}"
        )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_fly")])
    text = f"🌟 Межсистемный прыжок\n⛽ Топливо: {player.fuel}/{player.fuel_tank}\n🔧 Дальность: {effective_range} pc"
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("game_system_"))
async def cb_game_system(callback: CallbackQuery, user: User, session: AsyncSession):
    system_name = callback.data.replace("game_system_", "")
    player = await get_or_create_player(session, user.telegram_id)
    system = SYSTEMS.get(system_name)

    if not system:
        await callback.answer("❌ Система не найдена.")
        return

    current_system = get_location_system(player.location)
    from services.game_data import get_system_distance
    dist = get_system_distance(current_system, system_name)
    effective_range = get_effective_engine_range(player)
    can_reach = dist <= player.fuel and dist <= effective_range

    buttons = []
    for loc_name in system["locations"]:
        loc = LOCATIONS.get(loc_name, {})
        type_icon = {"station": "🛸", "planet": "🌍", "uninhabited": "🪨", "abandoned": "🏚", "training": "🎓"}.get(loc.get("type"), "❓")
        type_name = {"station": "станция", "planet": "планета", "uninhabited": "необитаемая", "abandoned": "заброшенная", "training": "тренировочная"}.get(loc.get("type"), "")
        if can_reach:
            buttons.append([InlineKeyboardButton(
                text=f"🚀 {type_icon} {loc_name} — {type_name}",
                callback_data=f"game_jump_{loc_name}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                text=f"🔴 {type_icon} {loc_name} — {type_name}",
                callback_data="game_cant_reach"
            )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_fly_systems")])

    reason = ""
    if not can_reach:
        if dist > effective_range:
            reason = f"\n⚠️ Нужен двигатель с range {dist}, у тебя {effective_range}"
        elif dist > player.fuel:
            reason = f"\n⚠️ Нужно {dist} топлива, у тебя {player.fuel}"

    text = (
        f"🌟 Система {system_name}\n"
        f"{system['description']}\n\n"
        f"Расстояние: {dist} pc ⛽{dist}{reason}"
    )
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "game_cant_reach")
async def cb_cant_reach(callback: CallbackQuery):
    await callback.answer("🔴 Недостаточно топлива или дальности двигателя.")

@router.callback_query(F.data == "game_reset_confirm")
async def cb_game_reset_confirm(callback: CallbackQuery, user: User):
    buttons = [
        [InlineKeyboardButton(text="✅ Да, начать заново", callback_data="game_reset")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="game_main")],
    ]
    try:
        await callback.message.edit_text(
            "⚠️ Ты уверен? Весь прогресс будет потерян.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            "⚠️ Ты уверен? Весь прогресс будет потерян.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data == "game_reset")
async def cb_game_reset(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    player = await reset_player(session, player)
    text = f"🔄 Новое начало.\n\n{format_player_status(player)}"
    try:
        await callback.message.edit_text(text, reply_markup=game_main_menu(player))
    except Exception:
        await callback.message.answer(text, reply_markup=game_main_menu(player))

@router.callback_query(F.data.startswith("game_jump_"))
async def cb_game_jump(callback: CallbackQuery, user: User, session: AsyncSession):
    destination = callback.data.replace("game_jump_", "")
    player = await get_or_create_player(session, user.telegram_id)

    result = await fly_to(session, player, destination)

    if not result["success"]:
        try:
            await callback.message.edit_text(
                f"❌ {result['error']}",
                reply_markup=back_button("game_fly")
            )
        except Exception:
            await callback.message.answer(f"❌ {result['error']}", reply_markup=back_button("game_fly"))
        return

    event = result["event"]
    p = result["player"]
    is_jump = result.get("is_jump", False)
    is_dead = result.get("is_dead", False)
    xp_gained = result.get("xp_gained", 0)
    levels_gained = result.get("levels_gained", 0)

    deltas = []
    if event.credits_delta > 0:
        deltas.append(f"💰 +{event.credits_delta} кредитов")
    elif event.credits_delta < 0:
        deltas.append(f"💰 {event.credits_delta} кредитов")
    if event.fuel_delta > 0:
        deltas.append(f"⛽ +{event.fuel_delta} топлива")
    elif event.fuel_delta < 0:
        deltas.append(f"⛽ {event.fuel_delta} топлива")
    if event.hull_delta > 0:
        deltas.append(f"❤️ +{event.hull_delta} корпуса")
    elif event.hull_delta < 0:
        deltas.append(f"❤️ {event.hull_delta} корпуса")
    if xp_gained > 0:
        deltas.append(f"✨ +{xp_gained} XP")
    if levels_gained > 0:
        deltas.append(f"🎉 Новый уровень! +{levels_gained * 2} очков!")

    delta_text = "\n".join(deltas) if deltas else "Без изменений."
    jump_text = "🌟 Межсистемный прыжок!\n" if is_jump else ""

    text = (
        f"{jump_text}"
        f"📍 Прибыл: {destination}\n"
        f"⛽ Потрачено топлива: {result['fuel_spent']}\n\n"
        f"{event.title}\n"
        f"{event.text}\n\n"
        f"{delta_text}\n\n"
        f"❤️ {p.hull}/{p.hull_max} | ⛽ {p.fuel}/{p.fuel_tank} | 💰 {p.credits}"
    )

    if is_dead:
        text += "\n\n💀 Корабль уничтожен!"
        image = await get_image(session, destination)
        if image:
            await callback.message.answer_photo(image.file_id, caption=text, reply_markup=dead_menu())
        else:
            try:
                await callback.message.edit_text(text, reply_markup=dead_menu())
            except Exception:
                await callback.message.answer(text, reply_markup=dead_menu())
        return

    location = LOCATIONS.get(destination, {})
    buttons = []
    if location.get("has_hangar"):
        buttons.append([InlineKeyboardButton(text="🔧 Ангар", callback_data="game_hangar")])
    if location.get("has_shop"):
        buttons.append([InlineKeyboardButton(text="🛒 Магазин", callback_data="game_shop")])
    if location.get("type") == "uninhabited" and destination in MINING_DATA:
        buttons.append([InlineKeyboardButton(text="⛏ Добыть ресурсы", callback_data="game_mine")])
    if location.get("type") == "training":
        buttons.append([InlineKeyboardButton(text="🎓 Тренировки", callback_data="game_training")])
    if location.get("type") == "abandoned":
        buttons.append([InlineKeyboardButton(text="🏚 Исследовать станцию", callback_data="game_abandoned")])
    buttons.append([InlineKeyboardButton(text="🚀 Лететь дальше", callback_data="game_fly")])
    buttons.append([InlineKeyboardButton(text="📊 Статус", callback_data="game_main")])

    image = await get_image(session, destination)
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    if image:
        await callback.message.answer_photo(image.file_id, caption=text, reply_markup=markup)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=markup)
        except Exception:
            await callback.message.answer(text, reply_markup=markup)

@router.callback_query(F.data == "game_hangar")
async def cb_game_hangar(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    location = LOCATIONS.get(player.location, {})

    if not location.get("has_hangar"):
        await callback.answer("🚫 Здесь нет ангара.")
        return

    discount = get_trade_discount(player)
    fuel_needed = player.fuel_tank - player.fuel
    fuel_price = int(FUEL_PRICE * (1 - discount))
    fuel_cost = fuel_needed * fuel_price
    repair_needed = player.hull_max - player.hull
    repair_price = int(REPAIR_PRICE * (1 - discount))
    repair_cost = repair_needed * repair_price
    discount_text = f" (скидка {int(discount * 100)}%)" if discount > 0 else ""

    text = (
        f"🔧 Ангар — {player.location}{discount_text}\n\n"
        f"❤️ Корпус: {player.hull}/{player.hull_max}\n"
        f"⛽ Топливо: {player.fuel}/{player.fuel_tank}\n"
        f"💰 Кредиты: {player.credits}\n\n"
        f"Полная заправка: {fuel_needed} ед. = {fuel_cost} кредитов\n"
        f"Полный ремонт: {repair_needed} ед. = {repair_cost} кредитов"
    )

    buttons = []
    if fuel_needed > 0:
        buttons.append([InlineKeyboardButton(
            text=f"⛽ Заправить полностью ({fuel_cost} cr)",
            callback_data="game_refuel_full"
        )])
        buttons.append([InlineKeyboardButton(
            text="⛽ Заправить на 5 ед.",
            callback_data="game_refuel_5"
        )])
    if repair_needed > 0:
        buttons.append([InlineKeyboardButton(
            text=f"🔧 Починить полностью ({repair_cost} cr)",
            callback_data="game_repair_full"
        )])
        buttons.append([InlineKeyboardButton(
            text="🔧 Починить на 20 ед.",
            callback_data="game_repair_20"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("game_refuel_"))
async def cb_game_refuel(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    amount_str = callback.data.replace("game_refuel_", "")
    amount = player.fuel_tank - player.fuel if amount_str == "full" else int(amount_str)
    result = await refuel(session, player, amount)
    if result["success"]:
        await callback.answer(f"⛽ Заправлено {result['amount']} ед. за {result['cost']} кредитов.")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_game_hangar(callback, user, session)

@router.callback_query(F.data.startswith("game_repair_"))
async def cb_game_repair(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    amount_str = callback.data.replace("game_repair_", "")
    amount = player.hull_max - player.hull if amount_str == "full" else int(amount_str)
    result = await repair(session, player, amount)
    if result["success"]:
        await callback.answer(f"🔧 Починено {result['amount']} ед. за {result['cost']} кредитов.")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_game_hangar(callback, user, session)

@router.callback_query(F.data == "game_shop")
async def cb_game_shop(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    location = LOCATIONS.get(player.location, {})
    if not location.get("has_shop"):
        await callback.answer("🚫 Здесь нет магазина.")
        return
    discount = get_trade_discount(player)
    discount_text = f" (скидка {int(discount * 100)}%)" if discount > 0 else ""
    buttons = [
        [InlineKeyboardButton(text="🔧 Двигатели", callback_data="game_shop_engines")],
        [InlineKeyboardButton(text="⛽ Топливные баки", callback_data="game_shop_tanks")],
        [InlineKeyboardButton(text="🛡 Корпус", callback_data="game_shop_hulls")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="game_main")],
    ]
    try:
        await callback.message.edit_text(
            f"🛒 Магазин — {player.location}{discount_text}\n💰 Кредиты: {player.credits}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"🛒 Магазин — {player.location}{discount_text}\n💰 Кредиты: {player.credits}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data == "game_shop_engines")
async def cb_shop_engines(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    discount = get_trade_discount(player)
    buttons = []
    for name, data in ENGINES.items():
        if data["price"] == 0:
            continue
        price = int(data["price"] * (1 - discount))
        affordable = "✅" if player.credits >= price else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{affordable} {name} — range {data['range']} ({price} cr)",
            callback_data=f"game_buy_engine_{name}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_shop")])
    effective_range = get_effective_engine_range(player)
    try:
        await callback.message.edit_text(
            f"🔧 Двигатели\n💰 Кредиты: {player.credits}\n🔧 Текущий range: {effective_range}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"🔧 Двигатели\n💰 Кредиты: {player.credits}\n🔧 Текущий range: {effective_range}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data == "game_shop_tanks")
async def cb_shop_tanks(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    discount = get_trade_discount(player)
    buttons = []
    for name, data in FUEL_TANKS.items():
        if data["price"] == 0:
            continue
        price = int(data["price"] * (1 - discount))
        affordable = "✅" if player.credits >= price else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{affordable} {name} — {data['capacity']} ед. ({price} cr)",
            callback_data=f"game_buy_tank_{name}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_shop")])
    try:
        await callback.message.edit_text(
            f"⛽ Топливные баки\n💰 Кредиты: {player.credits}\n⛽ Текущий бак: {player.fuel_tank}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"⛽ Топливные баки\n💰 Кредиты: {player.credits}\n⛽ Текущий бак: {player.fuel_tank}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data == "game_shop_hulls")
async def cb_shop_hulls(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    discount = get_trade_discount(player)
    buttons = []
    for name, data in HULLS.items():
        if data["price"] == 0:
            continue
        price = int(data["price"] * (1 - discount))
        affordable = "✅" if player.credits >= price else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{affordable} {name} — {data['hp']} hp ({price} cr)",
            callback_data=f"game_buy_hull_{name}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_shop")])
    try:
        await callback.message.edit_text(
            f"🛡 Корпус\n💰 Кредиты: {player.credits}\n❤️ Текущий: {player.hull_max} hp",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"🛡 Корпус\n💰 Кредиты: {player.credits}\n❤️ Текущий: {player.hull_max} hp",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data.startswith("game_buy_engine_"))
async def cb_buy_engine(callback: CallbackQuery, user: User, session: AsyncSession):
    name = callback.data.replace("game_buy_engine_", "")
    player = await get_or_create_player(session, user.telegram_id)
    result = await buy_upgrade(session, player, "engine", name)
    if result["success"]:
        await callback.answer(f"✅ Двигатель {name} установлен!")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_shop_engines(callback, user, session)

@router.callback_query(F.data.startswith("game_buy_tank_"))
async def cb_buy_tank(callback: CallbackQuery, user: User, session: AsyncSession):
    name = callback.data.replace("game_buy_tank_", "")
    player = await get_or_create_player(session, user.telegram_id)
    result = await buy_upgrade(session, player, "fuel_tank", name)
    if result["success"]:
        await callback.answer(f"✅ Топливный бак {name} установлен!")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_shop_tanks(callback, user, session)

@router.callback_query(F.data.startswith("game_buy_hull_"))
async def cb_buy_hull(callback: CallbackQuery, user: User, session: AsyncSession):
    name = callback.data.replace("game_buy_hull_", "")
    player = await get_or_create_player(session, user.telegram_id)
    result = await buy_upgrade(session, player, "hull", name)
    if result["success"]:
        await callback.answer(f"✅ Корпус {name} установлен!")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_shop_hulls(callback, user, session)

@router.callback_query(F.data == "game_map")
async def cb_game_map(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    text = "🗺 Галактическая карта\n\n"
    for system_name, system_data in SYSTEMS.items():
        text += f"⭐ {system_name}\n"
        for loc_name in system_data["locations"]:
            loc_data = LOCATIONS.get(loc_name, {})
            type_icon = {"station": "🛸", "planet": "🌍", "uninhabited": "🪨", "abandoned": "🏚", "training": "🎓"}.get(loc_data.get("type"), "❓")
            current = " ← ТЫ ЗДЕСЬ" if loc_name == player.location else ""
            text += f"  {type_icon} {loc_name}{current}\n"
        text += "\n"

    map_image = await get_image(session, "map")
    if map_image:
        await callback.message.answer_photo(map_image.file_id, caption=text, reply_markup=back_button("game_main"))
    else:
        try:
            await callback.message.edit_text(text, reply_markup=back_button("game_main"))
        except Exception:
            await callback.message.answer(text, reply_markup=back_button("game_main"))

@router.callback_query(F.data == "game_log")
async def cb_game_log(callback: CallbackQuery, user: User, session: AsyncSession):
    events = await get_player_events(session, user.telegram_id, limit=5)
    if not events:
        try:
            await callback.message.edit_text(
                "📜 Журнал пуст. Начни своё путешествие!",
                reply_markup=back_button("game_main")
            )
        except Exception:
            await callback.message.answer(
                "📜 Журнал пуст. Начни своё путешествие!",
                reply_markup=back_button("game_main")
            )
        return

    text = "📜 Последние события:\n\n"
    for e in events:
        text += f"📍 {e.location}\n"
        text += f"{e.event_text[:100]}...\n"
        deltas = []
        if e.credits_delta != 0:
            deltas.append(f"💰{'+' if e.credits_delta > 0 else ''}{e.credits_delta}")
        if e.fuel_delta != 0:
            deltas.append(f"⛽{'+' if e.fuel_delta > 0 else ''}{e.fuel_delta}")
        if e.hull_delta != 0:
            deltas.append(f"❤️{'+' if e.hull_delta > 0 else ''}{e.hull_delta}")
        if deltas:
            text += " ".join(deltas) + "\n"
        text += "\n"

    try:
        await callback.message.edit_text(text, reply_markup=back_button("game_main"))
    except Exception:
        await callback.message.answer(text, reply_markup=back_button("game_main"))
