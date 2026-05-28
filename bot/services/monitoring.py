import psutil
import os

def get_cpu_usage() -> float:
    return psutil.cpu_percent(interval=1)

def get_ram_usage() -> dict:
    ram = psutil.virtual_memory()
    return {
        "total": round(ram.total / 1024 / 1024 / 1024, 1),
        "used": round(ram.used / 1024 / 1024 / 1024, 1),
        "percent": ram.percent
    }

def get_disk_usage() -> dict:
    disk = psutil.disk_usage("/")
    return {
        "total": round(disk.total / 1024 / 1024 / 1024, 1),
        "used": round(disk.used / 1024 / 1024 / 1024, 1),
        "percent": disk.percent
    }

def get_cpu_temperature() -> float | None:
    try:
        temps = psutil.sensors_temperatures()
        if "cpu_thermal" in temps:
            return temps["cpu_thermal"][0].current
        if "coretemp" in temps:
            return temps["coretemp"][0].current
        return None
    except Exception:
        return None

def get_uptime() -> str:
    with open("/proc/uptime", "r") as f:
        seconds = float(f.readline().split()[0])
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    if days > 0:
        return f"{days}д {hours}ч {minutes}м"
    elif hours > 0:
        return f"{hours}ч {minutes}м"
    else:
        return f"{minutes}м"

def format_status_message() -> str:
    cpu = get_cpu_usage()
    ram = get_ram_usage()
    disk = get_disk_usage()
    temp = get_cpu_temperature()
    uptime = get_uptime()

    cpu_emoji = "🟢" if cpu < 60 else "🟡" if cpu < 80 else "🔴"
    ram_emoji = "🟢" if ram["percent"] < 70 else "🟡" if ram["percent"] < 90 else "🔴"
    disk_emoji = "🟢" if disk["percent"] < 70 else "🟡" if disk["percent"] < 85 else "🔴"

    temp_line = ""
    if temp is not None:
        temp_emoji = "🟢" if temp < 60 else "🟡" if temp < 75 else "🔴"
        temp_line = f"{temp_emoji} Температура: {temp:.1f}°C\n"

    return (
        f"🖥 Состояние сервера\n"
        f"⏱ Uptime: {uptime}\n\n"
        f"{cpu_emoji} CPU: {cpu}%\n"
        f"{ram_emoji} RAM: {ram['used']} / {ram['total']} GB ({ram['percent']}%)\n"
        f"{disk_emoji} Диск: {disk['used']} / {disk['total']} GB ({disk['percent']}%)\n"
        f"{temp_line}"
    )
