import random
from dataclasses import dataclass

@dataclass
class EventResult:
    title: str
    text: str
    event_type: str
    credits_delta: int = 0
    fuel_delta: int = 0
    hull_delta: int = 0

EVENTS = {
    "technical": [
        {
            "title": "⚙️ Поломка двигателя",
            "text": "Двигатель начал барахлить на полпути. Пришлось потратить час на ремонт прямо в открытом космосе. Расход топлива вырос.",
            "fuel_delta": -2,
            "hull_delta": -5,
        },
        {
            "title": "💧 Утечка топлива",
            "text": "Датчики показали утечку в топливопроводе. Часть топлива потеряна до того как удалось заткнуть дыру.",
            "fuel_delta": -3,
        },
        {
            "title": "🌡 Перегрев реактора",
            "text": "Реактор вышел на критическую температуру. Пришлось снизить скорость и охладить системы. Потеряно время и ресурсы.",
            "hull_delta": -8,
            "credits_delta": -50,
        },
    ],
    "signal": [
        {
            "title": "📡 Неизвестный маяк",
            "text": "Сканеры зафиксировали слабый сигнал маяка. Небольшое отклонение от курса — и вы находите брошенный контейнер с припасами.",
            "credits_delta": 120,
            "fuel_delta": 1,
        },
        {
            "title": "📻 Странный сигнал",
            "text": "Приёмник поймал зашифрованный сигнал. После декодирования — координаты тайника. Небольшая находка, но приятная.",
            "credits_delta": 80,
        },
        {
            "title": "🆘 Сигнал SOS",
            "text": "Вы получили сигнал бедствия. Корабль уже не спасти, но пилот выжил. Он заплатил вам за спасение.",
            "credits_delta": 200,
            "fuel_delta": -1,
        },
    ],
    "danger": [
        {
            "title": "☠️ Пираты",
            "text": "Из-за астероида вышел пиратский корабль. Короткая перестрелка — они отступили, но корпус получил повреждения.",
            "hull_delta": -15,
            "credits_delta": -100,
        },
        {
            "title": "☄️ Астероиды",
            "text": "Неожиданное астероидное поле. Маневрирование на пределе возможностей — несколько попаданий всё же случилось.",
            "hull_delta": -10,
        },
        {
            "title": "💥 Сбой систем",
            "text": "Бортовой компьютер дал сбой в самый неподходящий момент. Ручное управление спасло ситуацию, но не без потерь.",
            "hull_delta": -12,
            "fuel_delta": -2,
        },
    ],
    "find": [
        {
            "title": "📦 Дрейфующий контейнер",
            "text": "На радаре появился дрейфующий грузовой контейнер. Внутри — партия электронных компонентов. Неплохая находка.",
            "credits_delta": 150,
        },
        {
            "title": "🛸 Обломки корабля",
            "text": "Вы наткнулись на обломки старого корабля. Среди мусора нашлись запчасти которые можно продать.",
            "credits_delta": 100,
            "fuel_delta": 1,
        },
        {
            "title": "🤖 Дрейфующий дрон",
            "text": "Потерявшийся грузовой дрон всё ещё работает. После перепрограммирования он передал свой груз.",
            "credits_delta": 180,
        },
    ],
    "strange": [
        {
            "title": "👁 Загадочная аномалия",
            "text": "Пространство вокруг корабля на мгновение стало... другим. Приборы зафиксировали всплеск неизвестной энергии. Ничего не изменилось, но что-то было не так.",
        },
        {
            "title": "📨 Послание из прошлого",
            "text": "Старый ретранслятор передал сообщение датированное 30 лет назад. Голос неизвестного пилота описывает маршрут которого не существует на картах.",
        },
        {
            "title": "🌀 Гравитационная аномалия",
            "text": "Корабль засосало в слабую гравитационную аномалию. Выбраться удалось, но топливо сгорело быстрее обычного.",
            "fuel_delta": -2,
        },
    ],
    "empty": [
        {
            "title": "🌌 Тишина космоса",
            "text": "Перелёт прошёл без происшествий. Только звёзды и тишина. Иногда это лучшее что может случиться в космосе.",
        },
        {
            "title": "✨ Спокойный маршрут",
            "text": "Ничего особенного. Двигатель гудит ровно, топливо расходуется штатно. Хороший день для пилота.",
        },
    ],
}

LOCATION_DANGER = {
    "K-9 Hub": "safe",
    "Haven": "safe",
    "Dust-9": "medium",
    "Helion Station": "medium",
    "Helion Prime": "medium",
    "Void-3": "dangerous",
    "Nexus Gate": "dangerous",
    "Nexus Prime": "dangerous",
    "Shard": "dangerous",
}

def generate_event(destination: str) -> EventResult:
    danger = LOCATION_DANGER.get(destination, "medium")

    if danger == "safe":
        weights = {
            "technical": 10,
            "signal": 20,
            "danger": 5,
            "find": 25,
            "strange": 10,
            "empty": 30,
        }
    elif danger == "medium":
        weights = {
            "technical": 15,
            "signal": 15,
            "danger": 20,
            "find": 20,
            "strange": 15,
            "empty": 15,
        }
    else:
        weights = {
            "technical": 20,
            "signal": 10,
            "danger": 35,
            "find": 15,
            "strange": 10,
            "empty": 10,
        }

    event_type = random.choices(
        list(weights.keys()),
        weights=list(weights.values())
    )[0]

    event = random.choice(EVENTS[event_type])

    return EventResult(
        title=event["title"],
        text=event["text"],
        event_type=event_type,
        credits_delta=event.get("credits_delta", 0),
        fuel_delta=event.get("fuel_delta", 0),
        hull_delta=event.get("hull_delta", 0),
    )
