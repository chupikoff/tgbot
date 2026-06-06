# ─── ВРЕМЯ ───────────────────────────────────────────────────────────────────
DAY_START = 360   # 06:00
DAY_END = 1320    # 22:00
TOTAL_DAYS = 30

def is_daytime(game_time: int) -> bool:
    return DAY_START <= game_time < DAY_END

def format_time(game_time: int) -> str:
    hours = (game_time % 1440) // 60
    minutes = game_time % 60
    return f"{hours:02d}:{minutes:02d}"

# ─── РЕСУРСЫ ─────────────────────────────────────────────────────────────────
RESOURCES = {
    # Тир 1
    "wood":        {"name": "🪵 Дерево",        "tier": 1},
    "cloth":       {"name": "🧵 Ткань",          "tier": 1},
    "food":        {"name": "🥫 Еда",            "tier": 1},
    "scrap":       {"name": "🔩 Металлолом",     "tier": 1},
    "plastic":     {"name": "🧪 Пластик",        "tier": 1},
    "rubber":      {"name": "🧲 Резина",         "tier": 1},
    # Тир 2
    "leather":     {"name": "🧴 Кожа",           "tier": 2},
    "electronics": {"name": "⚡ Электроника",    "tier": 2},
    "meds":        {"name": "💊 Медикаменты",    "tier": 2},
    "fuel":        {"name": "⛽ Топливо",        "tier": 2},
    "ammo":        {"name": "🔋 Боеприпасы",     "tier": 2},
    # Тир 3
    "kevlar":      {"name": "🛡 Кевлар",         "tier": 3},
    "rare_metals": {"name": "💎 Редкие металлы", "tier": 3},
    "optics":      {"name": "🔭 Оптика",         "tier": 3},
}

# ─── ЛОКАЦИИ ─────────────────────────────────────────────────────────────────
LOCATIONS = {
    "residential": {
        "name": "🏙 Жилые кварталы",
        "tier": 1,
        "time_cost": 120,
        "zombie_chance": 30,
        "zombie_hp": (20, 35),
        "zombie_damage": (8, 12),
        "max_zombies": 1,
        "resources": {
            "wood":    {"chance": 70, "min": 1, "max": 4},
            "cloth":   {"chance": 65, "min": 1, "max": 4},
            "food":    {"chance": 75, "min": 1, "max": 5},
            "plastic": {"chance": 40, "min": 1, "max": 3},
            "rubber":  {"chance": 30, "min": 1, "max": 2},
        },
        "loot": [
            {"slot": "helmet",  "tier": 1, "chance": 15},
            {"slot": "backpack","tier": 1, "chance": 10},
            {"slot": "melee",   "tier": 1, "chance": 10},
        ],
        "npc_chance": 10,
    },
    "school": {
        "name": "🏫 Школа",
        "tier": 1,
        "time_cost": 120,
        "zombie_chance": 30,
        "zombie_hp": (20, 35),
        "zombie_damage": (8, 12),
        "max_zombies": 1,
        "resources": {
            "wood":    {"chance": 65, "min": 1, "max": 4},
            "cloth":   {"chance": 55, "min": 1, "max": 3},
            "scrap":   {"chance": 60, "min": 1, "max": 4},
            "plastic": {"chance": 50, "min": 1, "max": 3},
        },
        "loot": [
            {"slot": "melee",   "tier": 1, "chance": 20},
            {"slot": "backpack","tier": 1, "chance": 15},
            {"slot": "helmet",  "tier": 1, "chance": 15},
        ],
        "npc_chance": 10,
    },
    "supermarket": {
        "name": "🏪 Супермаркет",
        "tier": 1,
        "time_cost": 120,
        "zombie_chance": 30,
        "zombie_hp": (20, 35),
        "zombie_damage": (8, 12),
        "max_zombies": 1,
        "resources": {
            "food":    {"chance": 80, "min": 2, "max": 6},
            "cloth":   {"chance": 60, "min": 1, "max": 3},
            "plastic": {"chance": 55, "min": 1, "max": 4},
            "rubber":  {"chance": 45, "min": 1, "max": 3},
        },
        "loot": [
            {"slot": "backpack","tier": 1, "chance": 20},
            {"slot": "ranged",  "tier": 1, "chance": 10},
        ],
        "npc_chance": 10,
    },
    "hospital": {
        "name": "🏥 Больница",
        "tier": 2,
        "time_cost": 240,
        "zombie_chance": 60,
        "zombie_hp": (50, 80),
        "zombie_damage": (15, 25),
        "max_zombies": 2,
        "resources": {
            "meds":        {"chance": 70, "min": 1, "max": 4},
            "cloth":       {"chance": 50, "min": 1, "max": 3},
            "plastic":     {"chance": 45, "min": 1, "max": 3},
            "electronics": {"chance": 30, "min": 1, "max": 2},
            "leather":     {"chance": 25, "min": 1, "max": 2},
        },
        "loot": [
            {"slot": "melee",  "tier": 1, "chance": 15},
            {"slot": "helmet", "tier": 1, "chance": 10},
            {"slot": "ranged", "tier": 1, "chance": 10},
        ],
        "npc_chance": 15,
    },
    "factory": {
        "name": "🏭 Завод",
        "tier": 2,
        "time_cost": 240,
        "zombie_chance": 60,
        "zombie_hp": (50, 80),
        "zombie_damage": (15, 25),
        "max_zombies": 2,
        "resources": {
            "scrap":       {"chance": 75, "min": 2, "max": 5},
            "rubber":      {"chance": 60, "min": 1, "max": 4},
            "fuel":        {"chance": 45, "min": 1, "max": 3},
            "electronics": {"chance": 35, "min": 1, "max": 2},
            "leather":     {"chance": 30, "min": 1, "max": 2},
        },
        "loot": [
            {"slot": "melee",  "tier": 1, "chance": 15},
            {"slot": "ranged", "tier": 1, "chance": 10},
            {"slot": "helmet", "tier": 1, "chance": 10},
        ],
        "npc_chance": 15,
    },
    "police": {
        "name": "🚔 Полицейский участок",
        "tier": 3,
        "time_cost": 360,
        "zombie_chance": 85,
        "zombie_hp": (100, 150),
        "zombie_damage": (25, 40),
        "max_zombies": 3,
        "resources": {
            "ammo":        {"chance": 65, "min": 1, "max": 4},
            "fuel":        {"chance": 50, "min": 1, "max": 3},
            "kevlar":      {"chance": 20, "min": 1, "max": 2},
            "electronics": {"chance": 30, "min": 1, "max": 2},
        },
        "loot": [
            {"slot": "ranged", "tier": 1, "chance": 15},
            {"slot": "armor",  "tier": 1, "chance": 12},
            {"slot": "helmet", "tier": 1, "chance": 12},
        ],
        "npc_chance": 20,
    },
    "bank": {
        "name": "🏦 Банк",
        "tier": 3,
        "time_cost": 360,
        "zombie_chance": 85,
        "zombie_hp": (100, 150),
        "zombie_damage": (25, 40),
        "max_zombies": 3,
        "resources": {
            "rare_metals": {"chance": 35, "min": 1, "max": 2},
            "electronics": {"chance": 50, "min": 1, "max": 3},
            "optics":      {"chance": 20, "min": 1, "max": 1},
            "kevlar":      {"chance": 25, "min": 1, "max": 2},
            "ammo":        {"chance": 40, "min": 1, "max": 3},
        },
        "loot": [
            {"slot": "ranged", "tier": 1, "chance": 10},
            {"slot": "melee",  "tier": 1, "chance": 10},
            {"slot": "armor",  "tier": 1, "chance": 10},
        ],
        "npc_chance": 20,
    },
}

# ─── ПОСТРОЙКИ ───────────────────────────────────────────────────────────────
BUILDINGS = {
    "shelter": {
        "name": "🏠 Убежище",
        "description": "Увеличивает максимальный HP",
        "levels": [
            {"cost": {"wood": 5, "cloth": 5},                      "time": 60,  "hp_bonus": 20},
            {"cost": {"wood": 10, "scrap": 8, "leather": 5},       "time": 120, "hp_bonus": 40},
            {"cost": {"scrap": 15, "leather": 10, "meds": 5},      "time": 240, "hp_bonus": 60},
        ]
    },
    "workshop": {
        "name": "🔧 Мастерская",
        "description": "Открывает крафт и улучшение снаряжения",
        "levels": [
            {"cost": {"wood": 8, "scrap": 5},                              "time": 120, "craft_tier": 3},
            {"cost": {"scrap": 12, "electronics": 8, "rubber": 5},         "time": 240, "craft_tier": 5},
            {"cost": {"electronics": 10, "rare_metals": 5, "fuel": 5},     "time": 480, "craft_tier": 8},
        ]
    },
    "garden": {
        "name": "🌱 Огород",
        "description": "Пассивное производство еды каждый день",
        "levels": [
            {"cost": {"wood": 5, "cloth": 5, "food": 3},           "time": 60,  "food_per_day": 2},
            {"cost": {"wood": 10, "plastic": 8, "cloth": 5},       "time": 120, "food_per_day": 5},
            {"cost": {"plastic": 10, "electronics": 5, "meds": 3}, "time": 180, "food_per_day": 10},
        ]
    },
    "medpost": {
        "name": "🏥 Медпункт",
        "description": "Восстанавливает HP за ночной отдых",
        "levels": [
            {"cost": {"cloth": 5, "meds": 5},                              "time": 60,  "heal_bonus": 10},
            {"cost": {"plastic": 8, "meds": 8, "electronics": 5},          "time": 120, "heal_bonus": 25},
            {"cost": {"electronics": 8, "meds": 10, "rare_metals": 3},     "time": 240, "heal_bonus": 50},
        ]
    },
    "watchtower": {
        "name": "🔭 Наблюдательная вышка",
        "description": "Даёт информацию о локациях перед вылазкой",
        "levels": [
            {"cost": {"wood": 8, "scrap": 5},                              "time": 120},
            {"cost": {"scrap": 10, "electronics": 8, "optics": 2},         "time": 180},
            {"cost": {"electronics": 10, "optics": 5, "rare_metals": 3},   "time": 300},
        ]
    },
}

# ─── ЗАЩИТА ──────────────────────────────────────────────────────────────────
DEFENSE_LEVELS = [
    {"name": "Нет защиты",          "damage_reduction": 0,   "cost": {},                                           "time": 0},
    {"name": "🪵 Деревянный забор", "damage_reduction": 10,  "cost": {"wood": 20},                                 "time": 60},
    {"name": "🚧 Баррикады",        "damage_reduction": 25,  "cost": {"wood": 15, "scrap": 15},                    "time": 120},
    {"name": "💡 Прожекторы",       "damage_reduction": 40,  "cost": {"scrap": 20, "electronics": 15, "fuel": 10}, "time": 180},
    {"name": "🔫 Сторожевая вышка", "damage_reduction": 60,  "cost": {"scrap": 25, "ammo": 15, "kevlar": 10},      "time": 240},
    {"name": "🧱 Каменная стена",   "damage_reduction": 80,  "cost": {"rare_metals": 15, "kevlar": 15, "optics": 5}, "time": 360},
]

# ─── УРОВНИ БАЗЫ ─────────────────────────────────────────────────────────────
BASE_LEVELS = {
    2: {
        "requirements": {"shelter": 1, "workshop": 1},
        "cost": {"wood": 20, "scrap": 10},
        "max_npcs": 4,
    },
    3: {
        "requirements": {"shelter": 2, "workshop": 2, "medpost": 1},
        "cost": {"scrap": 20, "electronics": 10, "leather": 10},
        "max_npcs": 6,
    },
    4: {
        "requirements": {"shelter": 3, "workshop": 3, "medpost": 2, "watchtower": 1},
        "cost": {"scrap": 30, "electronics": 20, "fuel": 10},
        "max_npcs": 8,
    },
    5: {
        "requirements": {"shelter": 3, "workshop": 3, "medpost": 3, "watchtower": 3, "garden": 3},
        "cost": {"rare_metals": 10, "kevlar": 10, "electronics": 30},
        "max_npcs": 10,
    },
}

def get_max_npcs(base_level: int) -> int:
    npcs = {1: 2, 2: 4, 3: 6, 4: 8, 5: 10}
    return npcs.get(base_level, 2)

# ─── СНАРЯЖЕНИЕ ──────────────────────────────────────────────────────────────
EQUIPMENT_CHAINS = {
    "helmet": [
        {"name": "Нет шлема",              "defense": 0,  "craft_tier": 0, "cost": {}},
        {"name": "Бандана",                "defense": 2,  "craft_tier": 1, "cost": {"cloth": 3}},
        {"name": "Мотоциклетный шлем",     "defense": 5,  "craft_tier": 2, "cost": {"cloth": 5, "plastic": 3}},
        {"name": "Строительная каска",     "defense": 10, "craft_tier": 3, "cost": {"plastic": 5, "scrap": 3}},
        {"name": "Усиленная каска",        "defense": 15, "craft_tier": 4, "cost": {"scrap": 10, "leather": 5}},
        {"name": "Военная каска",          "defense": 22, "craft_tier": 5, "cost": {"scrap": 15, "kevlar": 5}},
        {"name": "Баллистический шлем",    "defense": 30, "craft_tier": 6, "cost": {"kevlar": 10, "rare_metals": 5}},
        {"name": "Тактический шлем",       "defense": 40, "craft_tier": 7, "cost": {"kevlar": 15, "rare_metals": 8, "electronics": 5}},
    ],
    "armor": [
        {"name": "Кожанка",                "defense": 5,  "craft_tier": 0, "cost": {}},
        {"name": "Усиленная кожанка",      "defense": 10, "craft_tier": 1, "cost": {"leather": 5}},
        {"name": "Самодельный жилет",      "defense": 18, "craft_tier": 2, "cost": {"scrap": 8, "cloth": 5}},
        {"name": "Противоударный жилет",   "defense": 25, "craft_tier": 3, "cost": {"scrap": 12, "plastic": 8}},
        {"name": "Самодельный бронежилет", "defense": 35, "craft_tier": 4, "cost": {"scrap": 15, "kevlar": 8}},
        {"name": "Бронежилет",             "defense": 45, "craft_tier": 5, "cost": {"kevlar": 15, "rare_metals": 5}},
        {"name": "Тактический бронежилет", "defense": 58, "craft_tier": 6, "cost": {"kevlar": 20, "rare_metals": 10}},
        {"name": "Полный тактический доспех","defense": 75,"craft_tier": 7, "cost": {"kevlar": 25, "rare_metals": 15, "electronics": 10}},
    ],
    "pants": [
        {"name": "Джинсы",                   "defense": 2,  "craft_tier": 0, "cost": {}},
        {"name": "Усиленные джинсы",         "defense": 5,  "craft_tier": 1, "cost": {"cloth": 5}},
        {"name": "Карго штаны",              "defense": 10, "craft_tier": 2, "cost": {"cloth": 8, "scrap": 3}},
        {"name": "Тактические штаны",        "defense": 15, "craft_tier": 3, "cost": {"scrap": 8, "plastic": 5}},
        {"name": "Усиленные тактические",    "defense": 22, "craft_tier": 4, "cost": {"scrap": 12, "kevlar": 5}},
        {"name": "Бронированные штаны",      "defense": 30, "craft_tier": 5, "cost": {"kevlar": 10, "rare_metals": 5}},
        {"name": "Тактические бронированные","defense": 40, "craft_tier": 6, "cost": {"kevlar": 15, "rare_metals": 8}},
        {"name": "Боевые бронированные",     "defense": 52, "craft_tier": 7, "cost": {"kevlar": 20, "rare_metals": 12, "electronics": 5}},
    ],
    "boots": [
        {"name": "Кроссовки",           "defense": 1,  "craft_tier": 0, "cost": {}},
        {"name": "Усиленные кроссовки", "defense": 3,  "craft_tier": 1, "cost": {"cloth": 3, "leather": 3}},
        {"name": "Рабочие ботинки",     "defense": 6,  "craft_tier": 2, "cost": {"leather": 8, "scrap": 3}},
        {"name": "Берцы",               "defense": 10, "craft_tier": 3, "cost": {"leather": 10, "scrap": 5, "plastic": 3}},
        {"name": "Усиленные берцы",     "defense": 15, "craft_tier": 4, "cost": {"leather": 12, "scrap": 10}},
        {"name": "Тактические берцы",   "defense": 20, "craft_tier": 5, "cost": {"scrap": 15, "rare_metals": 5}},
        {"name": "Военные ботинки",     "defense": 28, "craft_tier": 6, "cost": {"rare_metals": 8, "kevlar": 5}},
        {"name": "Штурмовые ботинки",   "defense": 38, "craft_tier": 7, "cost": {"rare_metals": 12, "kevlar": 8, "electronics": 5}},
    ],
    "melee": [
        {"name": "Кулаки",              "damage": 5,   "craft_tier": 0, "cost": {}},
        {"name": "Дубина",              "damage": 12,  "craft_tier": 1, "cost": {"wood": 5}},
        {"name": "Дубина с гвоздями",   "damage": 20,  "craft_tier": 2, "cost": {"wood": 5, "scrap": 5}},
        {"name": "Бита с шипами",       "damage": 30,  "craft_tier": 3, "cost": {"scrap": 10}},
        {"name": "Мачете",              "damage": 42,  "craft_tier": 4, "cost": {"scrap": 15, "leather": 5}},
        {"name": "Топор",               "damage": 55,  "craft_tier": 5, "cost": {"scrap": 20, "rare_metals": 5}},
        {"name": "Боевой топор",        "damage": 70,  "craft_tier": 6, "cost": {"rare_metals": 12}},
        {"name": "Тактический томагавк","damage": 88,  "craft_tier": 7, "cost": {"rare_metals": 18, "electronics": 5}},
    ],
    "ranged": [
        {"name": "Нет оружия",             "damage": 0,   "ammo_cost": 0, "craft_tier": 0, "cost": {}},
        {"name": "Рогатка",                "damage": 8,   "ammo_cost": 0, "craft_tier": 1, "cost": {"wood": 3, "rubber": 3}},
        {"name": "Арбалет",                "damage": 20,  "ammo_cost": 0, "craft_tier": 2, "cost": {"wood": 10, "scrap": 8}},
        {"name": "Самодельный пистолет",   "damage": 35,  "ammo_cost": 1, "craft_tier": 3, "cost": {"scrap": 15, "electronics": 5}},
        {"name": "Пистолет",               "damage": 50,  "ammo_cost": 1, "craft_tier": 4, "cost": {"scrap": 20, "electronics": 10}},
        {"name": "Обрез",                  "damage": 70,  "ammo_cost": 2, "craft_tier": 5, "cost": {"scrap": 25, "rare_metals": 8}},
        {"name": "Дробовик",               "damage": 90,  "ammo_cost": 2, "craft_tier": 6, "cost": {"rare_metals": 15, "electronics": 10}},
        {"name": "Снайперская винтовка",   "damage": 120, "ammo_cost": 1, "craft_tier": 7, "cost": {"rare_metals": 20, "electronics": 15, "optics": 5}},
    ],
    "backpack": [
        {"name": "Нет рюкзака",         "slots": 5,  "craft_tier": 0, "cost": {}},
        {"name": "Пакет",               "slots": 8,  "craft_tier": 1, "cost": {"cloth": 3}},
        {"name": "Школьный рюкзак",     "slots": 12, "craft_tier": 2, "cost": {"cloth": 8}},
        {"name": "Спортивная сумка",    "slots": 16, "craft_tier": 3, "cost": {"cloth": 10, "scrap": 3}},
        {"name": "Туристический рюкзак","slots": 22, "craft_tier": 4, "cost": {"cloth": 15, "scrap": 8}},
        {"name": "Тактический рюкзак",  "slots": 28, "craft_tier": 5, "cost": {"cloth": 20, "rare_metals": 5}},
        {"name": "Военный рюкзак",      "slots": 35, "craft_tier": 6, "cost": {"rare_metals": 10, "scrap": 15}},
        {"name": "Рейдерский рюкзак",   "slots": 45, "craft_tier": 7, "cost": {"rare_metals": 15, "electronics": 8}},
    ],
}

STARTER_EQUIPMENT = {
    "helmet":   0,
    "armor":    0,
    "pants":    0,
    "boots":    0,
    "melee":    0,
    "ranged":   0,
    "backpack": 0,
}

def get_equipment_item(slot: str, tier: int) -> dict:
    chain = EQUIPMENT_CHAINS.get(slot, [])
    if 0 <= tier < len(chain):
        return chain[tier]
    return {}

def get_total_defense(equipment: dict) -> int:
    total = 0
    for slot in ["helmet", "armor", "pants", "boots"]:
        tier = equipment.get(slot, 0)
        item = get_equipment_item(slot, tier)
        total += item.get("defense", 0)
    return total

def get_backpack_slots(equipment: dict) -> int:
    tier = equipment.get("backpack", 0)
    item = get_equipment_item("backpack", tier)
    return item.get("slots", 5)

def get_workshop_tier(buildings: dict) -> int:
    level = buildings.get("workshop", 0)
    if level == 0:
        return 0
    tiers = {1: 3, 2: 5, 3: 8}
    return tiers.get(level, 0)

# ─── НПС ─────────────────────────────────────────────────────────────────────
NPC_NAMES = [
    "Андрей", "Сергей", "Михаил", "Алексей", "Дмитрий",
    "Николай", "Виктор", "Иван", "Павел", "Артём",
    "Анна", "Мария", "Елена", "Ольга", "Наталья",
    "Татьяна", "Ирина", "Светлана", "Юлия", "Екатерина",
    "Богдан", "Тарас", "Остап", "Роман", "Василий",
]

# ─── РАДИОСООБЩЕНИЯ ──────────────────────────────────────────────────────────
RADIO_MESSAGES = {
    1:  "📻 Внимание всем выжившим.\nГоворит командование сектора Б-7.\n\nЭпидемия вышла из-под контроля.\nКрупные города потеряны. Армия\nотступает на оборонительные рубежи.\n\nУчёные Великой Крокожии начали\nработу над вакциной. Они говорят\nчто есть надежда.\n\n💉 Прогресс: 0%\n\nНайдите укрытие. Держитесь.\nКонец связи.",
    2:  "📻 Говорит сектор Б-7.\n\nСегодня ночью пал Северный район.\nЭвакуация не удалась. Выжившие\nпросим двигаться на юг.\n\nНе выходите в одиночку.\nДержитесь вместе.\n\nКонец связи.",
    3:  "📻 Говорит сектор Б-7.\n\nПолучены сообщения от выживших\nиз промышленной зоны. Там есть\nзапасы. Но и зомби там больше.\n\nРешайте сами — риск или голод.\nУдачи.\n\nКонец связи.",
    4:  "📻 Говорит сектор Б-7.\n\nСвязь с восточным сектором\nпотеряна три часа назад.\nПричина неизвестна.\n\nУсильте охрану периметра.\nНочи становятся опаснее.\n\nКонец связи.",
    5:  "📻 Говорит сектор Б-7.\n\nПоступают сведения что зомби\nстановятся агрессивнее ночью.\nПрирода этого явления неясна.\n\nУчёные работают. Мы работаем.\nДержитесь.\n\nКонец связи.",
    6:  "📻 Говорит сектор Б-7.\n\nСегодня потеряли троих солдат\nпри патрулировании. Хороших людей.\n\nНапоминаем — не геройствуйте.\nВыживший трус лучше мёртвого героя.\n\nКонец связи.",
    7:  "📻 Внимание. Важное сообщение.\nГоворит командование сектора Б-7.\n\nПрошла неделя. Мы ещё живы.\nЭто уже победа.\n\nУчёные Великой Крокожии\nсообщают о первых результатах.\nФормула вакцины частично готова.\n\n💉 Прогресс: 25%\n\nЕщё немного. Держитесь.\nКонец связи.",
    8:  "📻 Говорит сектор Б-7.\n\nПолучен сигнал бедствия\nиз западного квартала.\nГруппа выживших просит помощи.\n\nПомочь не можем. Прости.\nБерегите себя.\n\nКонец связи.",
    9:  "📻 Говорит сектор Б-7.\n\nЗапасы топлива на исходе.\nГенераторы работают через раз.\n\nЕсли слышите этот эфир —\nзначит мы ещё держимся.\nИ вы держитесь.\n\nКонец связи.",
    10: "📻 Говорит сектор Б-7.\n\nСегодня ночью орда прорвала\nюжный периметр. Отбили.\nЕле отбили.\n\nУкрепляйте базы. Каждый день\nони становятся сильнее.\n\nКонец связи.",
    11: "📻 Говорит сектор Б-7.\n\nСлухи о безопасной зоне\nна севере — это ложь.\nПроверяли. Там никого нет.\n\nНе верьте слухам.\nВерьте только нам.\n\nКонец связи.",
    12: "📻 Говорит сектор Б-7.\n\nОдин из наших учёных\nсвязался с Великой Крокожией.\nРабота идёт круглосуточно.\n\nОни не спят ради нас.\nМы не сдаёмся ради них.\n\nКонец связи.",
    13: "📻 Говорит сектор Б-7.\n\nТринадцатый день.\nНекоторые говорят плохое число.\n\nМы не верим в приметы.\nМы верим в выживание.\n\nКонец связи.",
    14: "📻 Говорит сектор Б-7.\n\nДве недели прошло.\nПоловина наших людей не дожила.\n\nНо вы живы. И мы живы.\nЗначит борьба продолжается.\n\nКонец связи.",
    15: "📻 Внимание. Важное сообщение.\nГоворит командование сектора Б-7.\n\nУчёные Великой Крокожии\nпреодолели критический барьер.\nВакцина работает на животных.\n\nИспытания на людях начнутся\nчерез несколько дней.\n\n💉 Прогресс: 50%\n\nПоловина пути позади.\nКонец связи.",
    16: "📻 Говорит сектор Б-7.\n\nНочью потеряли связь\nс бункером №4. Двадцать человек.\n\nМинута молчания.\n\n...\n\nПродолжаем работу.\nКонец связи.",
    17: "📻 Говорит сектор Б-7.\n\nЗафиксированы случаи когда\nзомби действовали скоординированно.\nЭто тревожный признак.\n\nНе недооценивайте их.\nКонец связи.",
    18: "📻 Говорит сектор Б-7.\n\nИспытания вакцины на людях\nдали обнадёживающие результаты.\nПобочные эффекты изучаются.\n\nСкоро. Совсем скоро.\nДержитесь ещё немного.\n\nКонец связи.",
    19: "📻 Говорит сектор Б-7.\n\nСегодня солнечный день.\nСтранно говорить об этом\nсреди всего происходящего.\n\nНо солнце всё ещё встаёт.\nЗначит мир ещё не кончился.\n\nКонец связи.",
    20: "📻 Говорит сектор Б-7.\n\nДвадцать дней.\nКто бы мог подумать.\n\nВы сильнее чем думаете.\nМы все сильнее.\n\nКонец связи.",
    21: "📻 Говорит сектор Б-7.\n\nПолучено сообщение из лаборатории.\nФинальная формула почти готова.\nОсталось несколько тестов.\n\nНе опускайте руки.\nФиниш близко.\n\nКонец связи.",
    22: "📻 Внимание. Важное сообщение.\nГоворит командование сектора Б-7.\n\nУчёные Великой Крокожии\nзавершают финальные испытания.\nМассовое производство готовится.\n\nНо орды усиливаются.\nОни будто чувствуют конец.\n\n💉 Прогресс: 75%\n\nПоследний рывок. Не сдавайтесь.\nКонец связи.",
    23: "📻 Говорит сектор Б-7.\n\nОрды стали крупнее.\nАтаки — чаще.\nКак будто время поджимает.\n\nУкрепляйте базы.\nПоследние дни самые опасные.\n\nКонец связи.",
    24: "📻 Говорит сектор Б-7.\n\nПотеряли ещё один аванпост.\nНо лаборатория цела.\n\nПока лаборатория цела —\nесть надежда.\n\nКонец связи.",
    25: "📻 Говорит сектор Б-7.\n\nПервые партии вакцины\nуже в производстве.\nДоставка — как только позволит обстановка.\n\nНемного. Совсем немного осталось.\nКонец связи.",
    26: "📻 Говорит сектор Б-7.\n\nСегодня ночью была самая\nкрупная орда за всё время.\nЕле удержались.\n\nОни чувствуют что проигрывают.\nИ злятся.\n\nКонец связи.",
    27: "📻 Говорит сектор Б-7.\n\nВертолёты с вакциной\nвылетают через трое суток.\nДержите периметр.\n\nПочти дома.\nКонец связи.",
    28: "📻 Говорит сектор Б-7.\n\nДвое суток.\nПросто продержитесь двое суток.\n\nМы верим в вас.\nКонец связи.",
    29: "📻 Говорит сектор Б-7.\n\nЗавтра.\nЗавтра всё изменится.\n\nОдна ночь. Последняя.\nКонец связи.",
    30: "📻 ВНИМАНИЕ ВСЕМ ВЫЖИВШИМ!\nГоворит командование сектора Б-7.\n\nВАКЦИНА ГОТОВА!\nУчёные Великой Крокожии\nвыполнили обещание!\n\nВертолёты уже в воздухе.\nЭвакуация начинается.\n\n💉 Прогресс: 100%\n\nВЫ ВЫЖИЛИ. ВЫ ПОБЕДИЛИ.\nСпасибо что не сдались.\n\nКонец связи. Навсегда.",
}

# ─── ИЗОБРАЖЕНИЯ ─────────────────────────────────────────────────────────────
IMAGE_KEYS = [
    # Локации
    "loc_residential", "loc_school", "loc_supermarket",
    "loc_hospital", "loc_factory", "loc_police", "loc_bank",
    # База по уровням
    "base_1", "base_2", "base_3", "base_4", "base_5",
    # Зомби по тирам
    "zombie_1", "zombie_2", "zombie_3",
    # События
    "night_attack", "victory", "death", "finale", "radio",
]
