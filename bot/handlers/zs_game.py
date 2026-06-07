from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models.user import User
from models.zombie_survival import ZSPlayer, ZSBase, ZSInventory
from services.zs_service import (
    get_player, get_base, get_inventory, create_player, reset_player,
    advance_time, add_resources, remove_resources, build, upgrade_base,
    upgrade_equipment, get_npcs, add_npc, send_npc_on_mission, night_attack,
    get_image, set_image, return_npcs, reduce_hunger, eat_food,
    add_event, get_events
)
from services.zs_data import NPC_LEVELS, get_npc_level_data, get_npc_exp_needed
from services.zs_data import (
    RESOURCES, LOCATIONS, BUILDINGS, DEFENSE_LEVELS, BASE_LEVELS,
    EQUIPMENT_CHAINS, STARTER_EQUIPMENT, NPC_NAMES, RADIO_MESSAGES,
    IMAGE_KEYS, is_daytime, format_time, get_total_defense,
    get_backpack_slots, get_equipment_item, get_workshop_tier, get_max_npcs
)
from sqlalchemy.ext.asyncio import AsyncSession

router = Router()

class ZSStates(StatesGroup):
    entering_name = State()
    night_attack = State()

def has_access(user: User) -> bool:
    return user.role in ["owner", "admin", "user"]

def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])

def dead_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Начать заново", callback_data="zs_restart")]
    ])

def fight_buttons(loc_id: str, zombie_hp: int, zombie_hp_max: int, zombie_index: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Ближний бой", callback_data=f"zs_fight_melee_{loc_id}_{zombie_hp}_{zombie_hp_max}_{zombie_index}")],
        [InlineKeyboardButton(text="🔫 Стрелять",    callback_data=f"zs_fight_ranged_{loc_id}_{zombie_hp}_{zombie_hp_max}_{zombie_index}")],
        [InlineKeyboardButton(text="🏃 Убежать",     callback_data=f"zs_fight_run_{loc_id}_{zombie_hp}_{zombie_hp_max}_{zombie_index}")],
    ])

def main_menu(player: ZSPlayer, base: ZSBase) -> InlineKeyboardMarkup:
    time_str = format_time(player.game_time)
    is_day = is_daytime(player.game_time)
    time_icon = "☀️" if is_day else "🌙"
    buttons = [
        [InlineKeyboardButton(text=f"{time_icon} День {player.day} | {time_str}", callback_data="zs_time_info")],
    ]
    if is_day:
        buttons.append([InlineKeyboardButton(text="🗺 Вылазка", callback_data="zs_raid")])
    else:
        buttons.append([InlineKeyboardButton(text="🌙 Ночь — отдохнуть", callback_data="zs_night")])
    buttons += [
        [InlineKeyboardButton(text="🏠 База", callback_data="zs_base")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="zs_inventory")],
        [InlineKeyboardButton(text="👥 Выжившие", callback_data="zs_npcs")],
        [InlineKeyboardButton(text="📻 Радио", callback_data="zs_radio")],
        [InlineKeyboardButton(text="📋 Лог событий", callback_data="zs_log")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="zs_help")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def format_status(player: ZSPlayer) -> str:
    hp_bar_filled = int(player.hp / player.hp_max * 10)
    hp_bar = "❤️" * hp_bar_filled + "🖤" * (10 - hp_bar_filled)
    hunger = getattr(player, "hunger", 10)
    hunger_bar = "🍖" * hunger + "⬛" * (10 - hunger)
    if hunger == 0:
        hunger_icon = "💀"
    elif hunger <= 3:
        hunger_icon = "⚠️"
    else:
        hunger_icon = "🍖"
    return (
        f"👤 {player.name}\n"
        f"{hp_bar}\n"
        f"❤️ HP: {player.hp}/{player.hp_max}\n"
        f"{hunger_bar}\n"
        f"{hunger_icon} Голод: {hunger}/10\n"
        f"📅 День {player.day}\n"
        f"⏰ {format_time(player.game_time)}"
    )

# ─── СОЗДАНИЕ ПЕРСОНАЖА ──────────────────────────────────────────────────────

@router.message(Command("zs"))
async def cmd_zs(message: Message, user: User, session: AsyncSession, state: FSMContext):
    if not has_access(user):
        await message.answer("⛔ Недостаточно прав.")
        return
    player = await get_player(session, user.telegram_id)
    if not player:
        await message.answer(
            "🧟 Добро пожаловать в зону заражения!\n\n"
            "Учёные из Великой Крокожии работают над вакциной.\n"
            "Твоя задача — выжить как можно дольше.\n\n"
            "Введи имя своего персонажа:"
        )
        await state.set_state(ZSStates.entering_name)
        return
    if not player.is_alive:
        await message.answer(
            "💀 Твой персонаж погиб.\n\nХочешь начать заново?",
            reply_markup=dead_menu()
        )
        return
    base = await get_base(session, user.telegram_id)
    image = await get_image(session, f"base_{base.level}")
    text = format_status(player)
    if image:
        await message.answer_photo(image.file_id, caption=text, reply_markup=main_menu(player, base))
    else:
        await message.answer(text, reply_markup=main_menu(player, base))

@router.message(ZSStates.entering_name)
async def process_name(message: Message, state: FSMContext, user: User, session: AsyncSession):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 32:
        await message.answer("❌ Имя должно быть от 2 до 32 символов.")
        return
    await state.clear()
    player = await create_player(session, user.telegram_id, name)
    base = await get_base(session, user.telegram_id)
    await message.answer(
        f"✅ Персонаж создан!\n\n{format_status(player)}\n\n"
        f"📻 {RADIO_MESSAGES[1]}",
        reply_markup=main_menu(player, base)
    )

# ─── ГЛАВНОЕ МЕНЮ ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_main")
async def cb_zs_main(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    if not player or not player.is_alive:
        await callback.answer("❌ Персонаж не найден.")
        return
    base = await get_base(session, user.telegram_id)
    text = format_status(player)
    image = await get_image(session, f"base_{base.level}")
    if image:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(image.file_id, caption=text, reply_markup=main_menu(player, base))
    else:
        try:
            await callback.message.edit_text(text, reply_markup=main_menu(player, base))
        except Exception:
            await callback.message.answer(text, reply_markup=main_menu(player, base))

@router.callback_query(F.data == "zs_time_info")
async def cb_time_info(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    is_day = is_daytime(player.game_time)
    phase = "☀️ День" if is_day else "🌙 Ночь"
    await callback.answer(f"{phase} | {format_time(player.game_time)} | День {player.day}")

# ─── НОЧЬ ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_night")
async def cb_night(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    resources = inventory.resources or {}
    food = resources.get("food", 0)
    buttons = [
        [InlineKeyboardButton(text="😴 Отдохнуть до утра", callback_data="zs_sleep")],
        [InlineKeyboardButton(text="🏠 База", callback_data="zs_base")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="zs_inventory")],
    ]
    hunger = getattr(player, "hunger", 10)
    if food > 0 and hunger < 10:
        buttons.append([InlineKeyboardButton(text=f"🍖 Поесть (+2 голода) | Еда: {food}", callback_data="zs_eat")])
    try:
        await callback.message.edit_text(
            f"🌙 Ночь — вылазки недоступны.\n\n"
            f"❤️ HP: {player.hp}/{player.hp_max}\n"
            f"🥫 Еда: {food}\n"
            f"⏰ {format_time(player.game_time)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"🌙 Ночь — вылазки недоступны.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data == "zs_eat")
async def cb_eat(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    success = await eat_food(session, player, inventory)
    if not success:
        await callback.answer("❌ Нет еды!")
        return
    await callback.answer(f"🍖 +2 голода. Голод: {player.hunger}/10")
    await cb_night(callback, user, session)

@router.callback_query(F.data == "zs_sleep")
async def cb_sleep(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext):
    import random
    player = await get_player(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)

    if player.game_time >= 360:
        minutes_until_morning = (1440 - player.game_time) + 360
    else:
        minutes_until_morning = 360 - player.game_time

    await advance_time(session, player, minutes_until_morning)
    await reduce_hunger(session, player, 1)

    import random as _r

    if player.day <= 3:
        zombie_hp_range = (20, 35)
        night_damage = (5, 10)
    elif player.day <= 7:
        zombie_hp_range = (35, 55)
        night_damage = (10, 18)
    elif player.day <= 15:
        zombie_hp_range = (55, 80)
        night_damage = (15, 25)
    else:
        zombie_hp_range = (80, 120)
        night_damage = (20, 35)

    dmg_min = night_damage[0]
    dmg_max = night_damage[1]

    base_attack_chance = max(10, 50 - base.defense_level * 10)
    attacked = _r.randint(1, 100) <= base_attack_chance

    if attacked:
        await add_event(session, user.telegram_id, player.day, "night", "🧟 Ночью напала орда зомби!")
        await state.set_state(ZSStates.night_attack)
        zombie_hp = _r.randint(*zombie_hp_range)
        zombie_hp_max = zombie_hp
        hp_bar = "🟥" * 10
        attack_text = (
            f"🌙 Ночью на базу напала орда зомби!\n\n"
            f"❤️ HP: {player.hp}/{player.hp_max}\n\n"
            f"🧟 Орда {hp_bar} {zombie_hp}/{zombie_hp_max}\n"
            f"Отбивайся!"
        )
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Ближний бой", callback_data=f"zs_night_fight_melee_{zombie_hp}_{zombie_hp_max}_{dmg_min}_{dmg_max}")],
            [InlineKeyboardButton(text="🔫 Стрелять",    callback_data=f"zs_night_fight_ranged_{zombie_hp}_{zombie_hp_max}_{dmg_min}_{dmg_max}")],
        ])
        image = await get_image(session, "night_attack")
        if image:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(image.file_id, caption=attack_text, reply_markup=buttons)
        else:
            try:
                await callback.message.edit_text(attack_text, reply_markup=buttons)
            except Exception:
                await callback.message.answer(attack_text, reply_markup=buttons)
        return

    # Нападения не было — лечение медпунктом и утро
    buildings = base.buildings or {}
    medpost_level = buildings.get("medpost", 0)
    heal_amount = 0
    if medpost_level > 0:
        heal_amount = [10, 25, 50][medpost_level - 1]

    old_hp = player.hp
    player.hp = min(player.hp_max, player.hp + heal_amount)
    actual_heal = player.hp - old_hp
    await session.commit()

    # Результаты вылазок НПС
    npc_results = await return_npcs(session, player)
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
                npc_text += f"  🎉 {r['name']} повысил уровень до {r['level']} ({level_data['name']})!\n"
    if npc_results["died"]:
        npc_text += "\n💀 Погибли на задании:\n"
        for name in npc_results["died"]:
            npc_text += f"  ❌ {name}\n"

    new_base = await get_base(session, user.telegram_id)

    hunger = getattr(player, "hunger", 10)
    if hunger == 0:
        hunger_icon = "💀"
    elif hunger <= 3:
        hunger_icon = "⚠️"
    else:
        hunger_icon = "🍖"
    hunger_bar = "🍖" * hunger + "⬛" * (10 - hunger)
    text = "😴 Ты отдохнул до утра.\n"
    if heal_amount > 0:
        text += f"❤️ Восстановлено: +{actual_heal} HP\n"
    text += f"\n❤️ HP: {player.hp}/{player.hp_max}\n"
    text += f"{hunger_bar}\n"
    text += f"{hunger_icon} Голод: {hunger}/10\n"
    text += f"📅 День {player.day}"
    text += npc_text

    import random as _rand
    tip = _rand.choice(TIPS)
    text += f"\n\n✅ Ночь прошла спокойно.\n\n💡 Совет дня: {tip}"
    image = await get_image(session, f"base_{new_base.level}")
    if image:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(image.file_id, caption=text, reply_markup=main_menu(player, new_base))
    else:
        try:
            await callback.message.edit_text(text, reply_markup=main_menu(player, new_base))
        except Exception:
            await callback.message.answer(text, reply_markup=main_menu(player, new_base))

async def handle_victory(callback: CallbackQuery, player: ZSPlayer, session: AsyncSession):
    text = (
        "🎉 ПОБЕДА!\n\n"
        "Учёные Великой Крокожии разработали вакцину!\n"
        "Вертолёты уже летят к тебе.\n\n"
        f"📊 Статистика:\n"
        f"📅 Дней выжито: {player.day}\n"
        f"❤️ HP: {player.hp}/{player.hp_max}\n\n"
        "Ты выжил. Ты победил."
    )
    image = await get_image(session, "finale")
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Играть снова", callback_data="zs_restart")]
    ])
    if image:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(image.file_id, caption=text, reply_markup=buttons)
    else:
        await callback.message.answer(text, reply_markup=buttons)

# ─── РАДИО ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_radio")
async def cb_radio(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    msg = RADIO_MESSAGES.get(player.day, "📻 Помехи в эфире...")
    image = await get_image(session, "radio")
    if image:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(image.file_id, caption=msg, reply_markup=back_button("zs_main"))
    else:
        try:
            await callback.message.edit_text(msg, reply_markup=back_button("zs_main"))
        except Exception:
            await callback.message.answer(msg, reply_markup=back_button("zs_main"))

# ─── ВЫЛАЗКИ ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_raid")
async def cb_raid(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    if not is_daytime(player.game_time):
        await callback.answer("🌙 Ночью вылазки недоступны.")
        return

    base = await get_base(session, user.telegram_id)
    watchtower = (base.buildings or {}).get("watchtower", 0)

    text = "🗺 Выбери локацию для вылазки:\n\n"
    text += "🟢 Тир 1 | 🟡 Тир 2 | 🔴 Тир 3\n\n"

    slot_names_ru = {
        "helmet": "Шлем", "armor": "Броня", "pants": "Штаны",
        "boots": "Обувь", "melee": "Ближнее оружие", "ranged": "Дальнее оружие", "backpack": "Рюкзак"
    }
    for loc_id, loc in LOCATIONS.items():
        tier_icon = {"1": "🟢", "2": "🟡", "3": "🔴"}.get(str(loc["tier"]), "⚪")
        text += f"{tier_icon} {loc['name']} ({loc['time_cost'] // 60}ч)\n"
        if watchtower >= 1:
            res_names = ", ".join([RESOURCES[r]["name"].split()[-1] for r in loc["resources"]])
            text += f"   Ресурсы: {res_names}\n"
            if loc.get("loot"):
                loot_names = ", ".join([slot_names_ru.get(l['slot'], l['slot']) for l in loc["loot"]])
                text += f"   Снаряжение: {loot_names}\n"
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
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_raid_"), lambda c: len(c.data.split("_")) <= 3)
async def cb_raid_location(callback: CallbackQuery, user: User, session: AsyncSession):
    import random
    loc_id = callback.data.replace("zs_raid_", "")
    loc = LOCATIONS.get(loc_id)
    if not loc:
        await callback.answer("❌ Локация не найдена.")
        return

    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    equipment = dict(inventory.equipment or {})
    backpack_slots = get_backpack_slots(equipment)

    await advance_time(session, player, loc["time_cost"])
    hunger_cost = loc["tier"]
    await reduce_hunger(session, player, hunger_cost)

    encountered_zombies = []
    zombie_chance = loc["zombie_chance"]
    max_zombies = loc["max_zombies"]

    for i in range(max_zombies):
        if i == 0:
            if random.randint(1, 100) <= zombie_chance:
                hp = random.randint(*loc["zombie_hp"])
                encountered_zombies.append(hp)
        else:
            extra_chance = zombie_chance - (i * 20)
            if extra_chance > 0 and random.randint(1, 100) <= extra_chance:
                hp = random.randint(*loc["zombie_hp"])
                encountered_zombies.append(hp)

    npc_found = random.randint(1, 100) <= loc["npc_chance"]

    if encountered_zombies:
        zombie_hp = encountered_zombies[0]
        zombie_hp_max = zombie_hp
        remaining = len(encountered_zombies) - 1
        hp_bar = "🟥" * 10
        text = (
            f"🗺 Вылазка: {loc['name']}\n\n"
            f"🧟 Зомби {hp_bar} {zombie_hp}/{zombie_hp_max}\n"
            f"❤️ Ты: {player.hp}/{player.hp_max}\n"
        )
        if remaining > 0:
            text += f"⚠️ Ещё зомби впереди: {remaining}\n"
        if npc_found:
            text += "\n👤 Вдали виден выживший!\n"
        text += "\nЗомби преградил путь!"

        extra = f"_npc" if npc_found else "_nonpc"
        extra += f"_rem{remaining}"

        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Ближний бой", callback_data=f"zs_fight_melee_{loc_id}_{zombie_hp}_{zombie_hp_max}_0{extra}")],
            [InlineKeyboardButton(text="🔫 Стрелять",    callback_data=f"zs_fight_ranged_{loc_id}_{zombie_hp}_{zombie_hp_max}_0{extra}")],
            [InlineKeyboardButton(text="🏃 Убежать",     callback_data=f"zs_fight_run_{loc_id}_{zombie_hp}_{zombie_hp_max}_0{extra}")],
        ])

        image = await get_image(session, f"zombie_{loc['tier']}")
        if image:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(image.file_id, caption=text, reply_markup=buttons)
        else:
            try:
                await callback.message.edit_text(text, reply_markup=buttons)
            except Exception:
                await callback.message.answer(text, reply_markup=buttons)
    else:
        found_resources = {}
        for res_id, res_data in loc["resources"].items():
            if random.randint(1, 100) <= res_data["chance"]:
                amount = min(
                    random.randint(res_data["min"], res_data["max"]),
                    backpack_slots - sum(found_resources.values())
                )
                if amount > 0:
                    found_resources[res_id] = amount
                if sum(found_resources.values()) >= backpack_slots:
                    break

        if found_resources:
            await add_resources(session, inventory, found_resources)

        eq = dict(inventory.equipment or {})
        found_equip = []
        for loot in loc.get("loot", []):
            slot = loot["slot"]
            tier = loot["tier"]
            if eq.get(slot, 0) == 0 and random.randint(1, 100) <= loot["chance"]:
                eq[slot] = tier
                item = get_equipment_item(slot, tier)
                found_equip.append(item.get("name", slot))
        if found_equip:
            inventory.equipment = eq
            await session.commit()

        if npc_found:
            npc = await add_npc(session, user.telegram_id)
            npc_text = f"\n\n👤 Найден выживший: {npc.name}!" if npc else "\n\n👤 База переполнена, нет места для выжившего."
        else:
            npc_text = ""

        res_text = ""
        if found_resources:
            res_text = "\n\n📦 Найдено:\n"
            for res_id, amount in found_resources.items():
                res_text += f"  {RESOURCES[res_id]['name']}: {amount}\n"
            if sum(found_resources.values()) >= backpack_slots:
                res_text += "  🎒 Рюкзак полон!\n"
        else:
            res_text = "\n\n📦 Ничего не найдено."

        loot_text = ""
        if found_equip:
            loot_text = "\n🎁 Найдено снаряжение:\n"
            for item_name in found_equip:
                loot_text += f"  ✨ {item_name}\n"

        await add_event(session, user.telegram_id, player.day,
            "raid", f"🗺 Вылазка в {loc['name']} — без зомби.{res_text.replace(chr(10), ' ')}")
        text = (
            f"🗺 Вылазка: {loc['name']}\n\n"
            f"✅ Всё спокойно.{res_text}{loot_text}{npc_text}\n\n"
            f"❤️ {player.hp}/{player.hp_max}"
        )
        buttons = [[InlineKeyboardButton(text="◀️ На базу", callback_data="zs_main")]]
        try:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception:
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ─── БОЙ ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("zs_fight_"))
async def cb_fight(callback: CallbackQuery, user: User, session: AsyncSession):
    import random
    parts = callback.data.split("_")
    action = parts[2]

    data_part = callback.data.replace(f"zs_fight_{action}_", "")
    has_npc = "_npc" in data_part
    data_part = data_part.replace("_npc", "").replace("_nonpc", "")

    remaining_zombies = 0
    if "_rem" in data_part:
        rem_idx = data_part.index("_rem")
        remaining_zombies = int(data_part[rem_idx + 4:])
        data_part = data_part[:rem_idx]

    num_parts = data_part.split("_")
    zombie_hp = int(num_parts[-3])
    zombie_hp_max = int(num_parts[-2])
    loc_id = "_".join(num_parts[:-3])

    loc = LOCATIONS.get(loc_id, {})
    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    equipment = inventory.equipment or {}
    backpack_slots = get_backpack_slots(equipment)

    zombie_damage_range = loc.get("zombie_damage", (10, 20))
    damage_taken = 0
    victory = False
    fled = False
    result_text = ""

    if action == "melee":
        melee_tier = equipment.get("melee", 0)
        melee_item = get_equipment_item("melee", melee_tier)
        player_damage = melee_item.get("damage", 5)
        zombie_hp -= player_damage
        if zombie_hp <= 0:
            victory = True
            result_text = f"⚔️ Удар! ({player_damage} урона) — Зомби убит!"
        else:
            damage_taken = random.randint(*zombie_damage_range)
            result_text = f"⚔️ Удар! ({player_damage} урона) — Зомби контратакует!"

    elif action == "ranged":
        ranged_tier = equipment.get("ranged", 0)
        if ranged_tier == 0:
            damage_taken = random.randint(*zombie_damage_range)
            result_text = "🔫 Нет оружия дальнего боя!"
        else:
            ranged_item = get_equipment_item("ranged", ranged_tier)
            ammo_cost = ranged_item.get("ammo_cost", 0)
            resources = dict(inventory.resources or {})
            if ammo_cost > 0 and resources.get("ammo", 0) < ammo_cost:
                damage_taken = random.randint(*zombie_damage_range)
                result_text = "🔫 Нет патронов!"
            else:
                if ammo_cost > 0:
                    resources["ammo"] -= ammo_cost
                    inventory.resources = resources
                player_damage = ranged_item.get("damage", 0)
                zombie_hp -= player_damage
                if zombie_hp <= 0:
                    victory = True
                    result_text = f"🔫 Выстрел! ({player_damage} урона) — Зомби убит!"
                else:
                    damage_taken = random.randint(0, zombie_damage_range[1] // 2)
                    result_text = f"🔫 Выстрел! ({player_damage} урона) — Зомби ещё жив!"

    else:  # run
        fled = True
        result_text = "🏃 Ты убежал! Лут не получен."

    defense = get_total_defense(equipment)
    actual_damage = max(0, damage_taken - defense // 5)
    player.hp = max(0, player.hp - actual_damage)
    await session.commit()

    damage_text = ""
    if actual_damage > 0:
        absorbed = damage_taken - actual_damage
        damage_text = f"\n💥 Урон: {actual_damage}"
        if absorbed > 0:
            damage_text += f" (🛡 поглощено {absorbed})"

    if player.hp <= 0:
        player.is_alive = False
        await session.commit()
        text = f"{result_text}{damage_text}\n\n💀 Ты погиб. Игра окончена."
        image = await get_image(session, "death")
        if image:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(image.file_id, caption=text, reply_markup=dead_menu())
        else:
            try:
                await callback.message.edit_text(text, reply_markup=dead_menu())
            except Exception:
                await callback.message.answer(text, reply_markup=dead_menu())
        return

    if fled:
        text = f"{result_text}\n\n❤️ {player.hp}/{player.hp_max}"
        buttons = [[InlineKeyboardButton(text="◀️ На базу", callback_data="zs_main")]]
        try:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception:
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        return

    if not victory:
        zombie_hp = max(0, zombie_hp)
        filled = zombie_hp * 10 // zombie_hp_max
        hp_bar = "🟥" * filled + "⬛" * (10 - filled)
        text = (
            f"🧟 Зомби {hp_bar} {zombie_hp}/{zombie_hp_max}\n"
            f"❤️ Ты: {player.hp}/{player.hp_max}\n\n"
            f"{result_text}{damage_text}"
        )
        extra = "_npc" if has_npc else "_nonpc"
        extra += f"_rem{remaining_zombies}"
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Ближний бой", callback_data=f"zs_fight_melee_{loc_id}_{zombie_hp}_{zombie_hp_max}_0{extra}")],
            [InlineKeyboardButton(text="🔫 Стрелять",    callback_data=f"zs_fight_ranged_{loc_id}_{zombie_hp}_{zombie_hp_max}_0{extra}")],
            [InlineKeyboardButton(text="🏃 Убежать",     callback_data=f"zs_fight_run_{loc_id}_{zombie_hp}_{zombie_hp_max}_0{extra}")],
        ])
        try:
            await callback.message.edit_text(text, reply_markup=buttons)
        except Exception:
            await callback.message.answer(text, reply_markup=buttons)
        return

    # Победа!
    if remaining_zombies > 0:
        next_zombie_hp = random.randint(*loc.get("zombie_hp", (20, 40)))
        hp_bar = "🟥" * 10
        text = (
            f"{result_text}{damage_text}\n\n"
            f"⚠️ Следующий зомби!\n\n"
            f"🧟 Зомби {hp_bar} {next_zombie_hp}/{next_zombie_hp}\n"
            f"❤️ Ты: {player.hp}/{player.hp_max}"
        )
        extra = "_npc" if has_npc else "_nonpc"
        extra += f"_rem{remaining_zombies - 1}"
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Ближний бой", callback_data=f"zs_fight_melee_{loc_id}_{next_zombie_hp}_{next_zombie_hp}_0{extra}")],
            [InlineKeyboardButton(text="🔫 Стрелять",    callback_data=f"zs_fight_ranged_{loc_id}_{next_zombie_hp}_{next_zombie_hp}_0{extra}")],
            [InlineKeyboardButton(text="🏃 Убежать",     callback_data=f"zs_fight_run_{loc_id}_{next_zombie_hp}_{next_zombie_hp}_0{extra}")],
        ])
        try:
            await callback.message.edit_text(text, reply_markup=buttons)
        except Exception:
            await callback.message.answer(text, reply_markup=buttons)
        return

    # Все зомби убиты — выдаём лут
    found_resources = {}
    for res_id, res_data in loc.get("resources", {}).items():
        if random.randint(1, 100) <= res_data["chance"]:
            amount = min(
                random.randint(res_data["min"], res_data["max"]),
                backpack_slots - sum(found_resources.values())
            )
            if amount > 0:
                found_resources[res_id] = amount
            if sum(found_resources.values()) >= backpack_slots:
                break

    if found_resources:
        await add_resources(session, inventory, found_resources)

    eq = dict(inventory.equipment or {})
    found_equip = []
    for loot in loc.get("loot", []):
        slot = loot["slot"]
        tier = loot["tier"]
        if eq.get(slot, 0) == 0 and random.randint(1, 100) <= loot["chance"]:
            eq[slot] = tier
            item = get_equipment_item(slot, tier)
            found_equip.append(item.get("name", slot))
    if found_equip:
        inventory.equipment = eq
        await session.commit()

    npc_text = ""
    if has_npc:
        npc = await add_npc(session, user.telegram_id)
        npc_text = f"\n\n👤 Спасён выживший: {npc.name}!" if npc else "\n\n👤 База переполнена!"

    loot_text = ""
    if found_resources:
        loot_text = "\n\n📦 Ресурсы:\n"
        for res_id, amount in found_resources.items():
            loot_text += f"  {RESOURCES[res_id]['name']}: {amount}\n"
    else:
        loot_text = "\n\n📦 Ресурсов не найдено."
    if found_equip:
        loot_text += "\n🎁 Снаряжение:\n"
        for item_name in found_equip:
            loot_text += f"  ✨ {item_name}\n"

    text = (
        f"🧟 Все зомби повержены!\n\n"
        f"{result_text}{damage_text}"
        f"{loot_text}{npc_text}\n\n"
        f"❤️ {player.hp}/{player.hp_max}"
    )
    buttons = [[InlineKeyboardButton(text="◀️ На базу", callback_data="zs_main")]]
    image = await get_image(session, "victory")
    if image:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(image.file_id, caption=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        try:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception:
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ─── НОЧНОЙ БОЙ ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("zs_night_fight_"))
async def cb_night_fight(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext):
    import random
    parts = callback.data.replace("zs_night_fight_", "").split("_")
    action = parts[0]
    zombie_hp = int(parts[-4])
    zombie_hp_max = int(parts[-3])
    dmg_min = int(parts[-2])
    dmg_max = int(parts[-1])

    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)
    equipment = inventory.equipment or {}

    zombie_damage_range = (dmg_min, dmg_max)
    damage_taken = 0
    victory = False
    result_text = ""

    if action == "melee":
        melee_tier = equipment.get("melee", 0)
        melee_item = get_equipment_item("melee", melee_tier)
        player_damage = melee_item.get("damage", 5)
        zombie_hp -= player_damage
        if zombie_hp <= 0:
            victory = True
            result_text = f"⚔️ Удар! ({player_damage} урона) — Зомби убит!"
        else:
            damage_taken = random.randint(*zombie_damage_range)
            result_text = f"⚔️ Удар! ({player_damage} урона) — Зомби контратакует!"

    elif action == "ranged":
        ranged_tier = equipment.get("ranged", 0)
        if ranged_tier == 0:
            damage_taken = random.randint(*zombie_damage_range)
            result_text = "🔫 Нет оружия дальнего боя!"
        else:
            ranged_item = get_equipment_item("ranged", ranged_tier)
            ammo_cost = ranged_item.get("ammo_cost", 0)
            resources = dict(inventory.resources or {})
            if ammo_cost > 0 and resources.get("ammo", 0) < ammo_cost:
                damage_taken = random.randint(*zombie_damage_range)
                result_text = "🔫 Нет патронов!"
            else:
                if ammo_cost > 0:
                    resources["ammo"] -= ammo_cost
                    inventory.resources = resources
                player_damage = ranged_item.get("damage", 0)
                zombie_hp -= player_damage
                if zombie_hp <= 0:
                    victory = True
                    result_text = f"🔫 Выстрел! ({player_damage} урона) — Зомби убит!"
                else:
                    damage_taken = random.randint(0, zombie_damage_range[1] // 2)
                    result_text = f"🔫 Выстрел! ({player_damage} урона) — Зомби ещё жив!"

    defense = get_total_defense(equipment)
    actual_damage = max(0, damage_taken - defense // 5)

    # НПС помогают в обороне
    npcs = await get_npcs(session, user.telegram_id)
    idle_npcs = [n for n in npcs if n.status == "idle"]
    npc_damage = len(idle_npcs) * random.randint(3, 8)
    if not victory:
        zombie_hp -= npc_damage

    if zombie_hp <= 0:
        victory = True
        if npc_damage > 0:
            result_text += f"\n👥 Выжившие помогли! ({npc_damage} урона)"

    player.hp = max(0, player.hp - actual_damage)
    await session.commit()

    damage_text = ""
    if actual_damage > 0:
        absorbed = damage_taken - actual_damage
        damage_text = f"\n💥 Урон: {actual_damage}"
        if absorbed > 0:
            damage_text += f" (🛡 поглощено {absorbed})"

    if player.hp <= 0:
        player.is_alive = False
        await session.commit()
        text = f"{result_text}{damage_text}\n\n💀 Ты погиб. Игра окончена."
        image = await get_image(session, "death")
        if image:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(image.file_id, caption=text, reply_markup=dead_menu())
        else:
            try:
                await callback.message.edit_text(text, reply_markup=dead_menu())
            except Exception:
                await callback.message.answer(text, reply_markup=dead_menu())
        return

    if victory:
        # Лечение медпунктом после победы
        buildings = base.buildings or {}
        medpost_level = buildings.get("medpost", 0)
        heal_amount = 0
        if medpost_level > 0:
            heal_amount = [10, 25, 50][medpost_level - 1]
        old_hp = player.hp
        player.hp = min(player.hp_max, player.hp + heal_amount)
        actual_heal = player.hp - old_hp
        await session.commit()

        if heal_amount > 0:
            morning_text = f"\n\n☀️ Утро: ❤️ +{actual_heal} HP от медпункта"
        else:
            morning_text = ""

        # Результаты НПС — возвращаем после победы
        npc_text = ""
        await state.clear()
        try:
            nr = await return_npcs(session, player)
            if nr["returned"]:
                npc_text += "\n\n👥 Выжившие вернулись:\n"
                for r in nr["returned"]:
                    if r["resources"]:
                        res_list = ", ".join([f"{RESOURCES[res]['name'].split()[-1]} x{amt}" for res, amt in r["resources"].items()])
                        npc_text += f"  ✅ {r['name']}: {res_list}\n"
                    else:
                        npc_text += f"  ✅ {r['name']}: ничего не нашёл\n"
                    if r.get("leveled_up"):
                        level_data = get_npc_level_data(r["level"])
                        npc_text += f"  🎉 {r['name']} повысил уровень до {r['level']} ({level_data['name']})!\n"
            if nr["died"]:
                npc_text += "\n💀 Погибли на задании:\n"
                for name in nr["died"]:
                    npc_text += f"  ❌ {name}\n"
        except Exception:
            pass

        import random as _rtip
        tip = _rtip.choice(TIPS)

        hunger = getattr(player, "hunger", 10)
        if hunger == 0:
            hunger_icon = "💀"
        elif hunger <= 3:
            hunger_icon = "⚠️"
        else:
            hunger_icon = "🍖"
        hunger_bar = "🍖" * hunger + "⬛" * (10 - hunger)

        text = (
            f"🌙 Ночное нападение отбито!\n\n"
            f"{result_text}{damage_text}\n\n"
            f"❤️ HP: {player.hp}/{player.hp_max}\n"
            f"{hunger_bar}\n"
            f"{hunger_icon} Голод: {hunger}/10\n"
            f"📅 День {player.day}"
            f"{morning_text}"
            f"{npc_text}\n\n"
            f"💡 Совет дня: {tip}"
        )
        image = await get_image(session, f"base_{base.level}")
        if image:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(image.file_id, caption=text, reply_markup=main_menu(player, base))
        else:
            try:
                await callback.message.edit_text(text, reply_markup=main_menu(player, base))
            except Exception:
                await callback.message.answer(text, reply_markup=main_menu(player, base))
    else:
        zombie_hp = max(0, zombie_hp)
        filled = zombie_hp * 10 // zombie_hp_max
        hp_bar = "🟥" * filled + "⬛" * (10 - filled)
        text = (
            f"🧟 Орда {hp_bar} {zombie_hp}/{zombie_hp_max}\n"
            f"❤️ Ты: {player.hp}/{player.hp_max}\n\n"
            f"{result_text}{damage_text}"
        )
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Ближний бой", callback_data=f"zs_night_fight_melee_{zombie_hp}_{zombie_hp_max}_{dmg_min}_{dmg_max}")],
            [InlineKeyboardButton(text="🔫 Стрелять",    callback_data=f"zs_night_fight_ranged_{zombie_hp}_{zombie_hp_max}_{dmg_min}_{dmg_max}")],
        ])
        try:
            await callback.message.edit_text(text, reply_markup=buttons)
        except Exception:
            await callback.message.answer(text, reply_markup=buttons)

# ─── БАЗА ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_base")
async def cb_base(callback: CallbackQuery, user: User, session: AsyncSession):
    base = await get_base(session, user.telegram_id)
    buildings = base.buildings or {}
    defense = DEFENSE_LEVELS[base.defense_level]

    text = f"🏠 База (уровень {base.level}/5)\n"
    text += f"🛡 Защита: {defense['name']} (-{defense['damage_reduction']}% урона)\n\n"
    text += "Постройки:\n"
    for b_id, b_data in BUILDINGS.items():
        level = buildings.get(b_id, 0)
        max_level = len(b_data["levels"])
        text += f"  {b_data['name']}: {'ур.' + str(level) + '/' + str(max_level) if level > 0 else 'не построено'}\n"

    buttons = [
        [InlineKeyboardButton(text="🏗 Строить/улучшать", callback_data="zs_build_menu")],
    ]

    if base.level < 5:
        next_level = base.level + 1
        if next_level in BASE_LEVELS:
            buttons.append([InlineKeyboardButton(
                text=f"⬆️ Улучшить базу до ур.{next_level}",
                callback_data="zs_upgrade_base"
            )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "zs_build_menu")
async def cb_build_menu(callback: CallbackQuery, user: User, session: AsyncSession):
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    buildings = base.buildings or {}
    resources = inventory.resources or {}

    text = "🏗 Строительство\n\n"

    text += "📋 Постройки:\n"
    for b_id, b_data in BUILDINGS.items():
        current_level = buildings.get(b_id, 0)
        if current_level < len(b_data["levels"]):
            next_level = b_data["levels"][current_level]
            cost = next_level["cost"]
            can_afford = all(resources.get(r, 0) >= a for r, a in cost.items())
            icon = "✅" if can_afford else "❌"
            action = f"ур.{current_level}→{current_level+1}" if current_level > 0 else "построить"
            cost_lines = "\n".join([f"      - {RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in cost.items()])
            text += f"{icon} {b_data['name']} ({action})\n"
            text += f"   {b_data['description']}\n"
            text += f"   Нужно:\n{cost_lines}\n\n"

    defense_level = base.defense_level
    if defense_level < len(DEFENSE_LEVELS) - 1:
        next_defense = DEFENSE_LEVELS[defense_level + 1]
        cost = next_defense["cost"]
        can_afford = all(resources.get(r, 0) >= a for r, a in cost.items())
        icon = "✅" if can_afford else "❌"
        cost_lines = "\n".join([f"      - {RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in cost.items()]) if cost else "бесплатно"
        text += f"🛡 Защита:\n"
        text += f"{icon} {next_defense['name']} (-{next_defense['damage_reduction']}% урона)\n"
        text += f"   Нужно:\n{cost_lines}\n\n"

    buttons = []
    for b_id, b_data in BUILDINGS.items():
        current_level = buildings.get(b_id, 0)
        if current_level < len(b_data["levels"]):
            next_level_data = b_data["levels"][current_level]
            can_afford = all(resources.get(r, 0) >= a for r, a in next_level_data["cost"].items())
            icon = "✅" if can_afford else "❌"
            action = "Улучшить" if current_level > 0 else "Построить"
            buttons.append([InlineKeyboardButton(
                text=f"{icon} {action} {b_data['name']}",
                callback_data=f"zs_build_{b_id}"
            )])

    if defense_level < len(DEFENSE_LEVELS) - 1:
        next_defense = DEFENSE_LEVELS[defense_level + 1]
        cost = next_defense["cost"]
        can_afford = all(resources.get(r, 0) >= a for r, a in cost.items()) if cost else True
        icon = "✅" if can_afford else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{icon} Улучшить защиту → {next_defense['name']}",
            callback_data="zs_build_defense"
        )])

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_base")])
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_build_"))
async def cb_build(callback: CallbackQuery, user: User, session: AsyncSession):
    build_id = callback.data.replace("zs_build_", "")
    result = await build(session, user.telegram_id, build_id)
    if result["success"]:
        await callback.answer("✅ Построено!")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_base(callback, user, session)

@router.callback_query(F.data == "zs_upgrade_base")
async def cb_upgrade_base(callback: CallbackQuery, user: User, session: AsyncSession):
    base = await get_base(session, user.telegram_id)
    next_level = base.level + 1

    if next_level not in BASE_LEVELS:
        await callback.answer("✅ База уже максимального уровня.")
        return

    req = BASE_LEVELS[next_level]
    req_text = "Требования:\n"
    for b_id, level in req["requirements"].items():
        req_text += f"  {BUILDINGS[b_id]['name']} ур.{level}\n"
    cost_text = ", ".join([f"{RESOURCES[r]['name']} x{a}" for r, a in req["cost"].items()])
    req_text += f"💰 {cost_text}"

    buttons = [
        [InlineKeyboardButton(text=f"✅ Улучшить до ур.{next_level}", callback_data="zs_upgrade_base_confirm")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="zs_base")],
    ]
    try:
        await callback.message.edit_text(
            f"⬆️ Улучшение базы до уровня {next_level}\n\n{req_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            f"⬆️ Улучшение базы до уровня {next_level}\n\n{req_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data == "zs_upgrade_base_confirm")
async def cb_upgrade_base_confirm(callback: CallbackQuery, user: User, session: AsyncSession):
    result = await upgrade_base(session, user.telegram_id)
    if result["success"]:
        await callback.answer(f"✅ База улучшена до уровня {result['level']}!")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_base(callback, user, session)

# ─── ИНВЕНТАРЬ ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_inventory")
async def cb_inventory(callback: CallbackQuery, user: User, session: AsyncSession):
    inventory = await get_inventory(session, user.telegram_id)
    equipment = inventory.equipment or {}
    resources = inventory.resources or {}
    defense = get_total_defense(equipment)
    slots = get_backpack_slots(equipment)

    slot_names = {
        "helmet":   "🪖 Шлем",
        "armor":    "👕 Броня",
        "pants":    "👖 Штаны",
        "boots":    "👟 Обувь",
        "melee":    "⚔️ Ближний бой",
        "ranged":   "🔫 Дальний бой",
        "backpack": "🎒 Рюкзак",
    }

    text = "🎒 Инвентарь\n\n🛡 Снаряжение:\n"
    for slot_id, slot_name in slot_names.items():
        tier = equipment.get(slot_id, 0)
        item = get_equipment_item(slot_id, tier)
        text += f"  {slot_name}: {item.get('name', '—')}\n"

    text += f"\n🛡 Защита: {defense} | 🎒 Слотов на вылазке: {slots}\n"

    text += "\n📦 Ресурсы:\n"
    if resources:
        for res_id, amount in resources.items():
            if amount > 0:
                text += f"  {RESOURCES.get(res_id, {}).get('name', res_id)}: {amount}\n"
    else:
        text += "  Пусто\n"

    food = resources.get("food", 0)
    buttons = [
        [InlineKeyboardButton(text="⬆️ Улучшить снаряжение", callback_data="zs_upgrade_menu")],
    ]
    if food > 0:
        buttons.append([InlineKeyboardButton(text=f"🍖 Поесть (+2 голода) | Еда: {food}", callback_data="zs_eat_day")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")])
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data == "zs_eat_day")
async def cb_eat_day(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    if getattr(player, "hunger", 10) >= 10:
        await callback.answer("🍖 Голод уже полный!")
        return
    success = await eat_food(session, player, inventory)
    if not success:
        await callback.answer("❌ Нет еды!")
        return
    await callback.answer(f"🍖 +2 голода. Голод: {player.hunger}/10")
    await cb_inventory(callback, user, session)

@router.callback_query(F.data == "zs_upgrade_menu")
async def cb_upgrade_menu(callback: CallbackQuery, user: User, session: AsyncSession):
    base = await get_base(session, user.telegram_id)
    inventory = await get_inventory(session, user.telegram_id)
    equipment = inventory.equipment or {}
    resources = inventory.resources or {}
    workshop_tier = get_workshop_tier(base.buildings or {})

    if workshop_tier == 0:
        try:
            await callback.message.edit_text(
                "❌ Нужна мастерская для улучшения снаряжения.",
                reply_markup=back_button("zs_inventory")
            )
        except Exception:
            await callback.message.answer(
                "❌ Нужна мастерская для улучшения снаряжения.",
                reply_markup=back_button("zs_inventory")
            )
        return

    slot_names = {
        "helmet":   "🪖 Шлем",
        "armor":    "👕 Броня",
        "pants":    "👖 Штаны",
        "boots":    "👟 Обувь",
        "melee":    "⚔️ Ближний бой",
        "ranged":   "🔫 Дальний бой",
        "backpack": "🎒 Рюкзак",
    }

    text = f"⬆️ Улучшение снаряжения\n🔧 Мастерская тир {workshop_tier}\n\n"
    buttons = []

    for slot_id, slot_name in slot_names.items():
        tier = equipment.get(slot_id, 0)
        chain = EQUIPMENT_CHAINS.get(slot_id, [])
        if tier + 1 < len(chain):
            next_item = chain[tier + 1]
            if next_item.get("craft_tier", 1) <= workshop_tier:
                cost = next_item.get("cost", {})
                can_afford = all(resources.get(r, 0) >= a for r, a in cost.items())
                icon = "✅" if can_afford else "❌"
                current_item = get_equipment_item(slot_id, tier)
                cost_lines = "\n".join([f"    - {RESOURCES[r]['name'].split()[-1]} x{a}" for r, a in cost.items()])
                text += f"{icon} {slot_name}\n"
                text += f"  {current_item.get('name')} → {next_item['name']}\n"
                text += f"  Нужно:\n{cost_lines}\n\n"
                buttons.append([InlineKeyboardButton(
                    text=f"{icon} {slot_name} → {next_item['name']}",
                    callback_data=f"zs_upgrade_{slot_id}"
                )])

    if not buttons:
        try:
            await callback.message.edit_text(
                "✅ Всё снаряжение максимального уровня для текущей мастерской.",
                reply_markup=back_button("zs_inventory")
            )
        except Exception:
            await callback.message.answer(
                "✅ Всё снаряжение максимального уровня для текущей мастерской.",
                reply_markup=back_button("zs_inventory")
            )
        return

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_inventory")])
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_upgrade_"))
async def cb_upgrade_item(callback: CallbackQuery, user: User, session: AsyncSession):
    slot = callback.data.replace("zs_upgrade_", "")
    result = await upgrade_equipment(session, user.telegram_id, slot)
    if result["success"]:
        await callback.answer(f"✅ {result['item']['name']} готово!")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_upgrade_menu(callback, user, session)

# ─── НПС ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_npcs")
async def cb_npcs(callback: CallbackQuery, user: User, session: AsyncSession):
    npcs = await get_npcs(session, user.telegram_id)
    base = await get_base(session, user.telegram_id)
    max_npcs = get_max_npcs(base.level)

    if not npcs:
        text = f"👥 Выжившие (0/{max_npcs})\n\nНикого нет. Ищи выживших на вылазках."
        buttons = [[InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")]]
    else:
        text = f"👥 Выжившие ({len(npcs)}/{max_npcs})\n\n"
        buttons = []
        for npc in npcs:
            level_data = get_npc_level_data(npc.level)
            exp_needed = get_npc_exp_needed(npc.level)
            status = "🏠 На базе" if npc.status == "idle" else f"🗺 На задании ({npc.location})"
            loc_name = LOCATIONS.get(npc.location, {}).get("name", npc.location) if npc.location else ""
            status_text = "🏠 На базе" if npc.status == "idle" else f"🗺 На задании ({loc_name})"
            text += f"👤 {npc.name}\n"
            text += f"   ⭐ Ур.{npc.level} {level_data['name']} | Опыт: {npc.exp}/{exp_needed}\n"
            text += f"   📊 Заданий выполнено: {npc.missions_survived}/{npc.missions_total}\n"
            text += f"   Статус: {status_text}\n\n"
            if npc.status == "idle":
                buttons.append([InlineKeyboardButton(
                    text=f"📤 Отправить {npc.name} (Ур.{npc.level})",
                    callback_data=f"zs_send_npc_{npc.id}"
                )])
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_main")])

    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(F.data.startswith("zs_send_npc_"))
async def cb_send_npc(callback: CallbackQuery, user: User, session: AsyncSession):
    npc_id = int(callback.data.replace("zs_send_npc_", ""))
    buttons = []
    for loc_id, loc in LOCATIONS.items():
        tier_icon = {"1": "🟢", "2": "🟡", "3": "🔴"}.get(str(loc["tier"]), "⚪")
        buttons.append([InlineKeyboardButton(
            text=f"{tier_icon} {loc['name']}",
            callback_data=f"zs_npc_mission_{npc_id}_{loc_id}"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="zs_npcs")])
    try:
        await callback.message.edit_text(
            "📤 Выбери локацию для задания:\n\nВыживший вернётся в конце дня.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception:
        await callback.message.answer(
            "📤 Выбери локацию для задания:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

@router.callback_query(F.data.startswith("zs_npc_mission_"))
async def cb_npc_mission(callback: CallbackQuery, user: User, session: AsyncSession):
    parts = callback.data.replace("zs_npc_mission_", "").split("_")
    npc_id = int(parts[0])
    loc_id = "_".join(parts[1:])
    result = await send_npc_on_mission(session, npc_id, loc_id)
    if result["success"]:
        loc = LOCATIONS.get(loc_id, {})
        await callback.answer(f"✅ Отправлен в {loc.get('name', loc_id)}")
    else:
        await callback.answer(f"❌ {result['error']}")
    await cb_npcs(callback, user, session)

# ─── РЕСТАРТ ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_restart")
async def cb_restart(callback: CallbackQuery, user: User, session: AsyncSession, state: FSMContext):
    await reset_player(session, user.telegram_id)
    await callback.message.answer(
        "🔄 Начинаем заново!\n\nВведи имя своего персонажа:"
    )
    await state.set_state(ZSStates.entering_name)

# ─── УПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ (только owner) ─────────────────────────────────

@router.message(Command("zsimages"))
async def cmd_zs_images(message: Message, user: User):
    if user.role != "owner":
        await message.answer("⛔ Только для владельца.")
        return
    text = "🖼 Управление изображениями игры\n\n"
    text += "Отправь изображение с подписью (ключ):\n\n"
    for key in IMAGE_KEYS:
        text += f"  {key}\n"
    await message.answer(text)

@router.message(F.photo, F.caption.in_(IMAGE_KEYS))
async def process_zs_image(message: Message, user: User, session: AsyncSession):
    if user.role != "owner":
        return
    key = message.caption
    file_id = message.photo[-1].file_id
    await set_image(session, key, file_id, user.telegram_id)
    await message.answer(f"✅ Изображение '{key}' сохранено!")

# ─── ПОМОЩЬ ──────────────────────────────────────────────────────────────────

TIPS = [
    "Сначала построй огород — еда нужна постоянно.",
    "Не ходи в тир 2 локации без снаряжения — зомби там сильные.",
    "Отправляй НПС на задания каждый день — они приносят ресурсы.",
    "Строй медпункт как можно раньше — HP само не восстанавливается.",
    "Следи за голодом перед вылазкой — при 0 теряешь HP.",
    "Защита базы снижает урон от ночных нападений.",
    "Рюкзак увеличивает количество ресурсов с вылазки.",
    "В тир 3 локациях самые редкие ресурсы — кевлар, оптика, редкие металлы.",
    "Мастерская открывает крафт снаряжения — строй её как можно раньше.",
    "НПС помогают в ночной обороне — чем больше, тем лучше.",
    "Наблюдательная вышка показывает ресурсы и шанс зомби в локациях.",
    "Улучшай снаряжение постепенно — сначала оружие, потом броню.",
]

HELP_TEXT = (
    "❓ Помощь\n\n"
    "🎮 Основы:\n"
    "— Голод уменьшается на вылазках (-1/2/3) и ночью (-1)\n"
    "— При голоде 0 теряешь 10 HP за каждое действие\n"
    "— HP восстанавливается только через медпункт ночью\n"
    "— Еда восстанавливает +2 голода за единицу\n\n"
    "🏗 Постройки:\n"
    "— 🏠 Убежище — +20/40/60 макс HP (ур.1/2/3)\n"
    "— 🔧 Мастерская — крафт снаряжения тир 1-3/4-5/6-8\n"
    "— 🌱 Огород — +2/5/10 еды каждое утро\n"
    "— 🏥 Медпункт — +10/25/50 HP каждое утро\n"
    "— 🔭 Вышка — инфо о локациях перед вылазкой\n\n"
    "🛡 Защита базы:\n"
    "— Снижает урон от ночных нападений\n"
    "— 5 уровней: -10%/-25%/-40%/-60%/-80% урона\n\n"
    "👥 НПС:\n"
    "— Находишь на вылазках, отправляешь на задания\n"
    "— Возвращаются утром с ресурсами\n"
    "— Помогают в ночной обороне\n\n"
    "🗺 Локации:\n"
    "— Тир 1 (2ч) — безопасно, базовые ресурсы\n"
    "— Тир 2 (4ч) — опасно, средние ресурсы\n"
    "— Тир 3 (6ч) — очень опасно, редкие ресурсы\n\n"
    "👥 Уровни выживших:\n"
    "— Ур.1 Новичок — шанс гибели 25%, лут x1.0\n"
    "— Ур.2 Выживший — шанс гибели 18%, лут x1.1\n"
    "— Ур.3 Опытный — шанс гибели 12%, лут x1.2\n"
    "— Ур.4 Ветеран — шанс гибели 7%, лут x1.35\n"
    "— Ур.5 Легенда — шанс гибели 3%, лут x1.5\n"
    "— Опыт: +1 за задание, +1 за ночную оборону"
)

@router.callback_query(F.data == "zs_help")
async def cb_zs_help(callback: CallbackQuery, user: User):
    try:
        await callback.message.edit_text(HELP_TEXT, reply_markup=back_button("zs_main"))
    except Exception:
        await callback.message.answer(HELP_TEXT, reply_markup=back_button("zs_main"))

# ─── ЛОГ СОБЫТИЙ ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "zs_log")
async def cb_zs_log(callback: CallbackQuery, user: User, session: AsyncSession):
    player = await get_player(session, user.telegram_id)
    events = await get_events(session, user.telegram_id, player.day)
    if not events:
        try:
            await callback.message.edit_text("📋 Лог событий пуст.", reply_markup=back_button("zs_main"))
        except Exception:
            await callback.message.answer("📋 Лог событий пуст.", reply_markup=back_button("zs_main"))
        return
    text = "📋 Лог событий (последние 3 дня):\n\n"
    current_day = None
    for event in events:
        if event.day != current_day:
            current_day = event.day
            text += f"📅 День {event.day}:\n"
        text += f"  {event.event_text}\n"
    try:
        await callback.message.edit_text(text, reply_markup=back_button("zs_main"))
    except Exception:
        await callback.message.answer(text, reply_markup=back_button("zs_main"))
