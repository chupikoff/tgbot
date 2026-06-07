import os
import re
import urllib.request
import urllib.parse
import json
import logging
from config import settings

logger = logging.getLogger(__name__)

MEDIA_DIR = "/home/chpk/media"

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv", ".flv"}

def get_media_files() -> list[str]:
    files = []
    try:
        for f in sorted(os.listdir(MEDIA_DIR)):
            ext = os.path.splitext(f)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                files.append(f)
    except Exception as e:
        logger.error(f"Error reading media dir: {e}")
    return files

def parse_movie_name(filename: str) -> tuple[str, str | None]:
    name = os.path.splitext(filename)[0]
    # Ищем год
    year_match = re.search(r"[\(\[\s](\d{4})[\)\]\s]", name)
    year = year_match.group(1) if year_match else None
    # Если есть английское название после украинского — берём его
    # Формат: "Украинское название  English Title (year)"
    eng_match = re.search(r"\s{2,}([A-Za-z][^(\[]+?)\s*[\(\[]", name)
    if eng_match:
        name = eng_match.group(1).strip()
    else:
        # Убираем всё после года
        if year:
            name = name[:name.index(year)].strip()
        # Убираем украинские символи если есть английские
        if re.search(r"[A-Za-z]", name):
            parts = re.split(r"[\u0400-\u04ff]+", name)
            eng_parts = [p.strip() for p in parts if re.search(r"[A-Za-z]{2,}", p)]
            if eng_parts:
                name = max(eng_parts, key=len)
        # Убираем технические теги
        name = re.sub(r"\b(1080p|720p|480p|4K|2160p|BluRay|BDRip|BDRemux|WEBRip|HDRip|UHD|HDR|x264|x265|HEVC|AAC|DTS|AC3|H\.265|H\.264)\b.*", "", name, flags=re.IGNORECASE)
        name = re.sub(r"[-_\.]+", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
    return name, year

def search_omdb(title: str, year: str | None = None) -> dict | None:
    if not settings.OMDB_API_KEY:
        return None
    try:
        params = {"apikey": settings.OMDB_API_KEY, "t": title, "type": "movie"}
        if year:
            params["y"] = year
        url = f"http://www.omdbapi.com/?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("Response") == "True":
                return data
    except Exception as e:
        logger.error(f"OMDB error: {e}")
    return None

def format_movie_info(data: dict) -> str:
    title = data.get("Title", "—")
    year = data.get("Year", "—")
    rating = data.get("imdbRating", "—")
    genre = data.get("Genre", "—")
    plot = data.get("Plot", "—")
    imdb_id = data.get("imdbID", "")
    runtime = data.get("Runtime", "—")
    director = data.get("Director", "—")

    text = (
        f"🎬 {title} ({year})\n"
        f"⭐ IMDB: {rating}\n"
        f"⏱ {runtime}\n"
        f"🎭 {genre}\n"
        f"🎬 Реж: {director}\n\n"
        f"📝 {plot}"
    )
    if imdb_id:
        text += f"\n\n🔗 https://www.imdb.com/title/{imdb_id}/"
    return text

async def get_imdb_override(session, filename: str):
    from sqlalchemy import select, text
    result = await session.execute(
        text("SELECT imdb_id, title FROM media_imdb WHERE filename = :fn"),
        {"fn": filename}
    )
    row = result.fetchone()
    return {"imdb_id": row[0], "title": row[1]} if row else None

async def set_imdb_override(session, filename: str, imdb_id: str, added_by: int):
    from sqlalchemy import text
    imdb_id = imdb_id.strip()
    if "imdb.com/title/" in imdb_id:
        match = re.search(r"tt\d+", imdb_id)
        if match:
            imdb_id = match.group(0)
    await session.execute(
        text("INSERT INTO media_imdb (filename, imdb_id, added_by) VALUES (:fn, :iid, :ab) ON CONFLICT (filename) DO UPDATE SET imdb_id = :iid"),
        {"fn": filename, "iid": imdb_id, "ab": added_by}
    )
    await session.commit()
    return imdb_id

def search_omdb_by_id(imdb_id: str) -> dict | None:
    if not settings.OMDB_API_KEY:
        return None
    try:
        params = {"apikey": settings.OMDB_API_KEY, "i": imdb_id}
        url = f"http://www.omdbapi.com/?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("Response") == "True":
                return data
    except Exception as e:
        logger.error(f"OMDB error: {e}")
    return None
