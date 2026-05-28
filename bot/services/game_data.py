# Звёздные системы
SYSTEMS = {
    "KALYPSO": {
        "name": "KALYPSO",
        "description": "Стартовая система. Относительно безопасный район.",
        "locations": ["K-9 Hub", "Haven", "Dust-9", "Abandoned Post", "Training Hub"],
    },
    "HELION": {
        "name": "HELION",
        "description": "Промышленная система. Более опасный район.",
        "locations": ["Helion Station", "Helion Prime", "Void-3"],
    },
    "NEXUS": {
        "name": "NEXUS",
        "description": "Пограничная система. Пираты и возможности.",
        "locations": ["Nexus Gate", "Nexus Prime", "Shard"],
    },
}

# Маршруты между системами
SYSTEM_ROUTES = {
    ("KALYPSO", "HELION"): 6,
    ("HELION", "NEXUS"): 8,
    ("KALYPSO", "NEXUS"): 14,
}

# Локации
LOCATIONS = {
    "K-9 Hub": {
        "name": "K-9 Hub",
        "system": "KALYPSO",
        "type": "station",
        "description": "Небольшая торговая станция на краю системы Калипсо.",
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
        "description": "Необитаемая планета покрытая пылью.",
        "has_hangar": False,
        "has_shop": False,
    },
    "Abandoned Post": {
        "name": "Abandoned Post",
        "system": "KALYPSO",
        "type": "abandoned",
        "description": "Заброшенная станция на краю системы. Здесь давно никого не было.",
        "has_hangar": False,
        "has_shop": False,
    },
    "Training Hub": {
        "name": "Training Hub",
        "system": "KALYPSO",
        "type": "training",
        "description": "Учебная станция. Здесь можно пройти тренировки за кредиты.",
        "has_hangar": True,
        "has_shop": False,
    },
    "Helion Station": {
        "name": "Helion Station",
        "system": "HELION",
        "type": "station",
        "description": "Старая военная станция, теперь используется торговцами.",
        "has_hangar": True,
        "has_shop": True,
    },
    "Helion Prime": {
        "name": "Helion Prime",
        "system": "HELION",
        "type": "planet",
        "description": "Промышленная планета. Опасный район, но прибыльный.",
        "has_hangar": True,
        "has_shop": True,
    },
    "Void-3": {
        "name": "Void-3",
        "system": "HELION",
        "type": "uninhabited",
        "description": "Тёмная планета на краю системы.",
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
        "description": "Пограничная планета. Фронтир.",
        "has_hangar": True,
        "has_shop": True,
    },
    "Shard": {
        "name": "Shard",
        "system": "NEXUS",
        "type": "uninhabited",
        "description": "Обломки древней планеты. Астероидное поле.",
        "has_hangar": False,
        "has_shop": False,
    },
}

# Внутрисистемные маршруты
INTERNAL_ROUTES = {
    ("K-9 Hub", "Haven"): 2,
    ("K-9 Hub", "Dust-9"): 4,
    ("K-9 Hub", "Abandoned Post"): 3,
    ("K-9 Hub", "Training Hub"): 2,
    ("Haven", "Dust-9"): 3,
    ("Haven", "Abandoned Post"): 4,
    ("Haven", "Training Hub"): 3,
    ("Dust-9", "Abandoned Post"): 5,
    ("Dust-9", "Training Hub"): 4,
    ("Abandoned Post", "Training Hub"): 2,
    ("Helion Station", "Helion Prime"): 2,
    ("Helion Station", "Void-3"): 3,
    ("Helion Prime", "Void-3"): 4,
    ("Nexus Gate", "Nexus Prime"): 2,
    ("Nexus Gate", "Shard"): 4,
    ("Nexus Prime", "Shard"): 3,
}

def get_location_system(location: str) -> str:
    return LOCATIONS.get(location, {}).get("system", "")

def get_internal_distance(from_loc: str, to_loc: str) -> int | None:
    return INTERNAL_ROUTES.get((from_loc, to_loc)) or INTERNAL_ROUTES.get((to_loc, from_loc))

def get_system_distance(from_system: str, to_system: str) -> int | None:
    return SYSTEM_ROUTES.get((from_system, to_system)) or SYSTEM_ROUTES.get((to_system, from_system))

def get_reachable_locations(current: str, engine_range: int, fuel: int) -> dict:
    current_system = get_location_system(current)
    result = {"internal": [], "systems": []}

    for loc_name, loc_data in LOCATIONS.items():
        if loc_data["system"] != current_system or loc_name == current:
            continue
        dist = get_internal_distance(current, loc_name)
        if dist:
            result["internal"].append({
                "name": loc_name,
                "distance": dist,
                "fuel_cost": dist,
                "can_reach": dist <= fuel,
                "location": loc_data,
            })

    result["internal"].sort(key=lambda x: x["distance"])

    for system_name, system_data in SYSTEMS.items():
        if system_name == current_system:
            continue
        dist = get_system_distance(current_system, system_name)
        if dist:
            can_reach = dist <= fuel and dist <= engine_range
            result["systems"].append({
                "name": system_name,
                "distance": dist,
                "fuel_cost": dist,
                "can_reach": can_reach,
                "system": system_data,
            })

    result["systems"].sort(key=lambda x: x["distance"])
    return result

# Улучшения
ENGINES = {
    "Civilian I":   {"range": 6,  "price": 0,    "description": "Стандартный двигатель"},
    "Vector II":    {"range": 10, "price": 800,  "description": "Улучшенный двигатель"},
    "Longhaul III": {"range": 16, "price": 2000, "description": "Дальнобойный двигатель"},
}

FUEL_TANKS = {
    "Standard Tank": {"capacity": 12, "price": 0,    "description": "Стандартный бак"},
    "Extended Tank": {"capacity": 20, "price": 600,  "description": "Расширенный бак"},
    "Heavy Tank":    {"capacity": 30, "price": 1500, "description": "Тяжёлый бак"},
}

HULLS = {
    "Light Frame":     {"hp": 100, "price": 0,    "description": "Стандартный корпус"},
    "Reinforced Frame":{"hp": 150, "price": 700,  "description": "Усиленный корпус"},
    "Heavy Armor":     {"hp": 250, "price": 1800, "description": "Тяжёлая броня"},
}

FUEL_PRICE = 15
REPAIR_PRICE = 8

# Добыча
MINING_DATA = {
    "Dust-9": {
        "fuel_cost": 1,
        "danger": "low",
        "rewards": [
            {"weight": 40, "credits": 0,   "hull": 0,   "text": "🪨 Пустая порода. Ничего ценного не найдено."},
            {"weight": 35, "credits": 80,  "hull": 0,   "text": "⛏ Найдены залежи минералов. Небольшой улов."},
            {"weight": 15, "credits": 150, "hull": 0,   "text": "💎 Редкие кристаллы! Хорошая находка."},
            {"weight": 8,  "credits": 50,  "hull": -10, "text": "💥 Обвал породы! Корабль повреждён, но кое-что нашёл."},
            {"weight": 2,  "credits": 300, "hull": 0,   "text": "🌟 Богатое месторождение! Отличный день."},
        ]
    },
    "Void-3": {
        "fuel_cost": 1,
        "danger": "medium",
        "rewards": [
            {"weight": 30, "credits": 0,   "hull": 0,   "text": "🌑 Планета мертва. Здесь нет ничего ценного."},
            {"weight": 30, "credits": 120, "hull": 0,   "text": "⛏ Редкие металлы в коре планеты. Неплохо."},
            {"weight": 20, "credits": 200, "hull": 0,   "text": "💎 Ценные соединения! Хорошая добыча."},
            {"weight": 12, "credits": 80,  "hull": -20, "text": "☢️ Радиоактивная зона! Корпус повреждён, но добыча есть."},
            {"weight": 8,  "credits": 400, "hull": 0,   "text": "🌟 Богатые залежи экзотических металлов!"},
        ]
    },
    "Shard": {
        "fuel_cost": 1,
        "danger": "high",
        "rewards": [
            {"weight": 20, "credits": 0,   "hull": -15, "text": "☄️ Астероиды! Корабль повреждён, ничего не найдено."},
            {"weight": 25, "credits": 150, "hull": 0,   "text": "⛏ Обломки старых кораблей. Есть что продать."},
            {"weight": 25, "credits": 250, "hull": 0,   "text": "💎 Древние артефакты в обломках. Ценная находка."},
            {"weight": 20, "credits": 100, "hull": -25, "text": "💥 Столкновение с астероидом! Серьёзные повреждения, но добыча есть."},
            {"weight": 10, "credits": 600, "hull": 0,   "text": "🌟 Джекпот! Древний корабль с нетронутым грузом."},
        ]
    },
}

def get_mining_result(location: str) -> dict | None:
    import random
    data = MINING_DATA.get(location)
    if not data:
        return None
    rewards = data["rewards"]
    weights = [r["weight"] for r in rewards]
    result = random.choices(rewards, weights=weights)[0]
    return {
        "fuel_cost": data["fuel_cost"],
        "credits": result["credits"],
        "hull": result["hull"],
        "text": result["text"],
    }

# Уровни и звания
LEVELS = [
    {"level": 1,  "xp": 0,    "title": "🔰 Новобранец"},
    {"level": 2,  "xp": 100,  "title": "⭐ Курсант"},
    {"level": 3,  "xp": 250,  "title": "⭐ Пилот"},
    {"level": 4,  "xp": 500,  "title": "⭐⭐ Опытный пилот"},
    {"level": 5,  "xp": 900,  "title": "⭐⭐ Ветеран"},
    {"level": 6,  "xp": 1400, "title": "⭐⭐⭐ Скиталец"},
    {"level": 7,  "xp": 2000, "title": "⭐⭐⭐ Следопыт"},
    {"level": 8,  "xp": 2800, "title": "🌟 Ас"},
    {"level": 9,  "xp": 3800, "title": "🌟 Легенда"},
    {"level": 10, "xp": 5000, "title": "💫 Призрак"},
]

XP_REWARDS = {
    "find":      5,
    "signal":    3,
    "danger":    8,
    "strange":   2,
    "technical": 2,
    "empty":     0,
    "mining":    5,
}

SKILL_MAX = 5

def get_level_info(xp: int) -> dict:
    current = LEVELS[0]
    for lvl in LEVELS:
        if xp >= lvl["xp"]:
            current = lvl
        else:
            break
    next_lvl = next((l for l in LEVELS if l["level"] == current["level"] + 1), None)
    return {
        "level": current["level"],
        "title": current["title"],
        "xp": xp,
        "xp_current": current["xp"],
        "xp_next": next_lvl["xp"] if next_lvl else None,
    }

def calculate_new_level(old_xp: int, new_xp: int) -> int:
    old_level = get_level_info(old_xp)["level"]
    new_level = get_level_info(new_xp)["level"]
    return new_level - old_level

def get_effective_engine_range(player) -> int:
    return player.engine_range + player.skill_pilot

def get_trade_discount(player) -> float:
    return player.skill_trade * 0.05

def get_engineer_bonus(player) -> tuple:
    hull_bonus = player.skill_engineer * 0.10
    damage_reduction = player.skill_engineer * 0.05
    return hull_bonus, damage_reduction

def get_mechanic_repair(player) -> int:
    return player.skill_mechanic * 5

def get_nearest_station(system: str) -> str:
    for loc_name, loc_data in LOCATIONS.items():
        if loc_data["system"] == system and loc_data["type"] == "station":
            return loc_name
    return None

def get_min_fuel_needed(location: str) -> int:
    min_dist = None
    for (a, b), dist in INTERNAL_ROUTES.items():
        if a == location or b == location:
            if min_dist is None or dist < min_dist:
                min_dist = dist
    return min_dist or 999

def can_evacuate(player) -> bool:
    location = LOCATIONS.get(player.location, {})
    if location.get("has_hangar"):
        return False
    if player.credits < 200:
        return False
    min_fuel = get_min_fuel_needed(player.location)
    return player.fuel < min_fuel

# Тренировки
TRAINING_OPTIONS = [
    {"xp": 10, "cost": 50,  "label": "Базовая тренировка — 50 cr = 10 XP"},
    {"xp": 25, "cost": 100, "label": "Продвинутая тренировка — 100 cr = 25 XP"},
    {"xp": 75, "cost": 250, "label": "Интенсив — 250 cr = 75 XP"},
]

# Сценарии заброшенной станции
ABANDONED_SCENARIOS = [
    {
        "id": "survivor",
        "intro": "На станции мигает аварийный свет. Где-то в глубине слышен слабый звук.",
        "choices": [
            {"id": "enter", "label": "🔦 Войти внутрь",           "next": "survivor_enter"},
            {"id": "scan",  "label": "📡 Просканировать снаружи", "next": "survivor_scan"},
            {"id": "leave", "label": "🚀 Улететь",                "next": "leave"},
        ],
        "scenes": {
            "survivor_enter": {
                "text": "В коридоре находишь выжившего пилота. Он ранен и еле дышит.",
                "choices": [
                    {"id": "help",  "label": "💊 Помочь выжившему", "next": "survivor_help"},
                    {"id": "leave", "label": "🚀 Уйти",             "next": "leave"},
                ],
            },
            "survivor_scan": {
                "text": "Сканер фиксирует слабые признаки жизни в глубине станции.",
                "choices": [
                    {"id": "enter", "label": "🔦 Войти за выжившим", "next": "survivor_help"},
                    {"id": "leave", "label": "🚀 Улететь",           "next": "leave"},
                ],
            },
            "survivor_help": {
                "text": "Ты помогаешь пилоту добраться до своего корабля. В благодарность он отдаёт всё что у него есть.",
                "result": {"credits": 200, "hull": -5, "xp": 15},
                "final": True,
            },
            "leave": {
                "text": "Ты улетаешь. Может оно и к лучшему.",
                "result": {"credits": 0, "hull": 0, "xp": 0},
                "final": True,
            },
        },
    },
    {
        "id": "warehouse",
        "intro": "Станция мертва. Только темнота и тишина. Но сканер показывает что-то интересное внутри.",
        "choices": [
            {"id": "enter", "label": "🔦 Войти внутрь",           "next": "warehouse_enter"},
            {"id": "scan",  "label": "📡 Просканировать снаружи", "next": "warehouse_scan"},
            {"id": "leave", "label": "🚀 Улететь",                "next": "leave"},
        ],
        "scenes": {
            "warehouse_enter": {
                "text": "В трюме находишь запертый склад. Замок старый но прочный.",
                "choices": [
                    {"id": "break", "label": "🔨 Взломать замок", "next": "warehouse_break"},
                    {"id": "leave", "label": "🚀 Уйти",           "next": "leave"},
                ],
            },
            "warehouse_scan": {
                "text": "Сканер фиксирует энергосигнал в трюме. Там что-то есть.",
                "choices": [
                    {"id": "enter", "label": "🔦 Войти в трюм", "next": "warehouse_loot"},
                    {"id": "leave", "label": "🚀 Улететь",      "next": "leave"},
                ],
            },
            "warehouse_break": {
                "text": "Замок поддался, но сорвавшаяся крышка задела корпус. Внутри — ящики с товарами.",
                "result": {"credits": 150, "hull": -10, "xp": 10},
                "final": True,
            },
            "warehouse_loot": {
                "text": "В трюме находишь нетронутый груз. Повезло — без повреждений.",
                "result": {"credits": 150, "hull": 0, "xp": 10},
                "final": True,
            },
            "leave": {
                "text": "Ты улетаешь. Может оно и к лучшему.",
                "result": {"credits": 0, "hull": 0, "xp": 0},
                "final": True,
            },
        },
    },
    {
        "id": "trap",
        "intro": "Станция выглядит нетронутой. Слишком нетронутой. Что-то здесь не так.",
        "choices": [
            {"id": "enter", "label": "🔦 Войти внутрь",           "next": "trap_enter"},
            {"id": "scan",  "label": "📡 Просканировать снаружи", "next": "trap_scan"},
            {"id": "leave", "label": "🚀 Улететь",                "next": "leave"},
        ],
        "scenes": {
            "trap_enter": {
                "text": "Засада! Пираты ждали внутри. Деваться некуда — только драться.",
                "choices": [
                    {"id": "fight", "label": "⚔️ Сражаться",          "next": "trap_fight"},
                    {"id": "run",   "label": "🏃 Бежать к кораблю",   "next": "trap_run"},
                ],
            },
            "trap_scan": {
                "text": "Сканер засёк скрытые энергосигналы — оружие и скафандры. Засада!",
                "choices": [
                    {"id": "attack", "label": "⚔️ Атаковать первым", "next": "trap_attack"},
                    {"id": "leave",  "label": "🚀 Улететь",          "next": "leave"},
                ],
            },
            "trap_fight": {
                "text": "Тяжёлый бой. Ты победил но корабль серьёзно повреждён. Зато добыча хорошая.",
                "result": {"credits": 300, "hull": -20, "xp": 20},
                "final": True,
            },
            "trap_run": {
                "text": "Удалось вырваться, но пираты успели выстрелить вслед.",
                "result": {"credits": 0, "hull": -5, "xp": 5},
                "final": True,
            },
            "trap_attack": {
                "text": "Внезапная атака застала пиратов врасплох. Победа с минимальными потерями!",
                "result": {"credits": 300, "hull": -10, "xp": 20},
                "final": True,
            },
            "leave": {
                "text": "Ты улетаешь. Правильное решение.",
                "result": {"credits": 0, "hull": 0, "xp": 0},
                "final": True,
            },
        },
    },
]
