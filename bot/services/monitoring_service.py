import psutil


def get_status() -> dict:
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    temp = None
    try:
        temps = psutil.sensors_temperatures()
        if "cpu_thermal" in temps:
            temp = temps["cpu_thermal"][0].current
        elif "coretemp" in temps:
            temp = temps["coretemp"][0].current
    except Exception:
        pass

    uptime_seconds = int(psutil.boot_time())
    import time
    uptime = int(time.time()) - uptime_seconds
    days = uptime // 86400
    hours = (uptime % 86400) // 3600
    minutes = (uptime % 3600) // 60

    return {
        "cpu": cpu,
        "ram_used": round(ram.used / 1024 / 1024 / 1024, 1),
        "ram_total": round(ram.total / 1024 / 1024 / 1024, 1),
        "ram_percent": ram.percent,
        "disk_used": round(disk.used / 1024 / 1024 / 1024, 1),
        "disk_total": round(disk.total / 1024 / 1024 / 1024, 1),
        "disk_percent": disk.percent,
        "temp": temp,
        "uptime": f"{days}д {hours}ч {minutes}м",
    }


def format_status(data: dict) -> str:
    temp_str = f"🌡 Температура: {data['temp']:.1f}°C\n" if data["temp"] else ""
    return (
        f"💻 CPU: {data['cpu']}%\n"
        f"🧠 RAM: {data['ram_used']} / {data['ram_total']} GB ({data['ram_percent']}%)\n"
        f"💾 Диск: {data['disk_used']} / {data['disk_total']} GB ({data['disk_percent']}%)\n"
        f"{temp_str}"
        f"⏱ Uptime: {data['uptime']}"
    )
