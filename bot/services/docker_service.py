import logging
import docker

logger = logging.getLogger(__name__)

def get_docker_client():
    return docker.from_env()

def get_containers() -> list:
    try:
        client = get_docker_client()
        containers = client.containers.list(all=True)
        result = []
        for c in containers:
            result.append({
                "id": c.short_id,
                "name": c.name,
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else "unknown",
            })
        return result
    except Exception as e:
        logger.error(f"Docker error: {e}")
        raise

def get_container_info(container_name: str) -> dict | None:
    try:
        client = get_docker_client()
        container = client.containers.get(container_name)
        cpu_percent = 0.0
        mem_mb = 0.0
        mem_percent = 0.0

        if container.status == "running":
            stats = container.stats(stream=False)
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"].get("system_cpu_usage", 0) - stats["precpu_stats"].get("system_cpu_usage", 0)
            cpu_percent = round((cpu_delta / system_delta) * 100, 1) if system_delta > 0 else 0.0
            mem_usage = stats["memory_stats"].get("usage", 0)
            mem_limit = stats["memory_stats"].get("limit", 1)
            mem_percent = round((mem_usage / mem_limit) * 100, 1)
            mem_mb = round(mem_usage / 1024 / 1024, 1)

        return {
            "id": container.short_id,
            "name": container.name,
            "status": container.status,
            "image": container.image.tags[0] if container.image.tags else "unknown",
            "cpu_percent": cpu_percent,
            "mem_mb": mem_mb,
            "mem_percent": mem_percent,
        }
    except Exception as e:
        logger.error(f"Docker container info error: {e}")
        return None

def container_action(container_name: str, action: str) -> dict:
    try:
        client = get_docker_client()
        container = client.containers.get(container_name)
        if action == "start":
            container.start()
        elif action == "stop":
            container.stop()
        elif action == "restart":
            container.restart()
        elif action == "remove":
            container.remove(force=True)
        return {"success": True}
    except Exception as e:
        logger.error(f"Docker action error: {e}")
        return {"success": False, "error": str(e)}
