from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from models.game import GamePlayer
from services.game_service import get_or_create_player, fly_to, refuel, repair, buy_upgrade, get_player_events, emergency_refuel, reset_player
from services.game_data import get_reachable_locations, LOCATIONS, ENGINES, FUEL_TANKS, HULLS, FUEL_PRICE, REPAIR_PRICE
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

    buttons.append([InlineKeyboardButton(text="🛸 Корабль", callback_data="game_ship")])
    buttons.append([InlineKeyboardButton(text="🗺 Карта", callback_data="game_map")])
    buttons.append([InlineKeyboardButton(text="📜 Журнал", callback_data="game_log")])
    buttons.append([InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_player_status(player: GamePlayer) -> str:
    hull_bar = "█" * (player.hull // 10) + "░" * (10 - player.hull // 10)
    fuel_bar = "█" * (player.fuel * 10 // player.fuel_tank) + "░" * (10 - player.fuel * 10 // player.fuel_tank)
    location = LOCATIONS.get(player.location, {})
    system = location.get("system", "???")

    return (
        f"🛸 {player.ship_name}\n"
        f"📍 {player.location} [{system}]\n\n"
        f"❤️ Корпус:  {hull_bar} {player.hull}/{player.hull_max}\n"
        f"⛽ Топливо: {fuel_bar} {player.fuel}/{player.fuel_tank}\n"
        f"💰 Кредиты: {player.credits}\n"
        f"🔧 Двигатель: range {player.engine_range}\n"
        f"📦 Карго: {player.cargo_used}/{player.cargo_max}\n"
        f"🌌 Прыжков: {player.total_jumps}"
    )

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
    await callback.message.edit_text(
        format_player_status(player),
        reply_markup=game_main_menu(player)
    )

@router.callback_query(F.data == "game_ship")
async def cb_game_ship(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    text = (
        f"🛸 {player.ship_name}\n\n"
        f"❤️ Корпус: {player.hull}/{player.hull_max}\n"
        f"⛽ Топливный бак: {player.fuel}/{player.fuel_tank}\n"
        f"🔧 Дальность двигателя: {player.engine_range} pc\n"
        f"📦 Карго: {player.cargo_used}/{player.cargo_max}\n\n"
        f"💰 Кредиты: {player.credits}\n"
        f"🌌 Всего прыжков: {player.total_jumps}"
    )
    await callback.message.edit_text(text, reply_markup=back_button("game_main"))

@router.callback_query(F.data == "game_fly")
async def cb_game_fly(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    destinations = get_reachable_locations(player.location, player.engine_range, player.fuel)

    if not destinations:
        await callback.message.edit_text(
            "🚫 Нет доступных маршрутов.",
            reply_markup=back_button("game_main")
        )
        return

    buttons = []
    for d in destinations:
        loc = d["location"]
        icon = "🟢" if d["can_reach"] else "🔴"
        type_icon = {"station": "🛸", "planet": "🌍", "uninhabited": "🪨"}.get(loc.get("type"), "❓")
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

    if player.fuel == 0:
        buttons.append([InlineKeyboardButton(
            text="🆘 Аварийная заправка (3 ед. за 150 cr)",
            callback_data="game_emergency_fuel"
        )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_main")])

    await callback.message.edit_text(
        f"🚀 Куда летим?\n📍 Сейчас: {player.location}\n⛽ Топливо: {player.fuel}/{player.fuel_tank}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "game_cant_reach")
async def cb_cant_reach(callback: CallbackQuery):
    await callback.answer("🔴 Недостаточно топлива или дальности двигателя.")

@router.callback_query(F.data == "game_emergency_fuel")
async def cb_emergency_fuel(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    result = await emergency_refuel(session, player)
    if result["success"]:
        await callback.answer(f"🆘 Аварийная заправка: +{result['amount']} ед. за {result['cost']} cr.")
        await cb_game_fly(callback, user, session)
    else:
        buttons = [
            [InlineKeyboardButton(text="🔄 Начать заново", callback_data="game_reset_confirm")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="game_main")],
        ]
        await callback.message.edit_text(
            "💀 Ты застрял в открытом космосе.\n\n"
            "Топлива нет. Кредитов нет.\n"
            "Единственный выход — начать заново.\n\n"
            "Весь прогресс будет сброшен.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data == "game_reset_confirm")
async def cb_game_reset_confirm(callback: CallbackQuery, user: User):
    buttons = [
        [InlineKeyboardButton(text="✅ Да, начать заново", callback_data="game_reset")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="game_main")],
    ]
    await callback.message.edit_text(
        "⚠️ Ты уверен? Весь прогресс будет потерян.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "game_reset")
async def cb_game_reset(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    player = await reset_player(session, player)
    await callback.message.edit_text(
        f"🔄 Новое начало.\n\n{format_player_status(player)}",
        reply_markup=game_main_menu(player)
    )

@router.callback_query(F.data.startswith("game_jump_"))
async def cb_game_jump(callback: CallbackQuery, user: User, session: AsyncSession):
    destination = callback.data.replace("game_jump_", "")
    player = await get_or_create_player(session, user.telegram_id)

    result = await fly_to(session, player, destination)

    if not result["success"]:
        await callback.message.edit_text(
            f"❌ {result['error']}",
            reply_markup=back_button("game_fly")
        )
        return

    event = result["event"]
    p = result["player"]

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

    delta_text = "\n".join(deltas) if deltas else "Без изменений."

    location = LOCATIONS.get(destination, {})
    buttons = []
    if location.get("has_hangar"):
        buttons.append([InlineKeyboardButton(text="🔧 Ангар", callback_data="game_hangar")])
    if location.get("has_shop"):
        buttons.append([InlineKeyboardButton(text="🛒 Магазин", callback_data="game_shop")])
    buttons.append([InlineKeyboardButton(text="🚀 Лететь дальше", callback_data="game_fly")])
    buttons.append([InlineKeyboardButton(text="📊 Статус", callback_data="game_main")])

    text = (
        f"📍 Прибыл: {destination}\n"
        f"⛽ Потрачено топлива: {result['fuel_spent']}\n\n"
        f"{event.title}\n"
        f"{event.text}\n\n"
        f"{delta_text}\n\n"
        f"❤️ {p.hull}/{p.hull_max} | ⛽ {p.fuel}/{p.fuel_tank} | 💰 {p.credits}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "game_hangar")
async def cb_game_hangar(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    location = LOCATIONS.get(player.location, {})

    if not location.get("has_hangar"):
        await callback.answer("🚫 Здесь нет ангара.")
        return

    fuel_needed = player.fuel_tank - player.fuel
    fuel_cost = fuel_needed * FUEL_PRICE
    repair_needed = player.hull_max - player.hull
    repair_cost = repair_needed * REPAIR_PRICE

    text = (
        f"🔧 Ангар — {player.location}\n\n"
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

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

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

    buttons = [
        [InlineKeyboardButton(text="🔧 Двигатели", callback_data="game_shop_engines")],
        [InlineKeyboardButton(text="⛽ Топливные баки", callback_data="game_shop_tanks")],
        [InlineKeyboardButton(text="🛡 Корпус", callback_data="game_shop_hulls")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="game_main")],
    ]

    await callback.message.edit_text(
        f"🛒 Магазин — {player.location}\n💰 Кредиты: {player.credits}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "game_shop_engines")
async def cb_shop_engines(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    buttons = []
    for name, data in ENGINES.items():
        if data["price"] == 0:
            continue
        affordable = "✅" if player.credits >= data["price"] else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{affordable} {name} — range {data['range']} ({data['price']} cr)",
            callback_data=f"game_buy_engine_{name}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_shop")])
    await callback.message.edit_text(
        f"🔧 Двигатели\n💰 Кредиты: {player.credits}\n🔧 Текущий range: {player.engine_range}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "game_shop_tanks")
async def cb_shop_tanks(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    buttons = []
    for name, data in FUEL_TANKS.items():
        if data["price"] == 0:
            continue
        affordable = "✅" if player.credits >= data["price"] else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{affordable} {name} — {data['capacity']} ед. ({data['price']} cr)",
            callback_data=f"game_buy_tank_{name}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_shop")])
    await callback.message.edit_text(
        f"⛽ Топливные баки\n💰 Кредиты: {player.credits}\n⛽ Текущий бак: {player.fuel_tank}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "game_shop_hulls")
async def cb_shop_hulls(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_or_create_player(session, user.telegram_id)
    buttons = []
    for name, data in HULLS.items():
        if data["price"] == 0:
            continue
        affordable = "✅" if player.credits >= data["price"] else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{affordable} {name} — {data['hp']} hp ({data['price']} cr)",
            callback_data=f"game_buy_hull_{name}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="game_shop")])
    await callback.message.edit_text(
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

    systems = {}
    for loc_name, loc_data in LOCATIONS.items():
        system = loc_data["system"]
        if system not in systems:
            systems[system] = []
        systems[system].append((loc_name, loc_data))

    for system, locs in systems.items():
        text += f"⭐ {system}\n"
        for loc_name, loc_data in locs:
            type_icon = {"station": "🛸", "planet": "🌍", "uninhabited": "🪨"}.get(loc_data["type"], "❓")
            current = " ← ТЫ ЗДЕСЬ" if loc_name == player.location else ""
            text += f"  {type_icon} {loc_name}{current}\n"
        text += "\n"

    await callback.message.edit_text(text, reply_markup=back_button("game_main"))

@router.callback_query(F.data == "game_log")
async def cb_game_log(callback: CallbackQuery, user: User, session: AsyncSession):
    events = await get_player_events(session, user.telegram_id, limit=5)

    if not events:
        await callback.message.edit_text(
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

    await callback.message.edit_text(text, reply_markup=back_button("game_main"))
