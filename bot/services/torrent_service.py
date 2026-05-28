import logging
from transmission_rpc import Client
from config import settings

logger = logging.getLogger(__name__)

def get_client() -> Client:
    return Client(
        host=settings.TRANSMISSION_HOST,
        port=settings.TRANSMISSION_PORT,
        username=settings.TRANSMISSION_USER if settings.TRANSMISSION_USER else None,
        password=settings.TRANSMISSION_PASSWORD if settings.TRANSMISSION_PASSWORD else None,
    )

def get_torrents() -> list:
    client = get_client()
    torrents = client.get_torrents()
    result = []
    for t in torrents:
        result.append({
            "id": t.id,
            "name": t.name,
            "status": t.status,
            "progress": round(t.progress, 1),
            "size": round(t.total_size / 1024 / 1024 / 1024, 2),
            "speed_down": round(t.rate_download / 1024, 1),
            "speed_up": round(t.rate_upload / 1024, 1),
        })
    return result

def add_torrent_by_url(url: str) -> dict:
    client = get_client()
    torrent = client.add_torrent(url, download_dir=settings.DOWNLOAD_DIR)
    return {
        "id": torrent.id,
        "name": torrent.name,
    }

def add_torrent_by_file(file_content: bytes) -> dict:
    try:
        logger.info(f"Sending torrent, bytes length: {len(file_content)}")
        client = get_client()
        torrent = client.add_torrent(file_content, download_dir=settings.DOWNLOAD_DIR)
        return {
            "id": torrent.id,
            "name": torrent.name,
        }
    except Exception as e:
        logger.error(f"Error adding torrent: {e}", exc_info=True)
        raise

def remove_torrent(torrent_id: int, delete_files: bool = False) -> bool:
    client = get_client()
    client.remove_torrent(torrent_id, delete_data=delete_files)
    return True

def pause_torrent(torrent_id: int) -> bool:
    client = get_client()
    client.stop_torrent(torrent_id)
    return True

def resume_torrent(torrent_id: int) -> bool:
    client = get_client()
    client.start_torrent(torrent_id)
    return True

def get_torrent(torrent_id: int) -> dict | None:
    client = get_client()
    torrents = client.get_torrents()
    for t in torrents:
        if t.id == torrent_id:
            return {
                "id": t.id,
                "name": t.name,
                "status": t.status,
                "progress": round(t.progress, 1),
                "size": round(t.total_size / 1024 / 1024 / 1024, 2),
                "speed_down": round(t.rate_download / 1024, 1),
                "speed_up": round(t.rate_upload / 1024, 1),
                "eta": str(t.eta) if t.eta else "—",
            }
    return None

STATUS_NAMES = {
    "stopped": "⏸ Остановлен",
    "check pending": "🔄 Ожидает проверки",
    "checking": "🔍 Проверяется",
    "download pending": "⏳ Ожидает загрузки",
    "downloading": "⬇️ Загружается",
    "seed pending": "⏳ Ожидает раздачи",
    "seeding": "⬆️ Раздаётся",
}
