from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.game import GamePlayer, GameEvent
from services.game_data import get_distance, get_reachable_locations, LOCATIONS, FUEL_PRICE, REPAIR_PRICE, ENGINES, FUEL_TANKS, HULLS
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

async def fly_to(session: AsyncSession, player: GamePlayer, destination: str) -> dict:
    distance = get_distance(player.location, destination)
    if not distance:
        return {"success": False, "error": "Маршрут не существует."}

    if distance > player.engine_range:
        return {"success": False, "error": f"Двигатель не поддерживает такую дальность. Нужен range {distance}, у тебя {player.engine_range}."}

    if distance > player.fuel:
        return {"success": False, "error": f"Недостаточно топлива. Нужно {distance}, у тебя {player.fuel}."}

    event = generate_event(destination)

    player.fuel -= distance
    player.location = destination
    player.total_jumps += 1

    new_credits = player.credits + event.credits_delta
    player.credits = max(0, new_credits)

    new_fuel = player.fuel + event.fuel_delta
    player.fuel = max(0, min(new_fuel, player.fuel_tank))

    new_hull = player.hull + event.hull_delta
    player.hull = max(0, min(new_hull, player.hull_max))

    game_event = GameEvent(
        telegram_id=player.telegram_id,
        event_type=event.event_type,
        event_text=event.text,
        location=destination,
        credits_delta=event.credits_delta,
        fuel_delta=event.fuel_delta,
        hull_delta=event.hull_delta,
    )
    session.add(game_event)
    await session.commit()

    return {
        "success": True,
        "event": event,
        "fuel_spent": distance,
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

    cost = amount * FUEL_PRICE
    if cost > player.credits:
        affordable = player.credits // FUEL_PRICE
        if affordable <= 0:
            return {"success": False, "error": "Недостаточно кредитов для заправки."}
        amount = affordable
        cost = amount * FUEL_PRICE

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

    cost = amount * REPAIR_PRICE
    if cost > player.credits:
        affordable = player.credits // REPAIR_PRICE
        if affordable <= 0:
            return {"success": False, "error": "Недостаточно кредитов для ремонта."}
        amount = affordable
        cost = amount * REPAIR_PRICE

    player.hull += amount
    player.credits -= cost
    await session.commit()

    return {"success": True, "amount": amount, "cost": cost}

async def buy_upgrade(session: AsyncSession, player: GamePlayer, upgrade_type: str, upgrade_name: str) -> dict:
    location = LOCATIONS.get(player.location, {})
    if not location.get("has_shop"):
        return {"success": False, "error": "Здесь нет магазина."}

    if upgrade_type == "engine":
        upgrade = ENGINES.get(upgrade_name)
        if not upgrade:
            return {"success": False, "error": "Двигатель не найден."}
        if upgrade["price"] > player.credits:
            return {"success": False, "error": f"Недостаточно кредитов. Нужно {upgrade['price']}."}
        player.credits -= upgrade["price"]
        player.engine_range = upgrade["range"]

    elif upgrade_type == "fuel_tank":
        upgrade = FUEL_TANKS.get(upgrade_name)
        if not upgrade:
            return {"success": False, "error": "Топливный бак не найден."}
        if upgrade["price"] > player.credits:
            return {"success": False, "error": f"Недостаточно кредитов. Нужно {upgrade['price']}."}
        player.credits -= upgrade["price"]
        player.fuel_tank = upgrade["capacity"]
        if player.fuel > player.fuel_tank:
            player.fuel = player.fuel_tank

    elif upgrade_type == "hull":
        upgrade = HULLS.get(upgrade_name)
        if not upgrade:
            return {"success": False, "error": "Корпус не найден."}
        if upgrade["price"] > player.credits:
            return {"success": False, "error": f"Недостаточно кредитов. Нужно {upgrade['price']}."}
        player.credits -= upgrade["price"]
        player.hull_max = upgrade["hp"]
        player.hull = upgrade["hp"]

    else:
        return {"success": False, "error": "Неизвестный тип улучшения."}

    await session.commit()
    return {"success": True, "upgrade": upgrade}

async def get_player_events(session: AsyncSession, telegram_id: int, limit: int = 5) -> list[GameEvent]:
    result = await session.execute(
        select(GameEvent)
        .where(GameEvent.telegram_id == telegram_id)
        .order_by(GameEvent.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()

async def emergency_refuel(session: AsyncSession, player: GamePlayer) -> dict:
    EMERGENCY_FUEL_AMOUNT = 3
    EMERGENCY_FUEL_PRICE = 50

    cost = EMERGENCY_FUEL_AMOUNT * EMERGENCY_FUEL_PRICE

    if player.credits < cost:
        return {"success": False, "error": f"Недостаточно кредитов. Аварийная заправка стоит {cost} cr."}

    player.fuel += EMERGENCY_FUEL_AMOUNT
    player.credits -= cost
    await session.commit()

    return {"success": True, "amount": EMERGENCY_FUEL_AMOUNT, "cost": cost}

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
    await session.commit()
    return player
