from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.game import GamePlayer, GameEvent
from services.game_data import (
    get_internal_distance, get_system_distance, get_location_system,
    LOCATIONS, FUEL_PRICE, REPAIR_PRICE, ENGINES, FUEL_TANKS, HULLS,
    XP_REWARDS, calculate_new_level, get_level_info,
    get_effective_engine_range, get_trade_discount, get_engineer_bonus,
    get_mechanic_repair, SKILL_MAX
)
from services.game_events import generate_event

async def get_player(session: AsyncSession, telegram_id: int) -> GamePlayer | None:
    result = await session.execute(
        select(GamePlayer).where(GamePlayer.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

async def create_player(session: AsyncSession, telegram_id: int) -> GamePlayer:
    player = GamePlayer(telegram_id=telegram_id)
    session.add(player)
    await session.commit()
    await session.refresh(player)
    return player

async def get_or_create_player(session: AsyncSession, telegram_id: int) -> GamePlayer:
    player = await get_player(session, telegram_id)
    if not player:
        player = await create_player(session, telegram_id)
    return player

async def add_xp(session: AsyncSession, player: GamePlayer, xp: int) -> int:
    old_xp = player.xp
    player.xp += xp
    levels_gained = calculate_new_level(old_xp, player.xp)
    if levels_gained > 0:
        player.level += levels_gained
        player.skill_points += levels_gained * 2
    await session.commit()
    return levels_gained

async def fly_to(session: AsyncSession, player: GamePlayer, destination: str) -> dict:
    current_system = get_location_system(player.location)
    dest_system = get_location_system(destination)
    effective_range = get_effective_engine_range(player)

    if current_system == dest_system:
        distance = get_internal_distance(player.location, destination)
        is_jump = False
    else:
        distance = get_system_distance(current_system, dest_system)
        is_jump = True

    if not distance:
        return {"success": False, "error": "Маршрут не существует."}
    if is_jump and distance > effective_range:
        return {"success": False, "error": f"Двигатель не поддерживает такую дальность. Нужен range {distance}, у тебя {effective_range}."}
    if distance > player.fuel:
        return {"success": False, "error": f"Недостаточно топлива. Нужно {distance}, у тебя {player.fuel}."}

    event = generate_event(destination)

    player.fuel -= distance
    player.location = destination
    player.total_jumps += 1
    player.mined_location = None
    player.explored_location = None

    player.credits = max(0, player.credits + event.credits_delta)
    player.fuel = max(0, min(player.fuel + event.fuel_delta, player.fuel_tank))

    hull_bonus, damage_reduction = get_engineer_bonus(player)
    actual_hull_delta = event.hull_delta
    if actual_hull_delta < 0:
        actual_hull_delta = int(actual_hull_delta * (1 - damage_reduction))
    player.hull = max(0, min(player.hull + actual_hull_delta, player.hull_max))

    game_event = GameEvent(
        telegram_id=player.telegram_id,
        event_type=event.event_type,
        event_text=event.text,
        location=destination,
        credits_delta=event.credits_delta,
        fuel_delta=event.fuel_delta,
        hull_delta=actual_hull_delta,
    )
    session.add(game_event)

    xp_reward = XP_REWARDS.get(event.event_type, 0)
    levels_gained = await add_xp(session, player, xp_reward)
    await session.commit()

    return {
        "success": True,
        "event": event,
        "fuel_spent": distance,
        "is_jump": is_jump,
        "is_dead": player.hull <= 0,
        "xp_gained": xp_reward,
        "levels_gained": levels_gained,
        "player": player,
    }

async def refuel(session: AsyncSession, player: GamePlayer, amount: int) -> dict:
    location = LOCATIONS.get(player.location, {})
    if not location.get("has_hangar"):
        return {"success": False, "error": "Здесь нет ангара."}

    max_refuel = player.fuel_tank - player.fuel
    amount = min(amount, max_refuel)
    if amount <= 0:
        return {"success": False, "error": "Бак уже полный."}

    discount = get_trade_discount(player)
    price_per_unit = int(FUEL_PRICE * (1 - discount))
    cost = amount * price_per_unit

    if cost > player.credits:
        affordable = player.credits // price_per_unit
        if affordable <= 0:
            return {"success": False, "error": "Недостаточно кредитов для заправки."}
        amount = affordable
        cost = amount * price_per_unit

    player.fuel += amount
    player.credits -= cost
    await session.commit()
    return {"success": True, "amount": amount, "cost": cost}

async def repair(session: AsyncSession, player: GamePlayer, amount: int) -> dict:
    location = LOCATIONS.get(player.location, {})
    if not location.get("has_hangar"):
        return {"success": False, "error": "Здесь нет ангара."}

    max_repair = player.hull_max - player.hull
    amount = min(amount, max_repair)
    if amount <= 0:
        return {"success": False, "error": "Корпус уже в норме."}

    discount = get_trade_discount(player)
    price_per_unit = int(REPAIR_PRICE * (1 - discount))
    cost = amount * price_per_unit

    if cost > player.credits:
        affordable = player.credits // price_per_unit
        if affordable <= 0:
            return {"success": False, "error": "Недостаточно кредитов для ремонта."}
        amount = affordable
        cost = amount * price_per_unit

    player.hull += amount
    player.credits -= cost
    await session.commit()
    return {"success": True, "amount": amount, "cost": cost}

async def self_repair(session: AsyncSession, player: GamePlayer) -> dict:
    repair_amount = get_mechanic_repair(player)
    if repair_amount <= 0:
        return {"success": False, "error": "Нет навыка механика."}
    if player.fuel < 1:
        return {"success": False, "error": "Недостаточно топлива для ремонта."}
    max_repair = player.hull_max - player.hull
    if max_repair <= 0:
        return {"success": False, "error": "Корпус уже в норме."}

    actual_repair = min(repair_amount, max_repair)
    player.hull += actual_repair
    player.fuel -= 1
    await session.commit()
    return {"success": True, "amount": actual_repair}

async def buy_upgrade(session: AsyncSession, player: GamePlayer, upgrade_type: str, upgrade_name: str) -> dict:
    location = LOCATIONS.get(player.location, {})
    if not location.get("has_shop"):
        return {"success": False, "error": "Здесь нет магазина."}

    discount = get_trade_discount(player)

    if upgrade_type == "engine":
        upgrade = ENGINES.get(upgrade_name)
        if not upgrade:
            return {"success": False, "error": "Двигатель не найден."}
        price = int(upgrade["price"] * (1 - discount))
        if price > player.credits:
            return {"success": False, "error": f"Недостаточно кредитов. Нужно {price}."}
        player.credits -= price
        player.engine_range = upgrade["range"]

    elif upgrade_type == "fuel_tank":
        upgrade = FUEL_TANKS.get(upgrade_name)
        if not upgrade:
            return {"success": False, "error": "Топливный бак не найден."}
        price = int(upgrade["price"] * (1 - discount))
        if price > player.credits:
            return {"success": False, "error": f"Недостаточно кредитов. Нужно {price}."}
        player.credits -= price
        player.fuel_tank = upgrade["capacity"]
        if player.fuel > player.fuel_tank:
            player.fuel = player.fuel_tank

    elif upgrade_type == "hull":
        upgrade = HULLS.get(upgrade_name)
        if not upgrade:
            return {"success": False, "error": "Корпус не найден."}
        price = int(upgrade["price"] * (1 - discount))
        if price > player.credits:
            return {"success": False, "error": f"Недостаточно кредитов. Нужно {price}."}
        player.credits -= price
        player.hull_max = upgrade["hp"]
        player.hull = upgrade["hp"]

    else:
        return {"success": False, "error": "Неизвестный тип улучшения."}

    await session.commit()
    return {"success": True, "upgrade": upgrade}

async def spend_skill_point(session: AsyncSession, player: GamePlayer, skill: str) -> dict:
    if player.skill_points <= 0:
        return {"success": False, "error": "Нет доступных очков характеристик."}

    skill_map = {
        "trade": "skill_trade",
        "engineer": "skill_engineer",
        "mechanic": "skill_mechanic",
        "pilot": "skill_pilot",
    }
    attr = skill_map.get(skill)
    if not attr:
        return {"success": False, "error": "Неизвестная характеристика."}

    current = getattr(player, attr)
    if current >= SKILL_MAX:
        return {"success": False, "error": f"Характеристика уже на максимуме ({SKILL_MAX})."}

    setattr(player, attr, current + 1)
    player.skill_points -= 1
    await session.commit()
    return {"success": True, "skill": skill, "value": current + 1}

async def get_player_events(session: AsyncSession, telegram_id: int, limit: int = 5) -> list[GameEvent]:
    result = await session.execute(
        select(GameEvent)
        .where(GameEvent.telegram_id == telegram_id)
        .order_by(GameEvent.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()

async def evacuate(session: AsyncSession, player: GamePlayer) -> dict:
    from services.game_data import get_nearest_station, get_location_system, can_evacuate
    if not can_evacuate(player):
        return {"success": False, "error": "Эвакуация недоступна."}

    cost = int(player.credits * 0.6)
    if player.credits < 200:
        return {"success": False, "error": "Недостаточно кредитов. Минимум 200 cr."}

    current_system = get_location_system(player.location)
    station = get_nearest_station(current_system)
    if not station:
        return {"success": False, "error": "Нет доступных станций в системе."}

    player.credits -= cost
    player.location = station
    player.fuel = player.fuel_tank
    player.mined_location = None
    player.explored_location = None
    await session.commit()

    return {"success": True, "cost": cost, "station": station}

async def reset_player(session: AsyncSession, player: GamePlayer) -> GamePlayer:
    player.credits = 500
    player.fuel = 12
    player.hull = 100
    player.hull_max = 100
    player.fuel_tank = 12
    player.engine_range = 6
    player.cargo_used = 0
    player.cargo_max = 10
    player.ship_name = "Shuttle MK-1"
    player.location = "K-9 Hub"
    player.total_jumps = 0
    player.mined_location = None
    player.explored_location = None
    player.xp = 0
    player.level = 1
    player.skill_points = 0
    player.skill_trade = 0
    player.skill_engineer = 0
    player.skill_mechanic = 0
    player.skill_pilot = 0
    await session.commit()
    return player
