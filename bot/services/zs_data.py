# ─── РЕСУРСЫ ──────────────────────────────────────────────────────────────────
RESOURCES = {
    # Расходники
    "food":         {"name": "🥫 Еда",            "tier": 0},
    "meds":         {"name": "💊 Медикаменты",     "tier": 0},
    "ammo":         {"name": "🔋 Боеприпасы",      "tier": 0},
    # Тир 1
    "wood":         {"name": "🪵 Дерево",          "tier": 1},
    "scrap":        {"name": "🔩 Металлолом",      "tier": 1},
    "plastic":      {"name": "🧪 Пластик",         "tier": 1},
    "rubber":       {"name": "🧲 Резина",          "tier": 1},
    # Тир 2
    "electronics":  {"name": "⚡ Электроника",     "tier": 2},
    "parts":        {"name": "🔧 Запчасти",        "tier": 2},
    "cloth":        {"name": "🧵 Ткань",           "tier": 2},
    # Тир 3
    "kevlar":       {"name": "🛡 Кевлар",          "tier": 3},
    "optics":       {"name": "🔭 Оптика",          "tier": 3},
    "rare_metals":  {"name": "💎 Редкие металлы",  "tier": 3},
}

# ─── КЛАССЫ ───────────────────────────────────────────────────────────────────
CLASSES = {
    "soldier": {
        "name": "⚔️ Солдат",
        "desc": "+25% урон в бою, -10% получаемый урон",
        "damage_bonus": 1.25,
        "defense_bonus": 0.9,
        "hp_bonus": 0,
        "loot_bonus": 1.0,
        "food_bonus": 1.0,
        "craft_discount": 1.0,
        "build_discount": 1.0,
        "raid_time_bonus": 1.0,
        "med_bonus": 1.0,
        "can_craft_t3_without_workshop": False,
    },
    "scientist": {
        "name": "🔬 Учёный",
        "desc": "Крафт -20%, улучшение снаряжения до тир 3 без мастерской",
        "damage_bonus": 1.0,
        "defense_bonus": 1.0,
        "hp_bonus": 0,
        "loot_bonus": 1.0,
        "food_bonus": 1.0,
        "craft_discount": 0.8,
        "build_discount": 1.0,
        "raid_time_bonus": 1.0,
        "med_bonus": 1.0,
        "can_craft_t3_without_workshop": True,
    },
    "scout": {
        "name": "🏃 Разведчик",
        "desc": "Вылазки -30% времени, +20% лута",
        "damage_bonus": 1.0,
        "defense_bonus": 1.0,
        "hp_bonus": 0,
        "loot_bonus": 1.2,
        "food_bonus": 1.0,
        "craft_discount": 1.0,
        "build_discount": 1.0,
        "raid_time_bonus": 0.7,
        "med_bonus": 1.0,
        "can_craft_t3_without_workshop": False,
    },
    "builder": {
        "name": "🔨 Строитель",
        "desc": "Постройки -20%, +30 стартовых HP",
        "damage_bonus": 1.0,
        "defense_bonus": 1.0,
        "hp_bonus": 30,
        "loot_bonus": 1.0,
        "food_bonus": 1.0,
        "craft_discount": 1.0,
        "build_discount": 0.8,
        "raid_time_bonus": 1.0,
        "med_bonus": 1.0,
        "can_craft_t3_without_workshop": False,
    },
    "survivor": {
        "name": "🌿 Выживальщик",
        "desc": "Голод медленнее, +30% еды с вылазок",
        "damage_bonus": 1.0,
        "defense_bonus": 1.0,
        "hp_bonus": 0,
        "loot_bonus": 1.0,
        "food_bonus": 1.3,
        "craft_discount": 1.0,
        "build_discount": 1.0,
        "raid_time_bonus": 1.0,
        "med_bonus": 1.0,
        "can_craft_t3_without_workshop": False,
        "slow_hunger": True,
    },
    "medic": {
        "name": "🩺 Медик",
        "desc": "Медикаменты +30 HP вместо +20, медпункт лечит больше",
        "damage_bonus": 1.0,
        "defense_bonus": 1.0,
        "hp_bonus": 0,
        "loot_bonus": 1.0,
        "food_bonus": 1.0,
        "craft_discount": 1.0,
        "build_discount": 1.0,
        "raid_time_bonus": 1.0,
        "med_bonus": 1.5,
        "can_craft_t3_without_workshop": False,
    },
}

# ─── ЛОКАЦИИ ──────────────────────────────────────────────────────────────────
LOCATIONS = {
    "residential": {
        "name": "🏙 Жилые кварталы", "tier": 1, "time_cost": 120,
        "resources": {"food": {"chance": 60, "min": 1, "max": 3}, "cloth": {"chance": 50, "min": 1, "max": 2}},
        "zombie_hp": (25, 40), "zombie_damage": (8, 15), "zombie_chance": 35,
    },
    "school": {
        "name": "🏫 Школа", "tier": 1, "time_cost": 120,
        "resources": {"wood": {"chance": 60, "min": 1, "max": 3}, "scrap": {"chance": 50, "min": 1, "max": 2}},
        "zombie_hp": (25, 40), "zombie_damage": (8, 15), "zombie_chance": 35,
    },
    "supermarket": {
        "name": "🏪 Супермаркет", "tier": 1, "time_cost": 120,
        "resources": {"food": {"chance": 65, "min": 2, "max": 4}, "rubber": {"chance": 40, "min": 1, "max": 2}, "plastic": {"chance": 40, "min": 1, "max": 2}},
        "zombie_hp": (25, 40), "zombie_damage": (8, 15), "zombie_chance": 40,
    },
    "park": {
        "name": "🏕 Парк", "tier": 1, "time_cost": 120,
        "resources": {"wood": {"chance": 65, "min": 2, "max": 4}, "food": {"chance": 45, "min": 1, "max": 2}},
        "zombie_hp": (25, 40), "zombie_damage": (8, 15), "zombie_chance": 30,
    },
    "parking": {
        "name": "🚗 Автостоянка", "tier": 1, "time_cost": 120,
        "resources": {"scrap": {"chance": 65, "min": 2, "max": 4}, "rubber": {"chance": 55, "min": 1, "max": 3}},
        "zombie_hp": (25, 40), "zombie_damage": (8, 15), "zombie_chance": 35,
    },
    "hospital": {
        "name": "🏥 Больница", "tier": 2, "time_cost": 240,
        "resources": {"meds": {"chance": 60, "min": 1, "max": 3}, "cloth": {"chance": 50, "min": 1, "max": 2}},
        "zombie_hp": (60, 100), "zombie_damage": (15, 28), "zombie_chance": 50,
    },
    "factory": {
        "name": "🏭 Завод", "tier": 2, "time_cost": 240,
        "resources": {"scrap": {"chance": 60, "min": 2, "max": 4}, "parts": {"chance": 50, "min": 1, "max": 2}, "electronics": {"chance": 35, "min": 1, "max": 2}},
        "zombie_hp": (60, 100), "zombie_damage": (15, 28), "zombie_chance": 55,
    },
    "hotel": {
        "name": "🏨 Отель", "tier": 2, "time_cost": 240,
        "resources": {"cloth": {"chance": 55, "min": 1, "max": 3}, "meds": {"chance": 45, "min": 1, "max": 2}},
        "zombie_hp": (60, 100), "zombie_damage": (15, 28), "zombie_chance": 45,
    },
    "autoservice": {
        "name": "🔧 Автосервис", "tier": 2, "time_cost": 240,
        "resources": {"parts": {"chance": 60, "min": 1, "max": 3}, "rubber": {"chance": 50, "min": 1, "max": 2}, "electronics": {"chance": 40, "min": 1, "max": 2}},
        "zombie_hp": (60, 100), "zombie_damage": (15, 28), "zombie_chance": 50,
    },
    "police": {
        "name": "🚔 Полицейский участок", "tier": 3, "time_cost": 360,
        "resources": {"ammo": {"chance": 55, "min": 1, "max": 3}, "kevlar": {"chance": 45, "min": 1, "max": 2}, "electronics": {"chance": 35, "min": 1, "max": 2}},
        "zombie_hp": (120, 180), "zombie_damage": (28, 45), "zombie_chance": 65,
    },
    "bank": {
        "name": "🏦 Банк", "tier": 3, "time_cost": 360,
        "resources": {"optics": {"chance": 45, "min": 1, "max": 2}, "rare_metals": {"chance": 40, "min": 1, "max": 2}, "electronics": {"chance": 50, "min": 1, "max": 2}},
        "zombie_hp": (120, 180), "zombie_damage": (28, 45), "zombie_chance": 65,
    },
    "military": {
        "name": "🏗 Военная база", "tier": 3, "time_cost": 360,
        "resources": {"kevlar": {"chance": 50, "min": 1, "max": 3}, "ammo": {"chance": 50, "min": 2, "max": 4}, "rare_metals": {"chance": 40, "min": 1, "max": 2}},
        "zombie_hp": (120, 180), "zombie_damage": (28, 45), "zombie_chance": 70,
    },
}

# ─── СНАРЯЖЕНИЕ ───────────────────────────────────────────────────────────────
EQUIPMENT = {
    "helmet": {
        "name": "🪖 Шлем",
        "tiers": {
            0: {"name": "Нет", "defense": 0},
            1: {"name": "Бандана", "defense": 1, "craft": {"wood": 3, "cloth": 3}},
            2: {"name": "Мотоциклетный шлем", "defense": 2, "craft": {"scrap": 5, "plastic": 3}},
            3: {"name": "Строительная каска", "defense": 4, "craft": {"scrap": 8, "parts": 3}},
            4: {"name": "Военная каска", "defense": 6, "craft": {"parts": 5, "kevlar": 3}},
            5: {"name": "Тактический шлем", "defense": 8, "craft": {"kevlar": 5, "rare_metals": 2}},
        }
    },
    "armor": {
        "name": "👕 Броня",
        "tiers": {
            0: {"name": "Кожанка", "defense": 1},
            1: {"name": "Усиленная кожанка", "defense": 2, "craft": {"cloth": 5, "rubber": 3}},
            2: {"name": "Самодельный жилет", "defense": 4, "craft": {"scrap": 5, "cloth": 5}},
            3: {"name": "Противоударный жилет", "defense": 6, "craft": {"parts": 5, "cloth": 5}},
            4: {"name": "Бронежилет", "defense": 9, "craft": {"kevlar": 5, "parts": 5}},
            5: {"name": "Тактический бронежилет", "defense": 12, "craft": {"kevlar": 8, "rare_metals": 3}},
        }
    },
    "pants": {
        "name": "👖 Штаны",
        "tiers": {
            0: {"name": "Джинсы", "defense": 0},
            1: {"name": "Усиленные джинсы", "defense": 1, "craft": {"cloth": 3, "rubber": 2}},
            2: {"name": "Карго штаны", "defense": 2, "craft": {"cloth": 5, "plastic": 3}},
            3: {"name": "Тактические штаны", "defense": 3, "craft": {"parts": 3, "cloth": 5}},
            4: {"name": "Бронированные штаны", "defense": 4, "craft": {"kevlar": 3, "parts": 5}},
            5: {"name": "Боевые штаны", "defense": 5, "craft": {"kevlar": 5, "rare_metals": 2}},
        }
    },
    "boots": {
        "name": "👟 Обувь",
        "tiers": {
            0: {"name": "Кроссовки", "defense": 0},
            1: {"name": "Рабочие ботинки", "defense": 1, "craft": {"wood": 3, "rubber": 3}},
            2: {"name": "Берцы", "defense": 2, "craft": {"scrap": 3, "rubber": 5}},
            3: {"name": "Усиленные берцы", "defense": 3, "craft": {"scrap": 5, "parts": 3}},
            4: {"name": "Тактические берцы", "defense": 4, "craft": {"parts": 5, "kevlar": 3}},
            5: {"name": "Штурмовые ботинки", "defense": 5, "craft": {"kevlar": 5, "rare_metals": 2}},
        }
    },
    "melee": {
        "name": "⚔️ Ближний бой",
        "tiers": {
            0: {"name": "Кулаки", "damage": 8},
            1: {"name": "Дубина", "damage": 15, "craft": {"wood": 5}},
            2: {"name": "Бита с гвоздями", "damage": 25, "craft": {"wood": 5, "scrap": 5}},
            3: {"name": "Мачете", "damage": 40, "craft": {"scrap": 8, "parts": 3}},
            4: {"name": "Боевой топор", "damage": 60, "craft": {"parts": 5, "rare_metals": 2}},
            5: {"name": "Тактический томагавк", "damage": 85, "craft": {"rare_metals": 5, "optics": 2}},
        }
    },
    "ranged": {
        "name": "🔫 Дальний бой",
        "tiers": {
            0: {"name": "Нет", "damage": 0},
            1: {"name": "Рогатка", "damage": 10, "ammo_cost": 0, "craft": {"wood": 3, "rubber": 3}},
            2: {"name": "Арбалет", "damage": 22, "ammo_cost": 0, "craft": {"wood": 8, "scrap": 5}},
            3: {"name": "Пистолет", "damage": 38, "ammo_cost": 1, "craft": {"scrap": 8, "parts": 5}},
            4: {"name": "Дробовик", "damage": 58, "ammo_cost": 2, "craft": {"parts": 8, "electronics": 5}},
            5: {"name": "Снайперская винтовка", "damage": 90, "ammo_cost": 1, "craft": {"rare_metals": 5, "optics": 3}},
        }
    },
    "backpack": {
        "name": "🎒 Рюкзак",
        "tiers": {
            0: {"name": "Нет", "slots": 5},
            1: {"name": "Школьный рюкзак", "slots": 8, "craft": {"cloth": 5, "wood": 3}},
            2: {"name": "Спортивная сумка", "slots": 12, "craft": {"cloth": 8, "plastic": 5}},
            3: {"name": "Туристический рюкзак", "slots": 16, "craft": {"cloth": 8, "parts": 3}},
            4: {"name": "Тактический рюкзак", "slots": 22, "craft": {"parts": 5, "electronics": 3}},
            5: {"name": "Военный рюкзак", "slots": 30, "craft": {"electronics": 5, "rare_metals": 2}},
        }
    },
}

# ─── ПОСТРОЙКИ ────────────────────────────────────────────────────────────────
BUILDINGS = {
    "shelter": {
        "name": "🏠 Убежище",
        "levels": {
            1: {"hp_bonus": 20,  "npc_slots": 2,  "cost": {"wood": 8, "scrap": 5}},
            2: {"hp_bonus": 40,  "npc_slots": 4,  "cost": {"wood": 10, "scrap": 8, "plastic": 5}},
            3: {"hp_bonus": 60,  "npc_slots": 6,  "cost": {"scrap": 8, "parts": 5}},
            4: {"hp_bonus": 80,  "npc_slots": 8,  "cost": {"parts": 10, "electronics": 5}},
            5: {"hp_bonus": 100, "npc_slots": 10, "cost": {"electronics": 8, "kevlar": 3}},
        }
    },
    "workshop": {
        "name": "🔧 Мастерская",
        "levels": {
            1: {"craft_tier": 1, "cost": {"wood": 8, "scrap": 5}},
            2: {"craft_tier": 2, "cost": {"scrap": 10, "plastic": 8}},
            3: {"craft_tier": 3, "cost": {"scrap": 8, "parts": 5}},
            4: {"craft_tier": 4, "cost": {"parts": 10, "electronics": 5}},
            5: {"craft_tier": 5, "cost": {"electronics": 8, "rare_metals": 3}},
        }
    },
    "garden": {
        "name": "🌱 Огород",
        "levels": {
            1: {"food_per_day": 1, "cost": {"wood": 8, "rubber": 5}},
            2: {"food_per_day": 2, "cost": {"wood": 10, "plastic": 8}},
            3: {"food_per_day": 3, "cost": {"wood": 8, "cloth": 5}},
            4: {"food_per_day": 4, "cost": {"cloth": 10, "parts": 5}},
            5: {"food_per_day": 5, "cost": {"parts": 8, "electronics": 5}},
        }
    },
    "medpost": {
        "name": "🏥 Медпункт",
        "levels": {
            1: {"heal_per_day": 10, "cost": {"wood": 8, "cloth": 5}},
            2: {"heal_per_day": 20, "cost": {"cloth": 10, "plastic": 8}},
            3: {"heal_per_day": 30, "cost": {"cloth": 8, "parts": 5}},
            4: {"heal_per_day": 40, "cost": {"parts": 10, "electronics": 5}},
            5: {"heal_per_day": 50, "cost": {"electronics": 8, "rare_metals": 3}},
        }
    },
    "watchtower": {
        "name": "🔭 Наблюдательная вышка",
        "levels": {
            1: {"info": "resources",   "cost": {"wood": 8, "scrap": 5}},
            2: {"info": "zombie_chance","cost": {"scrap": 10, "plastic": 8}},
            3: {"info": "zombie_stats", "cost": {"scrap": 8, "electronics": 5}},
            4: {"info": "npc_chance",   "cost": {"electronics": 10, "optics": 5}},
            5: {"info": "all",          "cost": {"optics": 8, "rare_metals": 3}},
        }
    },
    "defense": {
        "name": "🛡 Защита",
        "levels": {
            1: {"damage_reduction": 10, "cost": {"wood": 8, "rubber": 5}},
            2: {"damage_reduction": 20, "cost": {"wood": 10, "scrap": 8}},
            3: {"damage_reduction": 35, "cost": {"scrap": 8, "electronics": 5}},
            4: {"damage_reduction": 50, "cost": {"scrap": 10, "kevlar": 5}},
            5: {"damage_reduction": 70, "cost": {"kevlar": 8, "rare_metals": 3}},
        }
    },
}

# ─── УРОВНИ НПС ───────────────────────────────────────────────────────────────
NPC_LEVELS = {
    1: {"name": "Новичок",  "hp": 50,  "loot_bonus": 1.0,  "exp_needed": 3},
    2: {"name": "Выживший", "hp": 70,  "loot_bonus": 1.1,  "exp_needed": 8},
    3: {"name": "Опытный",  "hp": 90,  "loot_bonus": 1.2,  "exp_needed": 15},
    4: {"name": "Ветеран",  "hp": 120, "loot_bonus": 1.35, "exp_needed": 25},
    5: {"name": "Легенда",  "hp": 150, "loot_bonus": 1.5,  "exp_needed": 999},
}

def get_npc_level_data(level: int) -> dict:
    return NPC_LEVELS.get(level, NPC_LEVELS[1])

def get_npc_exp_needed(level: int) -> int:
    return NPC_LEVELS.get(level, NPC_LEVELS[1])["exp_needed"]

# ─── НОЧНЫЕ НАПАДЕНИЯ ─────────────────────────────────────────────────────────
NIGHT_ATTACK_CHANCE = 30

HORDE_LEVELS = {
    (1, 5):   {"hp": (30, 50),   "damage": (8, 15)},
    (6, 10):  {"hp": (50, 80),   "damage": (15, 25)},
    (11, 15): {"hp": (80, 120),  "damage": (25, 35)},
    (16, 20): {"hp": (120, 160), "damage": (35, 45)},
    (21, 999):{"hp": (160, 200), "damage": (45, 60)},
}

def get_horde_stats(day: int) -> dict:
    for (min_day, max_day), stats in HORDE_LEVELS.items():
        if min_day <= day <= max_day:
            return stats
    return HORDE_LEVELS[(21, 999)]

# ─── СОВЕТЫ ───────────────────────────────────────────────────────────────────
TIPS = [
    "Следи за голодом перед вылазкой — при 0 теряешь HP.",
    "Улучшай мастерскую чтобы открыть крафт лучшего снаряжения.",
    "Выживший с высоким уровнем приносит больше лута.",
    "Огород даёт еду каждое утро — строй его первым.",
    "Защита базы снижает урон от ночной орды.",
    "Тир 3 локации опасны — иди туда с хорошим снаряжением.",
    "Медпункт восстанавливает HP каждое утро.",
    "Корми выживших чтобы они оставались боеспособными.",
    "Наблюдательная вышка даёт информацию о локациях.",
    "Строитель получает +30 HP — хороший класс для новичков.",
    "Разведчик возвращается с вылазок быстрее.",
    "Учёный может крафтить снаряжение тир 3 без мастерской.",
]
