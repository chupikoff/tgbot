import os
import subprocess
import tarfile
import logging
from datetime import datetime
from pathlib import Path
from config import settings

logger = logging.getLogger(__name__)

BACKUP_DIR = "/home/chpk/backups"

CONFIGS = [
    "/home/chpk/tgbot/.env",
    "/home/chpk/tgbot/docker-compose.yml",
    "/etc/transmission-daemon/settings.json",
    "/etc/samba/smb.conf",
    "/etc/minidlna.conf",
]


def ensure_backup_dir():
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)


def get_filename(prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{BACKUP_DIR}/{prefix}_{timestamp}.tar.gz"


def backup_database() -> str:
    ensure_backup_dir()
    filename = get_filename("database")
    sql_file = filename.replace(".tar.gz", ".sql")

    env = os.environ.copy()
    env["PGPASSWORD"] = settings.POSTGRES_PASSWORD

    result = subprocess.run(
        ["pg_dump", "-h", "postgres", "-U", settings.POSTGRES_USER, settings.POSTGRES_DB],
        capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        raise Exception(f"pg_dump failed: {result.stderr}")

    with open(sql_file, "w") as f:
        f.write(result.stdout)

    with tarfile.open(filename, "w:gz") as tar:
        tar.add(sql_file, arcname=os.path.basename(sql_file))

    os.remove(sql_file)
    return filename


def backup_configs() -> str:
    ensure_backup_dir()
    filename = get_filename("configs")

    with tarfile.open(filename, "w:gz") as tar:
        for path in CONFIGS:
            if os.path.exists(path):
                tar.add(path, arcname=os.path.basename(path))

    return filename


def get_backups() -> list:
    ensure_backup_dir()
    files = []
    for f in sorted(Path(BACKUP_DIR).glob("*.tar.gz"), reverse=True):
        files.append({
            "name": f.name,
            "path": str(f),
            "size": round(os.path.getsize(f) / 1024, 1),
            "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M"),
        })
    return files


def delete_old_backups(keep: int = 10):
    files = sorted(Path(BACKUP_DIR).glob("*.tar.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[keep:]:
        os.remove(f)
        logger.info(f"Deleted old backup: {f}")
