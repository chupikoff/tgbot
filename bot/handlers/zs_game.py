import random as _r
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from models.zombie_survival import ZSPlayer, ZSBase, ZSInventory, ZSNPC
from services.zs_service import (
    get_player, create_player, delete_player,
    get_base, get_inventory, get_npcs, get_max_npcs,
    add_event, get_events, get_random_scenario,
    start_raid, process_raid_option, process_combat_victory,
    process_night, return_npcs, feed_npc, send_npc_on_mission,
    eat_food, use_meds, upgrade_building, craft_equipment,
    get_player_defense, get_player_melee_damage, get_player_ranged_damage,
)
from services.zs_data import (
    RESOURCES, CLASSES, LOCATIONS, EQUIPMENT, BUILDINGS,
    NPC_LEVELS, get_npc_level_data, get_npc_exp_needed,
    TIPS, NIGHT_ATTACK_CHANCE,
)
from services.zs_data import get_horde_stats

router = Router()

class ZSStates(StatesGroup):
    entering_name = State()
    night_attack = State()

def has_access(user: User) -> bool:
    return user.role in ["owner", "admin", "user"]

# ─── ГЛАВНОЕ МЕНЮ ─────────────────────────────────────────────────────────────

def main_menu(player: ZSPlayer, base: ZSBase) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🗺 Вылазка", callback_data="zs_raid"),
         InlineKeyboardButton(text="🏠 База", callback_data="zs_base")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="zs_inventory"),
         InlineKeyboardButton(text="👥 Выжившие", callback_data="zs_npcs")],
        [InlineKeyboardButton(text="😴 Отдохнуть до утра", callback_data="zs_sleep")],
        [InlineKeyboardButton(text="📋 Лог событий", callback_data="zs_events"),
         InlineKeyboardButton(text="❓ Помощь", callback_data="zs_help")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def show_main(callback: CallbackQuery, player: ZSPlayer, base: ZSBase, inventory: ZSInventory):
    hunger = player.hunger or 0
    if hunger == 0:
        hunger_icon = "💀"
    elif hunger <= 3:
        hunger_icon = "⚠️"
    else:
        hunger_icon = "🍖"
    hunger_bar = "🍖" * hunger + "⬛" * (10 - hunger)
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])

    text = (
        f"🧟 Зомби Выживание\n\n"
        f"👤 {player.name} | {class_data['name']}\n"
        f"❤️ HP: {player.hp}/{player.hp_max}\n"
        f"{hunger_bar}\n"
        f"{hunger_icon} Голод: {hunger}/10\n"
        f"📅 День {player.day}\n"
    )

    try:
        await callback.message.edit_text(text, reply_markup=main_menu(player, base))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=main_menu(player, base))

@router.callback_query(F.data == "menu_zs")
async def cb_zs_menu(callback: CallbackQuery, user: User, session: AsyncSession):
    if not has_access(user):
        await callback.answer("⛔ Недостаточно прав.")
        return
    player = await get_player(session, user.telegram_id)
    if not player or not player.is_alive:
        await cb_zs_start(callback, user, session)
        return
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    await show_main(callback, player, base, inventory)

@router.callback_query(F.data == "zs_main")
async def cb_zs_main(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    if not player or not player.is_alive:
        await cb_zs_start(callback, user, session)
        return
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    await show_main(callback, player, base, inventory)

# ─── СОЗДАНИЕ ПЕРСОНАЖА ───────────────────────────────────────────────────────

async def cb_zs_start(callback: CallbackQuery, user: User, session: AsyncSession):
    text = (
        "🧟 Зомби Выживание\n\n"
        "Выбери класс персонажа:"
    )
    buttons = []
    for class_id, class_data in CLASSES.items():
        buttons.append([InlineKeyboardButton(
            text=f"{class_data['name']} — {class_data['desc']}",
            callback_data=f"zs_class_{class_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="menu_main")])
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_class_"))
async def cb_zs_class(callback: CallbackQuery, state: FSMContext):
    class_id = callback.data.replace("zs_class_", "")
    if class_id not in CLASSES:
        await callback.answer("❌ Неверный класс.")
        return
    await state.update_data(player_class=class_id)
    await state.set_state(ZSStates.entering_name)
    class_data = CLASSES[class_id]
    msg = await callback.message.edit_text(
        f"Выбран класс: {class_data['name']}\n\n"
        f"Введи имя своего персонажа:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="menu_zs")]
        ])
    )
    await state.update_data(prompt_msg_id=msg.message_id)

@router.message(ZSStates.entering_name)
async def process_name(message: Message, state: FSMContext, user: User, session: AsyncSession):
    data = await state.get_data()
    await state.clear()
    try:
        await message.delete()
    except Exception:
        pass
    if data.get("prompt_msg_id"):
        try:
            await message.bot.delete_message(message.chat.id, data["prompt_msg_id"])
        except Exception:
            pass

    name = message.text.strip()[:32]
    player_class = data.get("player_class", "soldier")

    existing = await get_player(session, user.telegram_id)
    if existing:
        await delete_player(session, user.telegram_id)

    player = await create_player(session, user.telegram_id, name, player_class)
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    class_data = CLASSES[player_class]

    text = (
        f"✅ Добро пожаловать в апокалипсис, {name}!\n\n"
        f"Класс: {class_data['name']}\n"
        f"❤️ HP: {player.hp}/{player.hp_max}\n"
        f"🍖 Голод: {player.hunger}/10\n"
        f"🥫 Стартовая еда: 5\n\n"
        f"Удачи. Она тебе понадобится."
    )
    hunger_bar = "🍖" * player.hunger + "⬛" * (10 - player.hunger)
    await message.answer(
        f"🧟 Зомби Выживание\n\n"
        f"👤 {player.name} | {class_data['name']}\n"
        f"❤️ HP: {player.hp}/{player.hp_max}\n"
        f"{hunger_bar}\n"
        f"🍖 Голод: {player.hunger}/10\n"
        f"📅 День {player.day}\n\n"
        f"✅ Персонаж создан! Удачи.",
        reply_markup=main_menu(player, base)
    )
# ─── ИНВЕНТАРЬ ────────────────────────────────────────────────────────────────

SLOT_NAMES = {
    "helmet": "🪖 Шлем",
    "armor": "👕 Броня",
    "pants": "👖 Штаны",
    "boots": "👟 Обувь",
    "melee": "⚔️ Ближний бой",
    "ranged": "🔫 Дальний бой",
    "backpack": "🎒 Рюкзак",
}

async def show_inventory(callback: CallbackQuery, player: ZSPlayer, inventory: ZSInventory):
    resources = inventory.resources or {}
    text = "🎒 Инвентарь\n\n📦 Ресурсы:\n"
    for res_id, res_data in RESOURCES.items():
        amount = resources.get(res_id, 0)
        if amount > 0:
            text += f"  {res_data['name']}: {amount}\n"
    if not any(resources.get(r, 0) > 0 for r in RESOURCES):
        text += "  Пусто\n"

    text += "\n🛡 Снаряжение:\n"
    for slot, slot_name in SLOT_NAMES.items():
        tier = getattr(inventory, f"{slot}_tier", 0)
        item_name = EQUIPMENT[slot]["tiers"][tier]["name"]
        if slot in ["melee", "ranged"]:
            stat = EQUIPMENT[slot]["tiers"][tier].get("damage", 0)
            text += f"  {slot_name}: {item_name} (урон: {stat})\n"
        elif slot == "backpack":
            stat = EQUIPMENT[slot]["tiers"][tier].get("slots", 5)
            text += f"  {slot_name}: {item_name} ({stat} слотов)\n"
        else:
            stat = EQUIPMENT[slot]["tiers"][tier].get("defense", 0)
            text += f"  {slot_name}: {item_name} (защита: {stat})\n"

    buttons = [
        [InlineKeyboardButton(text="🍖 Съесть еду", callback_data="zs_eat"),
         InlineKeyboardButton(text="💊 Использовать медикамент", callback_data="zs_use_meds")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")],
    ]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "zs_inventory")
async def cb_inventory(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    await show_inventory(callback, player, inventory)

@router.callback_query(F.data == "zs_eat")
async def cb_eat(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    if player.hunger >= 10:
        await callback.answer("🍖 Голод уже максимальный!")
        return
    result = await eat_food(session, player, inventory)
    if result:
        await callback.answer(f"🍖 Голод: {player.hunger}/10")
    else:
        await callback.answer("❌ Еды нет!")
    await show_inventory(callback, player, inventory)

@router.callback_query(F.data == "zs_use_meds")
async def cb_use_meds(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    if player.hp >= player.hp_max:
        await callback.answer("❤️ HP уже максимальное!")
        return
    result = await use_meds(session, player, inventory)
    if result:
        await callback.answer(f"💊 HP: {player.hp}/{player.hp_max}")
    else:
        await callback.answer("❌ Медикаментов нет!")
    await show_inventory(callback, player, inventory)

# ─── БАЗА ─────────────────────────────────────────────────────────────────────

async def show_base(callback: CallbackQuery, player: ZSPlayer, base: ZSBase, inventory: ZSInventory):
    text = f"🏠 База | День {player.day}\n\n"
    for building_id, building_data in BUILDINGS.items():
        level = getattr(base, building_id, 0)
        text += f"{building_data['name']}: ур.{level}/5\n"
        if level > 0:
            if building_id == "shelter":
                text += f"  +{BUILDINGS[building_id]['levels'][level]['hp_bonus']} макс HP\n"
            elif building_id == "workshop":
                text += f"  Крафт до тир {BUILDINGS[building_id]['levels'][level]['craft_tier']}\n"
            elif building_id == "garden":
                text += f"  +{BUILDINGS[building_id]['levels'][level]['food_per_day']} еды утром\n"
            elif building_id == "medpost":
                text += f"  +{BUILDINGS[building_id]['levels'][level]['heal_per_day']} HP утром\n"
            elif building_id == "watchtower":
                text += f"  Информация о локациях\n"
            elif building_id == "defense":
                text += f"  -{BUILDINGS[building_id]['levels'][level]['damage_reduction']}% урона орды\n"

    buttons = []
    for building_id, building_data in BUILDINGS.items():
        level = getattr(base, building_id, 0)
        if level < 5:
            next_level = level + 1
            cost = BUILDINGS[building_id]["levels"][next_level]["cost"]
            cost_str = ", ".join([f"{RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in cost.items()])
            buttons.append([InlineKeyboardButton(
                text=f"🔨 {building_data['name']} ур.{next_level} ({cost_str})",
                callback_data=f"zs_build_{building_id}"
            )])
    buttons.append([InlineKeyboardButton(text="🔧 Крафт снаряжения", callback_data="zs_craft")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "zs_base")
async def cb_base(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    await show_base(callback, player, base, inventory)

@router.callback_query(F.data.startswith("zs_build_"))
async def cb_build(callback: CallbackQuery, user: User, session: AsyncSession):
    building_id = callback.data.replace("zs_build_", "")
    player = await get_player(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    success, msg = await upgrade_building(session, base, inventory, building_id)
    await callback.answer(msg)
    await show_base(callback, player, base, inventory)

# ─── КРАФТ ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_craft")
async def cb_craft(callback: CallbackQuery, user: User, session: AsyncSession):
    base = await get_base(session, user.telegram_id)
    workshop_level = base.workshop or 0
    player = await get_player(session, user.telegram_id)
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])

    text = "🔧 Крафт снаряжения\n\n"
    if workshop_level == 0 and not class_data.get("can_craft_t3_without_workshop"):
        text += "Нужна мастерская для крафта!"
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="zs_base")]
        ]))
        return

    max_tier = workshop_level
    if class_data.get("can_craft_t3_without_workshop"):
        max_tier = max(max_tier, 3)

    text += f"Доступный тир крафта: до тир {max_tier}\n\n"

    buttons = []
    for slot, slot_data in EQUIPMENT.items():
        buttons.append([InlineKeyboardButton(
            text=f"{slot_data['name']}",
            callback_data=f"zs_craft_slot_{slot}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_base")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_craft_slot_"))
async def cb_craft_slot(callback: CallbackQuery, user: User, session: AsyncSession):
    slot = callback.data.replace("zs_craft_slot_", "")
    player = await get_player(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])

    workshop_level = base.workshop or 0
    max_tier = workshop_level
    if class_data.get("can_craft_t3_without_workshop"):
        max_tier = max(max_tier, 3)

    current_tier = getattr(inventory, f"{slot}_tier", 0)
    slot_data = EQUIPMENT[slot]

    text = f"{slot_data['name']}\nТекущий: {slot_data['tiers'][current_tier]['name']}\n\n"
    buttons = []
    for tier in range(1, 6):
        if tier > max_tier:
            break
        tier_data = slot_data["tiers"][tier]
        cost = tier_data.get("craft", {})
        if not cost:
            continue
        cost_str = ", ".join([f"{RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in cost.items()])
        if slot in ["melee", "ranged"]:
            stat = f"урон {tier_data.get('damage', 0)}"
        elif slot == "backpack":
            stat = f"{tier_data.get('slots', 5)} слотов"
        else:
            stat = f"защита {tier_data.get('defense', 0)}"
        buttons.append([InlineKeyboardButton(
            text=f"Тир {tier}: {tier_data['name']} ({stat}) — {cost_str}",
            callback_data=f"zs_craft_item_{slot}_{tier}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_craft")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_craft_item_"))
async def cb_craft_item(callback: CallbackQuery, user: User, session: AsyncSession):
    parts = callback.data.replace("zs_craft_item_", "").rsplit("_", 1)
    slot = parts[0]
    tier = int(parts[1])
    player = await get_player(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    success, msg = await craft_equipment(session, inventory, player, base, slot, tier)
    await callback.answer(msg)
    await cb_craft_slot(callback, user, session)
# ─── ВЫЛАЗКА ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_raid")
async def cb_raid(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)
    watchtower = base.watchtower or 0

    text = "🗺 Выбери локацию для вылазки:\n\n"
    text += "🟢 Тир 1 | 🟡 Тир 2 | 🔴 Тир 3\n\n"

    for loc_id, loc in LOCATIONS.items():
        tier_icon = {"1": "🟢", "2": "🟡", "3": "🔴"}.get(str(loc["tier"]), "⚪")
        time_h = loc["time_cost"] // 60
        text += f"{tier_icon} {loc['name']} ({time_h}ч)\n"
        if watchtower >= 1:
            res_names = ", ".join([RESOURCES[r]["name"].split()[-1] for r in loc["resources"]])
            text += f"   Ресурсы: {res_names}\n"
        if watchtower >= 2:
            text += f"   Шанс зомби: {loc['zombie_chance']}%\n"
        if watchtower >= 3:
            text += f"   Зомби: {loc['zombie_hp'][0]}-{loc['zombie_hp'][1]} HP, урон {loc['zombie_damage'][0]}-{loc['zombie_damage'][1]}\n"
        text += "\n"

    buttons = []
    for loc_id, loc in LOCATIONS.items():
        tier_icon = {"1": "🟢", "2": "🟡", "3": "🔴"}.get(str(loc["tier"]), "⚪")
        buttons.append([InlineKeyboardButton(
            text=f"{tier_icon} {loc['name']} ({loc['time_cost'] // 60}ч)",
            callback_data=f"zs_raid_{loc_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_raid_"))
async def cb_raid_location(callback: CallbackQuery, user: User, session: AsyncSession):
    loc_id = callback.data.replace("zs_raid_", "")
    if loc_id not in LOCATIONS:
        await callback.answer("❌ Локация не найдена.")
        return

    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)

    if player.hunger == 0:
        await callback.answer("⚠️ Голод на нуле! Съешь еду перед вылазкой.")

    result = await start_raid(session, player, inventory, loc_id)
    scenario = result["scenario"]

    if not scenario:
        await callback.answer("❌ Сценарий не найден.")
        return

    text = f"🗺 {LOCATIONS[loc_id]['name']}\n\n{scenario['intro']}\n\nЧто делаешь?"
    buttons = []
    for opt in scenario["options"]:
        buttons.append([InlineKeyboardButton(
            text=opt["button"],
            callback_data=f"zs_option_{loc_id}_{opt['type']}"
        )])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_option_"))
async def cb_raid_option(callback: CallbackQuery, user: User, session: AsyncSession):
    parts = callback.data.replace("zs_option_", "").split("_", 1)
    loc_id = parts[0]
    option_type = parts[1]

    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)

    # Получаем сценарий заново чтобы найти нужный вариант
    scenario = await get_random_scenario(session, loc_id)
    option = next((o for o in scenario["options"] if o["type"] == option_type), None)
    if not option:
        await callback.answer("❌ Вариант не найден.")
        return

    result = await process_raid_option(session, player, inventory, base, loc_id, option)

    if result["type"] == "fight":
        # Показываем бой
        zombie_hp = result["zombie_hp"]
        zombie_hp_max = result["zombie_hp_max"]
        zombie_damage = result["zombie_damage"]
        is_combat_loot = result.get("is_combat_loot", False)
        filled = zombie_hp * 10 // zombie_hp_max
        hp_bar = "🟥" * filled + "⬛" * (10 - filled)
        player_defense = await get_player_defense(inventory)
        melee_damage = await get_player_melee_damage(inventory, player)
        ranged_damage = await get_player_ranged_damage(inventory, player)

        text = (
            f"🧟 Зомби {hp_bar} {zombie_hp}/{zombie_hp_max}\n"
            f"❤️ Ты: {player.hp}/{player.hp_max}\n\n"
            f"{result['text']}\n\n"
            f"⚔️ Твой урон: {melee_damage} | 🔫 {ranged_damage}\n"
            f"🛡 Защита: {player_defense}"
        )
        combat_data = f"{loc_id}_{zombie_hp}_{zombie_hp_max}_{zombie_damage}_{1 if is_combat_loot else 0}"
        buttons = [
            [InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"zs_fight_melee_{combat_data}")],
            [InlineKeyboardButton(text="🔫 Стрелять", callback_data=f"zs_fight_ranged_{combat_data}")],
            [InlineKeyboardButton(text="🏃 Убежать", callback_data=f"zs_fight_flee_{combat_data}")],
        ]
        try:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception:
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    if result["type"] == "leave":
        text = f"{result['text']}\n\n+1 голод восстановлен."
        hunger = player.hunger
        hunger_bar = "🍖" * hunger + "⬛" * (10 - hunger)
        text += f"\n{hunger_bar} Голод: {hunger}/10"
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ На базу", callback_data="zs_main")]
            ])
        )
        return

    if result["type"] == "npc":
        text = f"{result['text']}\n\n"
        if result.get("npc"):
            text += f"👤 {result['npc'].name} присоединился к твоей базе!\n"
        elif not result.get("has_space"):
            text += "На базе нет места для новых выживших.\n"
        if result.get("resources"):
            res_list = ", ".join([f"{RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in result["resources"].items()])
            text += f"📦 Получено: {res_list}"
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ На базу", callback_data="zs_main")]
            ])
        )
        return

    if result["type"] == "empty":
        text = f"{result['text']}\n\nНичего не нашёл."
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ На базу", callback_data="zs_main")]
            ])
        )
        return

    if result["type"] == "loot":
        text = f"{result['text']}\n\n"
        if result.get("resources"):
            res_list = ", ".join([f"{RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in result["resources"].items()])
            text += f"📦 Найдено: {res_list}"
        else:
            text += "Ничего не нашёл."
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ На базу", callback_data="zs_main")]
            ])
        )
        return

# ─── БОЙ ──────────────────────────────────────────────────────────────────────

async def process_fight(callback: CallbackQuery, user: User, session: AsyncSession, action: str, combat_data: str):
    parts = combat_data.split("_")
    loc_id = parts[0]
    zombie_hp = int(parts[1])
    zombie_hp_max = int(parts[2])
    zombie_damage = int(parts[3])
    is_combat_loot = parts[4] == "1"

    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    player_defense = await get_player_defense(inventory)
    melee_damage = await get_player_melee_damage(inventory, player)
    ranged_damage = await get_player_ranged_damage(inventory, player)

    result_text = ""

    if action == "flee":
        # Шанс получить урон при побеге
        if _r.randint(1, 100) <= 50:
            dmg = max(1, zombie_damage - player_defense)
            player.hp = max(0, player.hp - dmg)
            await session.commit()
            result_text = f"🏃 Убегаешь! Зомби достал тебя — -{dmg} HP."
        else:
            result_text = "🏃 Успешно убежал!"

        if player.hp <= 0:
            await delete_player(session, user.telegram_id)
            await callback.message.edit_text(
                "💀 Ты погиб при побеге!\n\nИгра окончена.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Начать заново", callback_data="menu_zs")]
                ])
            )
            return

        hunger = player.hunger
        hunger_bar = "🍖" * hunger + "⬛" * (10 - hunger)
        await callback.message.edit_text(
            f"{result_text}\n\n❤️ HP: {player.hp}/{player.hp_max}\n{hunger_bar} Голод: {hunger}/10",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ На базу", callback_data="zs_main")]
            ])
        )
        return

    if action == "melee":
        damage = melee_damage
        result_text = f"⚔️ Удар! -{damage} HP зомби."
    elif action == "ranged":
        ranged_tier = inventory.ranged_tier or 0
        if ranged_tier == 0:
            await callback.answer("❌ Нет дальнего оружия!")
            return
        ammo_cost = EQUIPMENT["ranged"]["tiers"][ranged_tier].get("ammo_cost", 0)
        if ammo_cost > 0:
            resources = dict(inventory.resources or {})
            if resources.get("ammo", 0) < ammo_cost:
                await callback.answer("❌ Нет боеприпасов!")
                return
            resources["ammo"] = resources["ammo"] - ammo_cost
            inventory.resources = resources
        damage = ranged_damage
        result_text = f"🔫 Выстрел! -{damage} HP зомби."

    zombie_hp -= damage
    result_text += f"\nЗомби: {max(0, zombie_hp)}/{zombie_hp_max} HP"

    if zombie_hp <= 0:
        # Победа
        resources = await process_combat_victory(session, player, inventory, loc_id, is_combat_loot)
        res_text = ""
        if resources:
            res_list = ", ".join([f"{RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in resources.items()])
            res_text = f"\n📦 Лут: {res_list}"
        hunger = player.hunger
        hunger_bar = "🍖" * hunger + "⬛" * (10 - hunger)
        await callback.message.edit_text(
            f"✅ Зомби повержен!{res_text}\n\n❤️ HP: {player.hp}/{player.hp_max}\n{hunger_bar} Голод: {hunger}/10",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ На базу", callback_data="zs_main")]
            ])
        )
        return

    # Зомби атакует
    dmg = max(1, zombie_damage - player_defense)
    player.hp = max(0, player.hp - dmg)
    await session.commit()
    result_text += f"\n🧟 Зомби атакует! -{dmg} HP"

    if player.hp <= 0:
        await delete_player(session, user.telegram_id)
        await callback.message.edit_text(
            "💀 Ты погиб в бою!\n\nИгра окончена.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Начать заново", callback_data="menu_zs")]
            ])
        )
        return

    # Продолжаем бой
    filled = zombie_hp * 10 // zombie_hp_max
    hp_bar = "🟥" * filled + "⬛" * (10 - filled)
    text = (
        f"🧟 Зомби {hp_bar} {zombie_hp}/{zombie_hp_max}\n"
        f"❤️ Ты: {player.hp}/{player.hp_max}\n\n"
        f"{result_text}"
    )
    combat_data_new = f"{loc_id}_{zombie_hp}_{zombie_hp_max}_{zombie_damage}_{1 if is_combat_loot else 0}"
    buttons = [
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"zs_fight_melee_{combat_data_new}")],
        [InlineKeyboardButton(text="🔫 Стрелять", callback_data=f"zs_fight_ranged_{combat_data_new}")],
        [InlineKeyboardButton(text="🏃 Убежать", callback_data=f"zs_fight_flee_{combat_data_new}")],
    ]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_fight_melee_"))
async def cb_fight_melee(callback: CallbackQuery, user: User, session: AsyncSession):
    await process_fight(callback, user, session, "melee", callback.data.replace("zs_fight_melee_", ""))

@router.callback_query(F.data.startswith("zs_fight_ranged_"))
async def cb_fight_ranged(callback: CallbackQuery, user: User, session: AsyncSession):
    await process_fight(callback, user, session, "ranged", callback.data.replace("zs_fight_ranged_", ""))

@router.callback_query(F.data.startswith("zs_fight_flee_"))
async def cb_fight_flee(callback: CallbackQuery, user: User, session: AsyncSession):
    await process_fight(callback, user, session, "flee", callback.data.replace("zs_fight_flee_", ""))
# ─── ВЫЖИВШИЕ ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_npcs")
async def cb_npcs(callback: CallbackQuery, user: User, session: AsyncSession):
    base = await get_base(session, user.telegram_id)
    npcs = await get_npcs(session, user.telegram_id)
    max_npcs = await get_max_npcs(base)

    if not npcs:
        text = f"👥 Выжившие (0/{max_npcs})\n\nНикого нет. Ищи выживших на вылазках (вариант В)."
        buttons = [[InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")]]
    else:
        text = f"👥 Выжившие ({len(npcs)}/{max_npcs})\n\n"
        buttons = []
        for npc in npcs:
            level_data = get_npc_level_data(npc.level)
            exp_needed = get_npc_exp_needed(npc.level)
            loc_name = LOCATIONS.get(npc.location, {}).get("name", npc.location) if npc.location else ""
            status_text = "🏠 На базе" if npc.status == "idle" else f"🗺 На задании ({loc_name})"
            weapon = EQUIPMENT["melee"]["tiers"][npc.weapon_tier or 0]["name"]
            armor = EQUIPMENT["armor"]["tiers"][npc.armor_tier or 0]["name"]
            hunger_bar = "🍖" * (npc.hunger or 0) + "⬛" * (10 - (npc.hunger or 0))
            text += (
                f"👤 {npc.name}\n"
                f"   ⭐ Ур.{npc.level} {level_data['name']} | Опыт: {npc.exp}/{exp_needed}\n"
                f"   ❤️ HP: {npc.hp}/{npc.hp_max} | {hunger_bar}\n"
                f"   ⚔️ {weapon} | 🛡 {armor}\n"
                f"   📊 Заданий выполнено: {npc.missions_survived}/{npc.missions_total}\n"
                f"   Статус: {status_text}\n\n"
            )
            if npc.status == "idle":
                buttons.append([
                    InlineKeyboardButton(text=f"📤 Отправить {npc.name}", callback_data=f"zs_send_npc_{npc.id}"),
                    InlineKeyboardButton(text=f"🍖 Покормить", callback_data=f"zs_feed_npc_{npc.id}"),
                ])
                buttons.append([InlineKeyboardButton(
                    text=f"🔧 Снаряжение {npc.name}",
                    callback_data=f"zs_npc_equip_{npc.id}"
                )])
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_feed_npc_"))
async def cb_feed_npc(callback: CallbackQuery, user: User, session: AsyncSession):
    npc_id = int(callback.data.replace("zs_feed_npc_", ""))
    from sqlalchemy import select as sa_select
    from models.zombie_survival import ZSNPC as ZSNPCModel
    result = await session.execute(sa_select(ZSNPCModel).where(ZSNPCModel.id == npc_id))
    npc = result.scalar_one_or_none()
    if not npc:
        await callback.answer("❌ НПС не найден.")
        return
    inventory = await get_inventory(session, user.telegram_id)
    success = await feed_npc(session, npc, inventory)
    if success:
        await callback.answer(f"🍖 {npc.name} накормлен! Голод: {npc.hunger}/10")
    else:
        await callback.answer("❌ Еды нет!")
    await cb_npcs(callback, user, session)

@router.callback_query(F.data.startswith("zs_send_npc_"))
async def cb_send_npc(callback: CallbackQuery, user: User, session: AsyncSession):
    npc_id = int(callback.data.replace("zs_send_npc_", ""))
    from sqlalchemy import select as sa_select
    from models.zombie_survival import ZSNPC as ZSNPCModel
    result = await session.execute(sa_select(ZSNPCModel).where(ZSNPCModel.id == npc_id))
    npc = result.scalar_one_or_none()
    if not npc:
        await callback.answer("❌ НПС не найден.")
        return

    text = f"📤 Отправить {npc.name} на задание\n\nВыбери локацию:"
    buttons = []
    for loc_id, loc in LOCATIONS.items():
        tier_icon = {"1": "🟢", "2": "🟡", "3": "🔴"}.get(str(loc["tier"]), "⚪")
        buttons.append([InlineKeyboardButton(
            text=f"{tier_icon} {loc['name']}",
            callback_data=f"zs_npc_mission_{npc_id}_{loc_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_npcs")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_npc_mission_"))
async def cb_npc_mission(callback: CallbackQuery, user: User, session: AsyncSession):
    parts = callback.data.replace("zs_npc_mission_", "").split("_", 1)
    npc_id = int(parts[0])
    loc_id = parts[1]
    from sqlalchemy import select as sa_select
    from models.zombie_survival import ZSNPC as ZSNPCModel
    result = await session.execute(sa_select(ZSNPCModel).where(ZSNPCModel.id == npc_id))
    npc = result.scalar_one_or_none()
    if not npc:
        await callback.answer("❌ НПС не найден.")
        return
    await send_npc_on_mission(session, npc, loc_id)
    loc_name = LOCATIONS[loc_id]["name"]
    await callback.answer(f"📤 {npc.name} отправлен в {loc_name}")
    await cb_npcs(callback, user, session)

@router.callback_query(F.data.startswith("zs_npc_equip_"))
async def cb_npc_equip(callback: CallbackQuery, user: User, session: AsyncSession):
    npc_id = int(callback.data.replace("zs_npc_equip_", ""))
    from sqlalchemy import select as sa_select
    from models.zombie_survival import ZSNPC as ZSNPCModel
    result = await session.execute(sa_select(ZSNPCModel).where(ZSNPCModel.id == npc_id))
    npc = result.scalar_one_or_none()
    if not npc:
        await callback.answer("❌ НПС не найден.")
        return

    base = await get_base(session, user.telegram_id)
    workshop_level = base.workshop or 0
    inventory = await get_inventory(session, user.telegram_id)

    weapon = EQUIPMENT["melee"]["tiers"][npc.weapon_tier or 0]["name"]
    armor = EQUIPMENT["armor"]["tiers"][npc.armor_tier or 0]["name"]
    text = f"🔧 Снаряжение {npc.name}\n\n⚔️ Оружие: {weapon}\n🛡 Броня: {armor}\n\nВыбери что улучшить:"

    buttons = []
    for tier in range(1, min(workshop_level + 1, 6)):
        tier_data = EQUIPMENT["melee"]["tiers"][tier]
        cost = tier_data.get("craft", {})
        cost_str = ", ".join([f"{RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in cost.items()])
        buttons.append([InlineKeyboardButton(
            text=f"⚔️ {tier_data['name']} ({cost_str})",
            callback_data=f"zs_npc_weapon_{npc_id}_{tier}"
        )])
    for tier in range(1, min(workshop_level + 1, 6)):
        tier_data = EQUIPMENT["armor"]["tiers"][tier]
        cost = tier_data.get("craft", {})
        cost_str = ", ".join([f"{RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in cost.items()])
        buttons.append([InlineKeyboardButton(
            text=f"🛡 {tier_data['name']} ({cost_str})",
            callback_data=f"zs_npc_armor_{npc_id}_{tier}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_npcs")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_npc_weapon_"))
async def cb_npc_weapon(callback: CallbackQuery, user: User, session: AsyncSession):
    parts = callback.data.replace("zs_npc_weapon_", "").split("_")
    npc_id = int(parts[0])
    tier = int(parts[1])
    from sqlalchemy import select as sa_select
    from models.zombie_survival import ZSNPC as ZSNPCModel
    result = await session.execute(sa_select(ZSNPCModel).where(ZSNPCModel.id == npc_id))
    npc = result.scalar_one_or_none()
    inventory = await get_inventory(session, user.telegram_id)
    cost = EQUIPMENT["melee"]["tiers"][tier].get("craft", {})
    resources = dict(inventory.resources or {})
    for res, amount in cost.items():
        if resources.get(res, 0) < amount:
            await callback.answer(f"❌ Недостаточно {RESOURCES[res]['name']}")
            return
    for res, amount in cost.items():
        resources[res] = resources.get(res, 0) - amount
    inventory.resources = resources
    npc.weapon_tier = tier
    await session.commit()
    await callback.answer(f"✅ Выдано: {EQUIPMENT['melee']['tiers'][tier]['name']}")
    await cb_npc_equip(callback, user, session)

@router.callback_query(F.data.startswith("zs_npc_armor_"))
async def cb_npc_armor(callback: CallbackQuery, user: User, session: AsyncSession):
    parts = callback.data.replace("zs_npc_armor_", "").split("_")
    npc_id = int(parts[0])
    tier = int(parts[1])
    from sqlalchemy import select as sa_select
    from models.zombie_survival import ZSNPC as ZSNPCModel
    result = await session.execute(sa_select(ZSNPCModel).where(ZSNPCModel.id == npc_id))
    npc = result.scalar_one_or_none()
    inventory = await get_inventory(session, user.telegram_id)
    cost = EQUIPMENT["armor"]["tiers"][tier].get("craft", {})
    resources = dict(inventory.resources or {})
    for res, amount in cost.items():
        if resources.get(res, 0) < amount:
            await callback.answer(f"❌ Недостаточно {RESOURCES[res]['name']}")
            return
    for res, amount in cost.items():
        resources[res] = resources.get(res, 0) - amount
    inventory.resources = resources
    npc.armor_tier = tier
    await session.commit()
    await callback.answer(f"✅ Выдана: {EQUIPMENT['armor']['tiers'][tier]['name']}")
    await cb_npc_equip(callback, user, session)

# ─── НОЧЬ ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_sleep")
async def cb_sleep(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext):
    player = await get_player(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)

    night_result = await process_night(session, player, base, inventory)
    npc_results = await return_npcs(session, player)

    if night_result.get("attacked"):
        await state.set_state(ZSStates.night_attack)
        horde_stats = get_horde_stats(player.day - 1)
        zombie_hp = night_result["zombie_hp"]
        zombie_hp_max = night_result["zombie_hp_max"]
        zombie_damage = night_result["zombie_damage"]
        defense_level = base.defense or 0
        defense_reduction = 0
        if defense_level > 0:
            from services.zs_data import BUILDINGS as B
            defense_reduction = B["defense"]["levels"][defense_level]["damage_reduction"]

        filled = zombie_hp * 10 // zombie_hp_max
        hp_bar = "🟥" * filled + "⬛" * (10 - filled)

        npc_text = ""
        if npc_results["returned"]:
            npc_text += "\n\n👥 Выжившие вернулись с заданий:\n"
            for r in npc_results["returned"]:
                if r["resources"]:
                    res_list = ", ".join([f"{RESOURCES[res]['name'].split()[-1]} x{amt}" for res, amt in r["resources"].items()])
                    npc_text += f"  ✅ {r['name']}: {res_list}\n"
                else:
                    npc_text += f"  ✅ {r['name']}: ничего не нашёл\n"
                if r.get("leveled_up"):
                    level_data = get_npc_level_data(r["level"])
                    npc_text += f"  🎉 {r['name']} — ур.{r['level']} {level_data['name']}!\n"
        if npc_results["died"]:
            npc_text += "\n💀 Погибли на задании:\n"
            for name in npc_results["died"]:
                npc_text += f"  ❌ {name}\n"

        text = (
            f"🧟 Ночное нападение!\n\n"
            f"Орда {hp_bar} {zombie_hp}/{zombie_hp_max}\n"
            f"❤️ Ты: {player.hp}/{player.hp_max}\n"
            f"🛡 Защита базы: -{defense_reduction}%"
            f"{npc_text}"
        )
        combat_data = f"{zombie_hp}_{zombie_hp_max}_{zombie_damage}_{defense_reduction}"
        buttons = [
            [InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"zs_night_fight_melee_{combat_data}")],
            [InlineKeyboardButton(text="🔫 Стрелять", callback_data=f"zs_night_fight_ranged_{combat_data}")],
        ]
        try:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    # Тихая ночь
    hunger = player.hunger
    hunger_bar = "🍖" * hunger + "⬛" * (10 - hunger)
    tip = _r.choice(TIPS)

    npc_text = ""
    if npc_results["returned"]:
        npc_text += "\n\n👥 Выжившие вернулись:\n"
        for r in npc_results["returned"]:
            if r["resources"]:
                res_list = ", ".join([f"{RESOURCES[res]['name'].split()[-1]} x{amt}" for res, amt in r["resources"].items()])
                npc_text += f"  ✅ {r['name']}: {res_list}\n"
            else:
                npc_text += f"  ✅ {r['name']}: ничего не нашёл\n"
            if r.get("leveled_up"):
                level_data = get_npc_level_data(r["level"])
                npc_text += f"  🎉 {r['name']} — ур.{r['level']} {level_data['name']}!\n"
    if npc_results["died"]:
        npc_text += "\n💀 Погибли на задании:\n"
        for name in npc_results["died"]:
            npc_text += f"  ❌ {name}\n"

    morning_text = ""
    if night_result.get("medpost_heal", 0) > 0:
        morning_text += f"\n☀️ Медпункт: +{night_result['medpost_heal']} HP"
    if night_result.get("garden_food", 0) > 0:
        morning_text += f"\n🌱 Огород: +{night_result['garden_food']} еды"

    text = (
        f"😴 Ты отдохнул до утра.\n"
        f"{morning_text}\n\n"
        f"❤️ HP: {player.hp}/{player.hp_max}\n"
        f"{hunger_bar}\n"
        f"🍖 Голод: {hunger}/10\n"
        f"📅 День {player.day}"
        f"{npc_text}\n\n"
        f"✅ Ночь прошла спокойно.\n\n"
        f"💡 {tip}"
    )

    try:
        await callback.message.edit_text(text, reply_markup=main_menu(player, base))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=main_menu(player, base))

@router.callback_query(F.data.startswith("zs_night_fight_"))
async def cb_night_fight(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext):
    parts = callback.data.replace("zs_night_fight_", "").split("_", 1)
    action = parts[0]
    combat_data = parts[1]
    data_parts = combat_data.split("_")
    zombie_hp = int(data_parts[0])
    zombie_hp_max = int(data_parts[1])
    zombie_damage = int(data_parts[2])
    defense_reduction = int(data_parts[3])

    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)
    player_defense = await get_player_defense(inventory)
    melee_damage = await get_player_melee_damage(inventory, player)
    ranged_damage = await get_player_ranged_damage(inventory, player)

    # НПС помогают
    npcs = await get_npcs(session, user.telegram_id)
    npc_damage = sum(EQUIPMENT["melee"]["tiers"][npc.weapon_tier or 0]["damage"] for npc in npcs if npc.status == "idle")

    result_text = ""
    if action == "melee":
        damage = melee_damage + npc_damage
        result_text = f"⚔️ Атака! -{damage} HP орды."
        if npc_damage > 0:
            result_text += f" (в т.ч. {npc_damage} от выживших)"
    elif action == "ranged":
        ranged_tier = inventory.ranged_tier or 0
        if ranged_tier == 0:
            await callback.answer("❌ Нет дальнего оружия!")
            return
        ammo_cost = EQUIPMENT["ranged"]["tiers"][ranged_tier].get("ammo_cost", 0)
        if ammo_cost > 0:
            resources = dict(inventory.resources or {})
            if resources.get("ammo", 0) < ammo_cost:
                await callback.answer("❌ Нет боеприпасов!")
                return
            resources["ammo"] = resources["ammo"] - ammo_cost
            inventory.resources = resources
        damage = ranged_damage + npc_damage
        result_text = f"🔫 Выстрел! -{damage} HP орды."

    zombie_hp -= damage

    if zombie_hp <= 0:
        # Победа
        await state.clear()
        npc_results = await return_npcs(session, player)
        heal_amount = 0
        medpost_level = base.medpost or 0
        if medpost_level > 0:
            heal_amount = BUILDINGS["medpost"]["levels"][medpost_level]["heal_per_day"]
        old_hp = player.hp
        player.hp = min(player.hp_max, player.hp + heal_amount)
        await session.commit()

        hunger = player.hunger
        hunger_bar = "🍖" * hunger + "⬛" * (10 - hunger)
        tip = _r.choice(TIPS)

        npc_text = ""
        if npc_results["returned"]:
            npc_text += "\n\n👥 Выжившие вернулись:\n"
            for r in npc_results["returned"]:
                if r["resources"]:
                    res_list = ", ".join([f"{RESOURCES[res]['name'].split()[-1]} x{amt}" for res, amt in r["resources"].items()])
                    npc_text += f"  ✅ {r['name']}: {res_list}\n"
                else:
                    npc_text += f"  ✅ {r['name']}: ничего не нашёл\n"
                if r.get("leveled_up"):
                    level_data = get_npc_level_data(r["level"])
                    npc_text += f"  🎉 {r['name']} — ур.{r['level']} {level_data['name']}!\n"
        if npc_results["died"]:
            npc_text += "\n💀 Погибли на задании:\n"
            for name in npc_results["died"]:
                npc_text += f"  ❌ {name}\n"

        morning = f"\n☀️ Медпункт: +{player.hp - old_hp} HP" if heal_amount > 0 else ""

        text = (
            f"🌙 Нападение отбито!\n\n"
            f"{result_text}\n\n"
            f"❤️ HP: {player.hp}/{player.hp_max}\n"
            f"{hunger_bar}\n"
            f"🍖 Голод: {hunger}/10\n"
            f"📅 День {player.day}"
            f"{morning}"
            f"{npc_text}\n\n"
            f"💡 {tip}"
        )
        try:
            await callback.message.edit_text(text, reply_markup=main_menu(player, base))
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, reply_markup=main_menu(player, base))
        return

    # Орда атакует
    effective_damage = max(1, int(zombie_damage * (1 - defense_reduction / 100)) - player_defense)
    player.hp = max(0, player.hp - effective_damage)
    await session.commit()
    result_text += f"\n🧟 Орда атакует! -{effective_damage} HP"

    if player.hp <= 0:
        await state.clear()
        await delete_player(session, user.telegram_id)
        await callback.message.edit_text(
            "💀 База пала. Ты погиб!\n\nИгра окончена.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Начать заново", callback_data="menu_zs")]
            ])
        )
        return

    filled = max(0, zombie_hp) * 10 // zombie_hp_max
    hp_bar = "🟥" * filled + "⬛" * (10 - filled)
    text = (
        f"🧟 Орда {hp_bar} {zombie_hp}/{zombie_hp_max}\n"
        f"❤️ Ты: {player.hp}/{player.hp_max}\n\n"
        f"{result_text}"
    )
    combat_data_new = f"{zombie_hp}_{zombie_hp_max}_{zombie_damage}_{defense_reduction}"
    buttons = [
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data=f"zs_night_fight_melee_{combat_data_new}")],
        [InlineKeyboardButton(text="🔫 Стрелять", callback_data=f"zs_night_fight_ranged_{combat_data_new}")],
    ]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ─── ЛОГ СОБЫТИЙ ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_events")
async def cb_events(callback: CallbackQuery, user: User, session: AsyncSession):
    events = await get_events(session, user.telegram_id)
    if not events:
        text = "📋 Лог событий пуст."
    else:
        text = "📋 Лог событий:\n\n"
        for event in reversed(events):
            text += f"День {event.day}: {event.event_text}\n"
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")]
        ]))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")]
        ]))

# ─── ПОМОЩЬ ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_help")
async def cb_help(callback: CallbackQuery, user: User):
    text = (
        "❓ Помощь\n\n"
        "🎯 Цель: выживи как можно дольше.\n\n"
        "🗺 Вылазки:\n"
        "— Тир 1 (2ч) — безопасно, базовые ресурсы\n"
        "— Тир 2 (4ч) — опасно, средние ресурсы\n"
        "— Тир 3 (6ч) — очень опасно, редкие ресурсы\n"
        "— Вариант А: поиск лута (риск встретить зомби)\n"
        "— Вариант Б: гарантированный бой, больше лута\n"
        "— Вариант В: найти выжившего\n"
        "— Вариант Г: уйти (+1 голод)\n\n"
        "🏠 База:\n"
        "— Убежище: +HP и места для выживших\n"
        "— Мастерская: крафт снаряжения\n"
        "— Огород: еда каждое утро\n"
        "— Медпункт: лечение утром\n"
        "— Вышка: информация о локациях\n"
        "— Защита: снижает урон от орды\n\n"
        "👥 Выжившие:\n"
        "— Ур.1 Новичок: лут x1.0\n"
        "— Ур.2 Выживший: лут x1.1\n"
        "— Ур.3 Опытный: лут x1.2\n"
        "— Ур.4 Ветеран: лут x1.35\n"
        "— Ур.5 Легенда: лут x1.5\n"
        "— Опыт: +1 за задание, +1 за ночную оборону\n\n"
        "🌙 Ночь:\n"
        "— 30% шанс нападения орды\n"
        "— Сила орды растёт каждые 5 дней\n"
        "— Защита базы снижает урон\n\n"
        "💊 Лечение:\n"
        "— Еда: +2 голода\n"
        "— Медикаменты: +20 HP (медик +30)\n"
        "— Медпункт: лечит каждое утро"
    )
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")]
        ]))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")]
        ]))
