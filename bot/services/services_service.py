import urllib.request
import urllib.parse
import json
import logging
from config import settings

logger = logging.getLogger(__name__)

SERVICES = {
    "docker": "🐳 Docker",
    "transmission-daemon": "🌊 Transmission",
    "minidlna": "📺 MiniDLNA",
    "smbd": "📁 Samba",
}


def call_api(action: str, service: str) -> str:
    try:
        params = urllib.parse.urlencode({
            "action": action,
            "service": service,
            "token": settings.SERVICE_API_TOKEN,
        })
        url = f"{settings.SERVICE_API_URL}?{params}"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("result", data.get("error", "unknown"))
    except Exception as e:
        logger.error(f"Service API error: {e}")
        return f"error"


def get_status(service: str) -> str:
    return call_api("status", service)


def restart_service(service: str) -> str:
    return call_api("restart", service)


def start_service(service: str) -> str:
    return call_api("start", service)


def stop_service(service: str) -> str:
    return call_api("stop", service)


def get_all_statuses() -> list:
    result = []
    for service_id, service_name in SERVICES.items():
        status = get_status(service_id)
        result.append({
            "id": service_id,
            "name": service_name,
            "status": status,
            "is_active": status == "active",
        })
    return result
