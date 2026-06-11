import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models.zombie_survival import ZSPlayer, ZSBase, ZSInventory, ZSNPC, ZSEvent
from services.zs_data import (
    RESOURCES, CLASSES, LOCATIONS, EQUIPMENT, BUILDINGS,
    NPC_LEVELS, get_npc_level_data, get_npc_exp_needed,
    get_horde_stats, NIGHT_ATTACK_CHANCE
)

NPC_NAMES = [
    "Андрей", "Мария", "Олег", "Наталья", "Дмитрий", "Ирина",
    "Сергей", "Анна", "Виктор", "Елена", "Павел", "Оксана",
    "Алексей", "Юлия", "Максим", "Татьяна", "Роман", "Светлана",
    "Денис", "Людмила", "Артём", "Вера", "Евгений", "Надежда",
]

# ─── ИГРОК ────────────────────────────────────────────────────────────────────

async def get_player(session: AsyncSession, telegram_id: int) -> ZSPlayer | None:
    result = await session.execute(select(ZSPlayer).where(ZSPlayer.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def create_player(session: AsyncSession, telegram_id: int, name: str, player_class: str) -> ZSPlayer:
    class_data = CLASSES.get(player_class, CLASSES["soldier"])
    hp_max = 100 + class_data["hp_bonus"]
    player = ZSPlayer(
        telegram_id=telegram_id,
        name=name,
        hp=hp_max,
        hp_max=hp_max,
        hunger=10,
        day=1,
        game_time=360,
        player_class=player_class,
        is_alive=True,
    )
    session.add(player)
    base = ZSBase(telegram_id=telegram_id)
    session.add(base)
    inventory = ZSInventory(
        telegram_id=telegram_id,
        resources={"food": 5},
        equipment={},
    )
    session.add(inventory)
    await session.commit()
    return player

async def delete_player(session: AsyncSession, telegram_id: int):
    await session.execute(delete(ZSPlayer).where(ZSPlayer.telegram_id == telegram_id))
    await session.execute(delete(ZSBase).where(ZSBase.telegram_id == telegram_id))
    await session.execute(delete(ZSInventory).where(ZSInventory.telegram_id == telegram_id))
    await session.execute(delete(ZSNPC).where(ZSNPC.telegram_id == telegram_id))
    await session.execute(delete(ZSEvent).where(ZSEvent.telegram_id == telegram_id))
    await session.commit()

# ─── БАЗА ─────────────────────────────────────────────────────────────────────

async def get_base(session: AsyncSession, telegram_id: int) -> ZSBase | None:
    result = await session.execute(select(ZSBase).where(ZSBase.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def get_max_npcs(base: ZSBase) -> int:
    shelter_level = base.shelter or 0
    if shelter_level == 0:
        return 0
    return BUILDINGS["shelter"]["levels"][shelter_level]["npc_slots"]

async def upgrade_building(session: AsyncSession, base: ZSBase, inventory: ZSInventory, building: str) -> tuple[bool, str]:
    current_level = getattr(base, building, 0)
    if current_level >= 5:
        return False, "Максимальный уровень!"
    next_level = current_level + 1
    cost = BUILDINGS[building]["levels"][next_level]["cost"]
    resources = dict(inventory.resources or {})

    # Проверяем ресурсы
    for res, amount in cost.items():
        if resources.get(res, 0) < amount:
            res_name = RESOURCES[res]["name"]
            return False, f"Недостаточно {res_name}: нужно {amount}, есть {resources.get(res, 0)}"

    # Списываем ресурсы
    for res, amount in cost.items():
        resources[res] = resources.get(res, 0) - amount
    inventory.resources = resources
    setattr(base, building, next_level)
    await session.commit()
    return True, f"✅ {BUILDINGS[building]['name']} улучшена до уровня {next_level}!"

# ─── ИНВЕНТАРЬ ────────────────────────────────────────────────────────────────

async def get_inventory(session: AsyncSession, telegram_id: int) -> ZSInventory | None:
    result = await session.execute(select(ZSInventory).where(ZSInventory.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def add_resources(session: AsyncSession, inventory: ZSInventory, resources: dict):
    current = dict(inventory.resources or {})
    for res, amount in resources.items():
        current[res] = current.get(res, 0) + amount
    inventory.resources = current
    await session.commit()

async def get_player_defense(inventory: ZSInventory) -> int:
    defense = 0
    defense += EQUIPMENT["helmet"]["tiers"][inventory.helmet_tier or 0]["defense"]
    defense += EQUIPMENT["armor"]["tiers"][inventory.armor_tier or 0]["defense"]
    defense += EQUIPMENT["pants"]["tiers"][inventory.pants_tier or 0]["defense"]
    defense += EQUIPMENT["boots"]["tiers"][inventory.boots_tier or 0]["defense"]
    return defense

async def get_player_melee_damage(inventory: ZSInventory, player: ZSPlayer) -> int:
    base_damage = EQUIPMENT["melee"]["tiers"][inventory.melee_tier or 0]["damage"]
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])
    return int(base_damage * class_data["damage_bonus"])

async def get_player_ranged_damage(inventory: ZSInventory, player: ZSPlayer) -> int:
    base_damage = EQUIPMENT["ranged"]["tiers"][inventory.ranged_tier or 0]["damage"]
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])
    return int(base_damage * class_data["damage_bonus"])

async def craft_equipment(session: AsyncSession, inventory: ZSInventory, player: ZSPlayer, base: ZSBase, slot: str, tier: int) -> tuple[bool, str]:
    if tier < 1 or tier > 5:
        return False, "Неверный тир!"
    current_tier = getattr(inventory, f"{slot}_tier", 0)
    if tier <= current_tier:
        return False, "У тебя уже есть снаряжение этого или лучшего тира!"

    # Проверяем мастерскую
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])
    workshop_level = base.workshop or 0
    required_workshop = tier
    if class_data.get("can_craft_t3_without_workshop") and tier <= 3:
        required_workshop = 0
    if workshop_level < required_workshop:
        return False, f"Нужна мастерская уровня {required_workshop}!"

    tier_data = EQUIPMENT[slot]["tiers"][tier]
    cost = dict(tier_data.get("craft", {}))

    # Скидка для учёного
    if class_data["craft_discount"] < 1.0:
        cost = {res: max(1, int(amount * class_data["craft_discount"])) for res, amount in cost.items()}

    resources = dict(inventory.resources or {})
    for res, amount in cost.items():
        if resources.get(res, 0) < amount:
            res_name = RESOURCES[res]["name"]
            return False, f"Недостаточно {res_name}: нужно {amount}, есть {resources.get(res, 0)}"

    for res, amount in cost.items():
        resources[res] = resources.get(res, 0) - amount
    inventory.resources = resources
    setattr(inventory, f"{slot}_tier", tier)
    await session.commit()
    return True, f"✅ {EQUIPMENT[slot]['tiers'][tier]['name']} скрафтен!"

# ─── ГОЛОД ────────────────────────────────────────────────────────────────────

async def reduce_hunger(session: AsyncSession, player: ZSPlayer, amount: int):
    was_hungry = player.hunger == 0
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])
    if class_data.get("slow_hunger"):
        amount = max(1, amount - 1)
    player.hunger = max(0, player.hunger - amount)
    if was_hungry:
        player.hp = max(1, player.hp - 10)
    await session.commit()

async def eat_food(session: AsyncSession, player: ZSPlayer, inventory: ZSInventory) -> bool:
    resources = dict(inventory.resources or {})
    if resources.get("food", 0) <= 0:
        return False
    resources["food"] = resources["food"] - 1
    inventory.resources = resources
    player.hunger = min(10, player.hunger + 2)
    await session.commit()
    return True

async def use_meds(session: AsyncSession, player: ZSPlayer, inventory: ZSInventory) -> bool:
    resources = dict(inventory.resources or {})
    if resources.get("meds", 0) <= 0:
        return False
    resources["meds"] = resources["meds"] - 1
    inventory.resources = resources
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])
    heal = int(20 * class_data["med_bonus"])
    player.hp = min(player.hp_max, player.hp + heal)
    await session.commit()
    return True

# ─── СОБЫТИЯ ──────────────────────────────────────────────────────────────────

async def add_event(session: AsyncSession, telegram_id: int, day: int, event_type: str, text: str):
    event = ZSEvent(telegram_id=telegram_id, day=day, event_type=event_type, event_text=text)
    session.add(event)
    # Удаляем события старше 3 дней
    old_day = day - 3
    if old_day > 0:
        await session.execute(delete(ZSEvent).where(
            ZSEvent.telegram_id == telegram_id,
            ZSEvent.day < old_day
        ))
    await session.commit()

async def get_events(session: AsyncSession, telegram_id: int, days: int = 3) -> list:
    result = await session.execute(
        select(ZSEvent).where(ZSEvent.telegram_id == telegram_id)
        .order_by(ZSEvent.created_at.desc()).limit(20)
    )
    return result.scalars().all()

# ─── НПС ──────────────────────────────────────────────────────────────────────

async def get_npcs(session: AsyncSession, telegram_id: int) -> list:
    result = await session.execute(
        select(ZSNPC).where(ZSNPC.telegram_id == telegram_id, ZSNPC.is_alive == True)
    )
    return result.scalars().all()

async def create_npc(session: AsyncSession, telegram_id: int) -> ZSNPC:
    name = random.choice(NPC_NAMES)
    npc = ZSNPC(
        telegram_id=telegram_id,
        name=name,
        status="idle",
        level=1,
        exp=0,
        hp=50,
        hp_max=50,
        hunger=10,
        weapon_tier=0,
        armor_tier=0,
        is_alive=True,
    )
    session.add(npc)
    await session.commit()
    return npc

async def feed_npc(session: AsyncSession, npc: ZSNPC, inventory: ZSInventory) -> bool:
    resources = dict(inventory.resources or {})
    if resources.get("food", 0) <= 0:
        return False
    resources["food"] = resources["food"] - 1
    inventory.resources = resources
    npc.hunger = min(10, npc.hunger + 2)
    await session.commit()
    return True

async def send_npc_on_mission(session: AsyncSession, npc: ZSNPC, location_id: str):
    npc.status = "mission"
    npc.location = location_id
    loc = LOCATIONS[location_id]
    npc.hunger = max(0, npc.hunger - loc["tier"])
    await session.commit()

async def return_npcs(session: AsyncSession, player: ZSPlayer) -> dict:
    result = await session.execute(
        select(ZSNPC).where(
            ZSNPC.telegram_id == player.telegram_id,
            ZSNPC.status == "mission",
            ZSNPC.is_alive == True
        )
    )
    npcs = result.scalars().all()
    inventory = await get_inventory(session, player.telegram_id)
    returned = []
    died = []

    for npc in npcs:
        loc = LOCATIONS.get(npc.location, {})
        tier = loc.get("tier", 1)
        level_data = get_npc_level_data(npc.level)
        loot_bonus = level_data["loot_bonus"]

        npc.missions_total = (npc.missions_total or 0) + 1

        # Бой НПС с зомби
        zombie_hp_range = loc.get("zombie_hp", (25, 40))
        zombie_damage_range = loc.get("zombie_damage", (8, 15))
        zombie_hp = random.randint(*zombie_hp_range)
        zombie_damage = random.randint(*zombie_damage_range)

        npc_weapon_damage = EQUIPMENT["melee"]["tiers"][npc.weapon_tier or 0]["damage"]
        npc_armor_defense = EQUIPMENT["armor"]["tiers"][npc.armor_tier or 0]["defense"]

        npc_hp = npc.hp
        rounds = 0
        survived = True
        while zombie_hp > 0 and npc_hp > 0 and rounds < 20:
            zombie_hp -= npc_weapon_damage
            if zombie_hp > 0:
                damage = max(1, zombie_damage - npc_armor_defense)
                npc_hp -= damage
            rounds += 1

        if npc_hp <= 0:
            npc.is_alive = False
            died.append(npc.name)
            continue

        npc.hp = min(npc.hp_max, npc_hp)
        npc.missions_survived = (npc.missions_survived or 0) + 1
        npc.exp = (npc.exp or 0) + 1
        leveled_up = False
        if npc.level < 5 and npc.exp >= get_npc_exp_needed(npc.level):
            npc.level += 1
            npc.exp = 0
            leveled_up = True
            level_data = get_npc_level_data(npc.level)
            npc.hp_max = level_data["hp"]
            npc.hp = npc.hp_max

        # Лут
        resources = {}
        for res_id, res_data in loc.get("resources", {}).items():
            if random.randint(1, 100) <= res_data["chance"] // 2:
                amount = int(random.randint(1, res_data["max"] // 2 + 1) * loot_bonus)
                if amount > 0:
                    resources[res_id] = amount

        if resources and inventory:
            await add_resources(session, inventory, resources)

        npc.status = "idle"
        npc.location = None
        returned.append({
            "name": npc.name,
            "resources": resources,
            "leveled_up": leveled_up,
            "level": npc.level
        })

    await session.commit()
    return {"returned": returned, "died": died}

# ─── ВЫЛАЗКА ──────────────────────────────────────────────────────────────────

async def get_random_scenario(session: AsyncSession, location_id: str) -> dict | None:
    from sqlalchemy import text
    result = await session.execute(
        text("SELECT id, intro_text FROM zs_location_scenarios WHERE location_id = :loc ORDER BY RANDOM() LIMIT 1"),
        {"loc": location_id}
    )
    row = result.fetchone()
    if not row:
        return None
    scenario_id, intro_text = row
    opts = await session.execute(
        text("SELECT option_type, button_text, action_text, result_type FROM zs_scenario_options WHERE scenario_id = :sid"),
        {"sid": scenario_id}
    )
    options = [{"type": r[0], "button": r[1], "text": r[2], "result": r[3]} for r in opts.fetchall()]
    return {"intro": intro_text, "options": options}

async def start_raid(session: AsyncSession, player: ZSPlayer, inventory: ZSInventory, location_id: str) -> dict:
    loc = LOCATIONS[location_id]
    tier = loc["tier"]
    await reduce_hunger(session, player, tier)
    scenario = await get_random_scenario(session, location_id)
    return {"scenario": scenario, "location": loc, "location_id": location_id}

async def process_raid_option(session: AsyncSession, player: ZSPlayer, inventory: ZSInventory, base: ZSBase, location_id: str, option: dict) -> dict:
    loc = LOCATIONS[location_id]
    tier = loc["tier"]
    result_type = option["result"]
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])

    if result_type == "leave":
        player.hunger = min(10, player.hunger + 1)
        await session.commit()
        return {"type": "leave", "text": option["text"]}

    if result_type == "npc":
        # Проверяем место на базе
        npcs = await get_npcs(session, player.telegram_id)
        max_npcs = await get_max_npcs(base)
        has_space = len(npcs) < max_npcs

        loot_chances = {1: 70, 2: 55, 3: 40}
        loot_chance = loot_chances.get(tier, 70)
        give_loot = random.randint(1, 100) <= loot_chance

        resources = {}
        if give_loot or not has_space:
            if give_loot:
                for res_id, res_data in loc["resources"].items():
                    if random.randint(1, 100) <= res_data["chance"] // 2:
                        amount = random.randint(1, res_data["max"] // 2 + 1)
                        if amount > 0:
                            resources[res_id] = amount
                if resources:
                    await add_resources(session, inventory, resources)

        npc = None
        if has_space:
            npc = await create_npc(session, player.telegram_id)

        return {"type": "npc", "text": option["text"], "npc": npc, "resources": resources, "has_space": has_space}

    if result_type == "fight":
        zombie_hp = random.randint(*loc["zombie_hp"])
        zombie_damage = random.randint(*loc["zombie_damage"])
        return {
            "type": "fight",
            "text": option["text"],
            "zombie_hp": zombie_hp,
            "zombie_damage": zombie_damage,
            "zombie_hp_max": zombie_hp,
            "location_id": location_id,
            "is_combat_loot": True,
        }

    if result_type == "loot":
        fight_chances = {1: 20, 2: 30, 3: 40}
        fight_chance = fight_chances.get(tier, 20)

        roll = random.randint(1, 100)
        if roll <= fight_chance:
            zombie_hp = random.randint(*loc["zombie_hp"])
            zombie_damage = random.randint(*loc["zombie_damage"])
            return {
                "type": "fight",
                "text": "Ты ищешь лут но натыкаешься на зомби!",
                "zombie_hp": zombie_hp,
                "zombie_damage": zombie_damage,
                "zombie_hp_max": zombie_hp,
                "location_id": location_id,
                "is_combat_loot": True,
            }
        else:
            resources = {}
            loot_bonus = class_data["loot_bonus"]
            for res_id, res_data in loc["resources"].items():
                if random.randint(1, 100) <= res_data["chance"]:
                    amount = int(random.randint(1, res_data["max"]) * loot_bonus)
                    if amount > 0:
                        resources[res_id] = amount
            if resources:
                await add_resources(session, inventory, resources)
            return {"type": "loot", "text": option["text"], "resources": resources}

    return {"type": "empty", "text": option["text"]}

async def process_combat_victory(session: AsyncSession, player: ZSPlayer, inventory: ZSInventory, location_id: str, is_combat_loot: bool = False) -> dict:
    loc = LOCATIONS[location_id]
    class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])
    resources = {}
    loot_bonus = class_data["loot_bonus"] * (1.3 if is_combat_loot else 1.0)
    for res_id, res_data in loc["resources"].items():
        if random.randint(1, 100) <= res_data["chance"]:
            amount = int(random.randint(1, res_data["max"]) * loot_bonus)
            if amount > 0:
                resources[res_id] = amount
    if resources:
        await add_resources(session, inventory, resources)
    return resources

# ─── НОЧЬ ─────────────────────────────────────────────────────────────────────

async def process_night(session: AsyncSession, player: ZSPlayer, base: ZSBase, inventory: ZSInventory) -> dict:
    result = {}

    # Огород
    garden_level = base.garden or 0
    if garden_level > 0:
        food_amount = BUILDINGS["garden"]["levels"][garden_level]["food_per_day"]
        await add_resources(session, inventory, {"food": food_amount})
        result["garden_food"] = food_amount

    # Медпункт
    medpost_level = base.medpost or 0
    if medpost_level > 0:
        heal = BUILDINGS["medpost"]["levels"][medpost_level]["heal_per_day"]
        class_data = CLASSES.get(player.player_class or "soldier", CLASSES["soldier"])
        heal = int(heal * class_data["med_bonus"])
        old_hp = player.hp
        player.hp = min(player.hp_max, player.hp + heal)
        result["medpost_heal"] = player.hp - old_hp

    # Голод
    await reduce_hunger(session, player, 1)

    # Новый день
    player.day += 1
    player.game_time = 360
    await session.commit()

    # Нападение орды
    attacked = random.randint(1, 100) <= NIGHT_ATTACK_CHANCE
    if attacked:
        horde_stats = get_horde_stats(player.day - 1)
        zombie_hp = random.randint(*horde_stats["hp"])
        zombie_damage = random.randint(*horde_stats["damage"])
        result["attacked"] = True
        result["zombie_hp"] = zombie_hp
        result["zombie_damage"] = zombie_damage
        result["zombie_hp_max"] = zombie_hp
    else:
        result["attacked"] = False

    return result
