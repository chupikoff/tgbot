import logging
import urllib.request
import urllib.parse
import json
from config import settings

logger = logging.getLogger(__name__)

SERVICES = []

SERVICE_NAMES = {}

def call_service_api(action: str, service: str) -> str:
    try:
        params = urllib.parse.urlencode({
            "action": action,
            "service": service,
            "token": settings.SERVICE_API_TOKEN
        })
        url = f"{settings.SERVICE_API_URL}?{params}"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("result", data.get("error", "unknown"))
    except Exception as e:
        logger.error(f"Service API error: {e}")
        return f"ERROR: {str(e)}"

def get_service_status(service: str) -> str:
    return call_service_api("status", service)

def restart_service(service: str) -> str:
    return call_service_api("restart", service)

def start_service(service: str) -> str:
    return call_service_api("start", service)

def stop_service(service: str) -> str:
    return call_service_api("stop", service)

def get_all_statuses() -> list:
    result = []
    for service in SERVICES:
        status = get_service_status(service)
        is_active = status == "active"
        result.append({
            "service": service,
            "name": SERVICE_NAMES.get(service, service),
            "status": status,
            "is_active": is_active,
        })
    return result
