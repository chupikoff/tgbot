import logging
import docker

logger = logging.getLogger(__name__)


def get_containers() -> list:
    client = docker.from_env()
    result = []
    for c in client.containers.list(all=True):
        result.append({
            "id": c.short_id,
            "name": c.name,
            "status": c.status,
            "image": c.image.tags[0] if c.image.tags else "unknown",
        })
    return result


def get_container_info(name: str) -> dict | None:
    try:
        client = docker.from_env()
        c = client.containers.get(name)
        cpu_percent = 0.0
        mem_mb = 0.0
        mem_percent = 0.0

        if c.status == "running":
            stats = c.stats(stream=False)
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"].get("system_cpu_usage", 0) - stats["precpu_stats"].get("system_cpu_usage", 0)
            cpu_percent = round((cpu_delta / system_delta) * 100, 1) if system_delta > 0 else 0.0
            mem_usage = stats["memory_stats"].get("usage", 0)
            mem_limit = stats["memory_stats"].get("limit", 1)
            mem_percent = round((mem_usage / mem_limit) * 100, 1)
            mem_mb = round(mem_usage / 1024 / 1024, 1)

        return {
            "name": c.name,
            "status": c.status,
            "image": c.image.tags[0] if c.image.tags else "unknown",
            "cpu_percent": cpu_percent,
            "mem_mb": mem_mb,
            "mem_percent": mem_percent,
        }
    except Exception as e:
        logger.error(f"Container info error: {e}")
        return None


def container_action(name: str, action: str) -> bool:
    try:
        client = docker.from_env()
        c = client.containers.get(name)
        if action == "start":
            c.start()
        elif action == "stop":
            c.stop()
        elif action == "restart":
            c.restart()
        elif action == "remove":
            c.remove(force=True)
        return True
    except Exception as e:
        logger.error(f"Container action error: {e}")
        return False
