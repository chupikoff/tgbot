# Звёздные системы и локации
LOCATIONS = {
    "K-9 Hub": {
        "name": "K-9 Hub",
        "system": "KALYPSO",
        "type": "station",
        "description": "Небольшая торговая станция на краю системы Калипсо. Здесь всегда найдётся работа.",
        "has_hangar": True,
        "has_shop": True,
    },
    "Haven": {
        "name": "Haven",
        "system": "KALYPSO",
        "type": "planet",
        "description": "Обитаемая планета. Тихое место, но торговля идёт бойко.",
        "has_hangar": True,
        "has_shop": True,
    },
    "Dust-9": {
        "name": "Dust-9",
        "system": "KALYPSO",
        "type": "uninhabited",
        "description": "Необитаемая планета покрытая пылью. Говорят здесь можно найти кое-что интересное.",
        "has_hangar": False,
        "has_shop": False,
    },
    "Helion Prime": {
        "name": "Helion Prime",
        "system": "HELION",
        "type": "planet",
        "description": "Промышленная планета. Опасный район, но прибыльный.",
        "has_hangar": True,
        "has_shop": True,
    },
    "Helion Station": {
        "name": "Helion Station",
        "system": "HELION",
        "type": "station",
        "description": "Старая военная станция, теперь используется торговцами.",
        "has_hangar": True,
        "has_shop": True,
    },
    "Void-3": {
        "name": "Void-3",
        "system": "HELION",
        "type": "uninhabited",
        "description": "Тёмная планета на краю системы. Сканеры показывают странные сигналы.",
        "has_hangar": False,
        "has_shop": False,
    },
    "Nexus Gate": {
        "name": "Nexus Gate",
        "system": "NEXUS",
        "type": "station",
        "description": "Пиратская станция. Здесь нет законов, но есть всё что нужно.",
        "has_hangar": True,
        "has_shop": True,
    },
    "Nexus Prime": {
        "name": "Nexus Prime",
        "system": "NEXUS",
        "type": "planet",
        "description": "Пограничная планета. Фронтир. Только сильные выживают здесь.",
        "has_hangar": True,
        "has_shop": True,
    },
    "Shard": {
        "name": "Shard",
        "system": "NEXUS",
        "type": "uninhabited",
        "description": "Обломки древней планеты. Астероидное поле полное опасностей и возможностей.",
        "has_hangar": False,
        "has_shop": False,
    },
}

# Маршруты между локациями (расстояние в парсеках)
ROUTES = {
    ("K-9 Hub", "Haven"): 2,
    ("K-9 Hub", "Dust-9"): 4,
    ("Haven", "Dust-9"): 3,
    ("K-9 Hub", "Helion Station"): 6,
    ("Haven", "Helion Prime"): 7,
    ("Dust-9", "Void-3"): 5,
    ("Helion Station", "Helion Prime"): 2,
    ("Helion Station", "Void-3"): 3,
    ("Helion Prime", "Void-3"): 4,
    ("Helion Station", "Nexus Gate"): 8,
    ("Helion Prime", "Nexus Prime"): 9,
    ("Void-3", "Shard"): 6,
    ("Nexus Gate", "Nexus Prime"): 2,
    ("Nexus Gate", "Shard"): 4,
    ("Nexus Prime", "Shard"): 3,
}

def get_distance(from_loc: str, to_loc: str) -> int | None:
    distance = ROUTES.get((from_loc, to_loc)) or ROUTES.get((to_loc, from_loc))
    return distance

def get_reachable_locations(current: str, engine_range: int, fuel: int) -> list:
    result = []
    for (a, b), dist in ROUTES.items():
        if a == current or b == current:
            destination = b if a == current else a
            can_reach = dist <= engine_range and dist <= fuel
            result.append({
                "name": destination,
                "distance": dist,
                "fuel_cost": dist,
                "can_reach": can_reach,
                "location": LOCATIONS.get(destination, {}),
            })
    result.sort(key=lambda x: x["distance"])
    return result

# Улучшения двигателей
ENGINES = {
    "Civilian I": {"range": 6, "price": 0, "description": "Стандартный двигатель"},
    "Vector II": {"range": 10, "price": 800, "description": "Улучшенный двигатель"},
    "Longhaul III": {"range": 16, "price": 2000, "description": "Дальнобойный двигатель"},
}

# Улучшения топливных баков
FUEL_TANKS = {
    "Standard Tank": {"capacity": 12, "price": 0, "description": "Стандартный бак"},
    "Extended Tank": {"capacity": 20, "price": 600, "description": "Расширенный бак"},
    "Heavy Tank": {"capacity": 30, "price": 1500, "description": "Тяжёлый бак"},
}

# Улучшения корпуса
HULLS = {
    "Light Frame": {"hp": 100, "price": 0, "description": "Стандартный корпус"},
    "Reinforced Frame": {"hp": 150, "price": 700, "description": "Усиленный корпус"},
    "Heavy Armor": {"hp": 250, "price": 1800, "description": "Тяжёлая броня"},
}

# Цены на топливо и ремонт
FUEL_PRICE = 15
REPAIR_PRICE = 8
