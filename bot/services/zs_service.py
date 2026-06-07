import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models.zombie_survival import ZSPlayer, ZSBase, ZSInventory, ZSNPC, ZSEvent, ZSImage
from services.zs_data import (
    STARTER_EQUIPMENT, NPC_NAMES, get_max_npcs,
    BUILDINGS, DEFENSE_LEVELS, BASE_LEVELS,
    get_workshop_tier, get_backpack_slots, RESOURCES
)

# ─── ИГРОК ───────────────────────────────────────────────────────────────────

async def get_player(session: AsyncSession, telegram_id: int) -> ZSPlayer | None:
    result = await session.execute(
        select(ZSPlayer).where(ZSPlayer.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

async def get_base(session: AsyncSession, telegram_id: int) -> ZSBase | None:
    result = await session.execute(
        select(ZSBase).where(ZSBase.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

async def get_inventory(session: AsyncSession, telegram_id: int) -> ZSInventory | None:
    result = await session.execute(
        select(ZSInventory).where(ZSInventory.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

async def create_player(session: AsyncSession, telegram_id: int, name: str) -> ZSPlayer:
    player = ZSPlayer(telegram_id=telegram_id, name=name)
    base = ZSBase(telegram_id=telegram_id, buildings={}, defense_level=0)
    inventory = ZSInventory(
        telegram_id=telegram_id,
        resources={"food": 5},
        equipment=STARTER_EQUIPMENT.copy()
    )
    session.add(player)
    session.add(base)
    session.add(inventory)
    await session.commit()
    await session.refresh(player)
    return player

async def reset_player(session: AsyncSession, telegram_id: int):
    await session.execute(delete(ZSPlayer).where(ZSPlayer.telegram_id == telegram_id))
    await session.execute(delete(ZSBase).where(ZSBase.telegram_id == telegram_id))
    await session.execute(delete(ZSInventory).where(ZSInventory.telegram_id == telegram_id))
    await session.execute(delete(ZSNPC).where(ZSNPC.telegram_id == telegram_id))
    await session.execute(delete(ZSEvent).where(ZSEvent.telegram_id == telegram_id))
    await session.commit()

# ─── ВРЕМЯ ───────────────────────────────────────────────────────────────────

async def advance_time(session: AsyncSession, player: ZSPlayer, minutes: int):
    player.game_time += minutes
    if player.game_time >= 1440:
        player.game_time -= 1440
        player.day += 1
        await process_new_day(session, player)
    await session.commit()

async def process_new_day(session: AsyncSession, player: ZSPlayer):
    inventory = await get_inventory(session, player.telegram_id)
    base = await get_base(session, player.telegram_id)
    resources = dict(inventory.resources or {})
    buildings = base.buildings or {}

    # Огород — пассивная еда
    garden_level = buildings.get("garden", 0)
    if garden_level > 0:
        food_bonus = [2, 5, 10][garden_level - 1]
        resources["food"] = resources.get("food", 0) + food_bonus

    from sqlalchemy.orm.attributes import flag_modified
    inventory.resources = resources
    flag_modified(inventory, "resources")
    await session.commit()

# ─── ГОЛОД ───────────────────────────────────────────────────────────────────

async def reduce_hunger(session: AsyncSession, player: ZSPlayer, amount: int):
    was_hungry = player.hunger == 0
    player.hunger = max(0, player.hunger - amount)
    if was_hungry:
        player.hp = max(1, player.hp - 10)
    await session.commit()

async def eat_food(session: AsyncSession, player: ZSPlayer, inventory) -> bool:
    resources = dict(inventory.resources or {})
    if resources.get("food", 0) <= 0:
        return False
    resources["food"] -= 1
    if resources["food"] == 0:
        del resources["food"]
    from sqlalchemy.orm.attributes import flag_modified
    inventory.resources = resources
    flag_modified(inventory, "resources")
    player.hunger = min(10, player.hunger + 2)
    await session.commit()
    return True

# ─── РЕСУРСЫ ─────────────────────────────────────────────────────────────────

async def add_resources(session: AsyncSession, inventory: ZSInventory, resources: dict):
    current = dict(inventory.resources or {})
    for res, amount in resources.items():
        current[res] = current.get(res, 0) + amount
    inventory.resources = current
    await session.commit()

async def remove_resources(session: AsyncSession, inventory: ZSInventory, resources: dict) -> dict:
    current = dict(inventory.resources or {})
    for res, amount in resources.items():
        if current.get(res, 0) < amount:
            return {"success": False, "error": f"Недостаточно: {RESOURCES.get(res, {}).get('name', res)}"}
        current[res] -= amount
        if current[res] == 0:
            del current[res]
    inventory.resources = current
    await session.commit()
    return {"success": True}

# ─── ПОСТРОЙКИ ───────────────────────────────────────────────────────────────

async def build(session: AsyncSession, telegram_id: int, build_id: str) -> dict:
    base = await get_base(session, telegram_id)
    inventory = await get_inventory(session, telegram_id)
    player = await get_player(session, telegram_id)
    buildings = dict(base.buildings or {})

    if build_id == "defense":
        current_level = base.defense_level
        if current_level >= len(DEFENSE_LEVELS) - 1:
            return {"success": False, "error": "Защита уже максимального уровня."}
        next_defense = DEFENSE_LEVELS[current_level + 1]
        cost = next_defense["cost"]
        time_cost = next_defense["time"]
    elif build_id in BUILDINGS:
        b_data = BUILDINGS[build_id]
        current_level = buildings.get(build_id, 0)
        if current_level >= len(b_data["levels"]):
            return {"success": False, "error": "Постройка уже максимального уровня."}
        next_level = b_data["levels"][current_level]
        cost = next_level["cost"]
        time_cost = next_level["time"]
    else:
        return {"success": False, "error": "Неизвестная постройка."}

    result = await remove_resources(session, inventory, cost)
    if not result.get("success"):
        return result

    if build_id == "defense":
        base.defense_level += 1
    else:
        buildings[build_id] = buildings.get(build_id, 0) + 1
        if build_id == "shelter":
            level = buildings[build_id]
            hp_bonus = BUILDINGS["shelter"]["levels"][level - 1]["hp_bonus"]
            player.hp_max += hp_bonus
        base.buildings = buildings

    await advance_time(session, player, time_cost)
    return {"success": True}

async def upgrade_base(session: AsyncSession, telegram_id: int) -> dict:
    base = await get_base(session, telegram_id)
    inventory = await get_inventory(session, telegram_id)
    player = await get_player(session, telegram_id)
    next_level = base.level + 1

    if next_level not in BASE_LEVELS:
        return {"success": False, "error": "База уже максимального уровня."}

    requirements = BASE_LEVELS[next_level]
    buildings = base.buildings or {}

    for build_id, required_level in requirements["requirements"].items():
        if buildings.get(build_id, 0) < required_level:
            build_name = BUILDINGS[build_id]["name"]
            return {"success": False, "error": f"Нужно: {build_name} ур.{required_level}"}

    result = await remove_resources(session, inventory, requirements["cost"])
    if not result.get("success"):
        return result

    base.level = next_level
    await session.commit()
    return {"success": True, "level": next_level}

# ─── СНАРЯЖЕНИЕ ──────────────────────────────────────────────────────────────

async def upgrade_equipment(session: AsyncSession, telegram_id: int, slot: str) -> dict:
    from services.zs_data import EQUIPMENT_CHAINS, get_equipment_item
    base = await get_base(session, telegram_id)
    inventory = await get_inventory(session, telegram_id)
    equipment = dict(inventory.equipment or {})
    current_tier = equipment.get(slot, 0)
    chain = EQUIPMENT_CHAINS.get(slot, [])

    if current_tier + 1 >= len(chain):
        return {"success": False, "error": "Снаряжение уже максимального уровня."}

    next_item = chain[current_tier + 1]
    craft_tier = next_item.get("craft_tier", 1)
    workshop_tier = get_workshop_tier(base.buildings or {})

    if craft_tier > workshop_tier:
        return {"success": False, "error": "Нужна более продвинутая мастерская."}

    result = await remove_resources(session, inventory, next_item.get("cost", {}))
    if not result.get("success"):
        return result

    equipment[slot] = current_tier + 1
    inventory.equipment = equipment
    await session.commit()
    return {"success": True, "item": next_item}

# ─── НПС ─────────────────────────────────────────────────────────────────────

async def get_npcs(session: AsyncSession, telegram_id: int) -> list[ZSNPC]:
    result = await session.execute(
        select(ZSNPC).where(ZSNPC.telegram_id == telegram_id, ZSNPC.is_alive == True)
    )
    return result.scalars().all()

async def add_npc(session: AsyncSession, telegram_id: int) -> ZSNPC | None:
    base = await get_base(session, telegram_id)
    npcs = await get_npcs(session, telegram_id)
    max_npcs = get_max_npcs(base.level)

    if len(npcs) >= max_npcs:
        return None

    name = random.choice(NPC_NAMES)
    npc = ZSNPC(telegram_id=telegram_id, name=name)
    session.add(npc)
    await session.commit()
    return npc

async def send_npc_on_mission(session: AsyncSession, npc_id: int, location: str) -> dict:
    result = await session.execute(select(ZSNPC).where(ZSNPC.id == npc_id))
    npc = result.scalar_one_or_none()
    if not npc:
        return {"success": False, "error": "НПС не найден."}
    npc.status = "mission"
    npc.location = location
    await session.commit()
    return {"success": True}

async def return_npcs(session: AsyncSession, player: ZSPlayer):
    from services.zs_data import LOCATIONS, get_npc_level_data, get_npc_exp_needed
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
        level_data = get_npc_level_data(npc.level)
        death_chance = level_data["death_chance"]
        loot_bonus = level_data["loot_bonus"]

        npc.missions_total = (npc.missions_total or 0) + 1

        if random.randint(1, 100) <= death_chance:
            npc.is_alive = False
            died.append(npc.name)
        else:
            npc.missions_survived = (npc.missions_survived or 0) + 1
            npc.exp = (npc.exp or 0) + 1
            leveled_up = False
            if npc.level < 5 and npc.exp >= get_npc_exp_needed(npc.level):
                npc.level += 1
                npc.exp = 0
                leveled_up = True

            resources = {}
            for res_id, res_data in loc.get("resources", {}).items():
                if random.randint(1, 100) <= res_data["chance"] // 2:
                    amount = int(random.randint(1, res_data["max"] // 2 + 1) * loot_bonus)
                    if amount > 0:
                        resources[res_id] = amount
            if resources:
                await add_resources(session, inventory, resources)
            npc.status = "idle"
            npc.location = None
            returned.append({"name": npc.name, "resources": resources, "leveled_up": leveled_up, "level": npc.level})

    await session.commit()
    return {"returned": returned, "died": died}

# ─── НОЧНОЕ НАПАДЕНИЕ ────────────────────────────────────────────────────────

async def night_attack(session: AsyncSession, player: ZSPlayer) -> dict:
    base = await get_base(session, player.telegram_id)
    inventory = await get_inventory(session, player.telegram_id)
    npcs = await get_npcs(session, player.telegram_id)

    npc_count = len(npcs)
    base_damage = 20 + (player.day * 2) + (npc_count * 5)
    defense = DEFENSE_LEVELS[base.defense_level]["damage_reduction"]
    actual_damage = max(5, int(base_damage * (1 - defense / 100)))

    from services.zs_data import get_total_defense
    equip_defense = get_total_defense(inventory.equipment or {})
    actual_damage = max(5, actual_damage - equip_defense // 10)

    player.hp = max(0, player.hp - actual_damage)

    lost_npcs = []
    lost_resources = {}

    if actual_damage > base_damage * 0.7:
        idle_npcs = [n for n in npcs if n.status == "idle"]
        if idle_npcs:
            for npc in idle_npcs:
                if random.randint(1, 100) <= 15:
                    npc.is_alive = False
                    lost_npcs.append(npc.name)

        resources = dict(inventory.resources or {})
        for res_id in list(resources.keys()):
            if random.randint(1, 100) <= 20:
                loss = int(resources[res_id] * random.uniform(0.1, 0.2))
                if loss > 0:
                    resources[res_id] = max(0, resources[res_id] - loss)
                    lost_resources[res_id] = loss
        inventory.resources = resources

    if player.hp <= 0:
        player.is_alive = False

    await session.commit()
    return {
        "damage": actual_damage,
        "lost_npcs": lost_npcs,
        "lost_resources": lost_resources,
        "survived": player.hp > 0,
    }

# ─── СОБЫТИЯ ─────────────────────────────────────────────────────────────────

async def add_event(session: AsyncSession, telegram_id: int, day: int, event_type: str, text: str):
    from models.zombie_survival import ZSEvent
    event = ZSEvent(telegram_id=telegram_id, day=day, event_type=event_type, event_text=text)
    session.add(event)
    await session.commit()

async def get_events(session: AsyncSession, telegram_id: int, current_day: int) -> list:
    from models.zombie_survival import ZSEvent
    from sqlalchemy import select
    min_day = max(1, current_day - 2)
    result = await session.execute(
        select(ZSEvent)
        .where(ZSEvent.telegram_id == telegram_id, ZSEvent.day >= min_day)
        .order_by(ZSEvent.day.desc(), ZSEvent.created_at.desc())
    )
    return result.scalars().all()

# ─── ИЗОБРАЖЕНИЯ ─────────────────────────────────────────────────────────────

async def get_image(session: AsyncSession, key: str) -> ZSImage | None:
    result = await session.execute(
        select(ZSImage).where(ZSImage.key == key)
    )
    return result.scalar_one_or_none()

async def set_image(session: AsyncSession, key: str, file_id: str, added_by: int) -> ZSImage:
    existing = await get_image(session, key)
    if existing:
        existing.file_id = file_id
        await session.commit()
        return existing
    image = ZSImage(key=key, file_id=file_id, added_by=added_by)
    session.add(image)
    await session.commit()
    return image
