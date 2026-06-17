import logging
from transmission_rpc import Client
from config import settings

logger = logging.getLogger(__name__)

STATUS_NAMES = {
    "stopped": "⏸ Остановлен",
    "check pending": "🔄 Ожидает проверки",
    "checking": "🔍 Проверяется",
    "download pending": "⏳ Ожидает загрузки",
    "downloading": "⬇️ Загружается",
    "seed pending": "⏳ Ожидает раздачи",
    "seeding": "⬆️ Раздаётся",
}


def get_client() -> Client:
    return Client(
        host=settings.TRANSMISSION_HOST,
        port=settings.TRANSMISSION_PORT,
        username=settings.TRANSMISSION_USER or None,
        password=settings.TRANSMISSION_PASSWORD or None,
    )


def get_torrents() -> list:
    client = get_client()
    result = []
    for t in client.get_torrents():
        result.append({
            "id": t.id,
            "name": t.name,
            "status": t.status,
            "progress": round(t.progress, 1),
            "size": round(t.total_size / 1024 / 1024 / 1024, 2),
            "speed_down": round(t.rate_download / 1024, 1),
            "speed_up": round(t.rate_upload / 1024, 1),
            "eta": str(t.eta) if t.eta else "—",
        })
    return result


def get_torrent(torrent_id: int) -> dict | None:
    for t in get_client().get_torrents():
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


def add_torrent_url(url: str) -> dict:
    t = get_client().add_torrent(url, download_dir=settings.DOWNLOAD_DIR)
    return {"id": t.id, "name": t.name}


def add_torrent_file(data: bytes) -> dict:
    t = get_client().add_torrent(data, download_dir=settings.DOWNLOAD_DIR)
    return {"id": t.id, "name": t.name}


def pause_torrent(torrent_id: int):
    get_client().stop_torrent(torrent_id)


def resume_torrent(torrent_id: int):
    get_client().start_torrent(torrent_id)


def remove_torrent(torrent_id: int, delete_files: bool = False):
    get_client().remove_torrent(torrent_id, delete_data=delete_files)
