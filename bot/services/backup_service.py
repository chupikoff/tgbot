import os
import subprocess
import tarfile
import logging
from datetime import datetime
from pathlib import Path

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

def get_backup_filename(prefix: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{BACKUP_DIR}/{prefix}_{timestamp}.tar.gz"

def backup_configs() -> str:
    ensure_backup_dir()
    filename = get_backup_filename("configs")

    with tarfile.open(filename, "w:gz") as tar:
        for config_path in CONFIGS:
            if os.path.exists(config_path):
                tar.add(config_path, arcname=os.path.basename(config_path))
                logger.info(f"Added to backup: {config_path}")
            else:
                logger.warning(f"Config not found, skipping: {config_path}")

    size = os.path.getsize(filename)
    logger.info(f"Configs backup created: {filename} ({size} bytes)")
    return filename

def backup_database(postgres_user: str, postgres_db: str, postgres_password: str) -> str:
    ensure_backup_dir()
    filename = get_backup_filename("database")
    sql_file = filename.replace(".tar.gz", ".sql")

    env = os.environ.copy()
    env["PGPASSWORD"] = postgres_password

    result = subprocess.run(
        ["pg_dump", "-h", "postgres", "-U", postgres_user, postgres_db],
        capture_output=True,
        text=True,
        env=env
    )

    if result.returncode != 0:
        raise Exception(f"pg_dump failed: {result.stderr}")

    with open(sql_file, "w") as f:
        f.write(result.stdout)

    with tarfile.open(filename, "w:gz") as tar:
        tar.add(sql_file, arcname=os.path.basename(sql_file))

    os.remove(sql_file)
    size = os.path.getsize(filename)
    logger.info(f"Database backup created: {filename} ({size} bytes)")
    return filename

def get_backups() -> list:
    ensure_backup_dir()
    files = []
    for f in sorted(Path(BACKUP_DIR).glob("*.tar.gz"), reverse=True):
        size = os.path.getsize(f)
        files.append({
            "name": f.name,
            "path": str(f),
            "size": round(size / 1024, 1),
            "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M"),
        })
    return files

def delete_old_backups(keep: int = 10):
    ensure_backup_dir()
    files = sorted(Path(BACKUP_DIR).glob("*.tar.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[keep:]:
        os.remove(f)
        logger.info(f"Deleted old backup: {f}")
