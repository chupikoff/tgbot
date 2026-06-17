import os
import hashlib
import logging
import urllib.request
import urllib.parse
import json
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from models.media import Media, MediaCategory
from config import settings

logger = logging.getLogger(__name__)


async def get_all_media(session: AsyncSession, category_id: int | None = None) -> list[Media]:
    query = select(Media).order_by(Media.created_at.desc())
    if category_id:
        query = query.where(Media.category_id == category_id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_media(session: AsyncSession, media_id: int) -> Media | None:
    result = await session.execute(select(Media).where(Media.id == media_id))
    return result.scalar_one_or_none()


async def create_media(session: AsyncSession, title: str, added_by: int,
                       file_id: str | None = None, file_path: str | None = None,
                       category_id: int | None = None, description: str | None = None) -> Media:
    media = Media(title=title, added_by=added_by, file_id=file_id,
                  file_path=file_path, category_id=category_id, description=description)
    session.add(media)
    await session.commit()
    return media


async def delete_media(session: AsyncSession, media_id: int):
    media = await get_media(session, media_id)
    if media:
        if media.file_path and os.path.exists(media.file_path):
            os.remove(media.file_path)
        await session.delete(media)
        await session.commit()


async def get_categories(session: AsyncSession) -> list[MediaCategory]:
    result = await session.execute(select(MediaCategory).order_by(MediaCategory.name))
    return result.scalars().all()


async def create_category(session: AsyncSession, name: str, created_by: int) -> MediaCategory:
    cat = MediaCategory(name=name, created_by=created_by)
    session.add(cat)
    await session.commit()
    return cat


def clean_title(name: str) -> str:
    import re
    name = re.sub(r'\[.*?\]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def get_media_files() -> list[dict]:
    media_dir = Path(settings.MEDIA_DIR)
    extensions = {".mp4", ".mkv", ".avi", ".mov", ".m4v"}
    files = []
    dirs = []
    seen = set()

    for item in sorted(media_dir.iterdir()):
        if item.is_dir():
            key = item.name
            if key not in seen:
                seen.add(key)
                dirs.append({"name": item.name, "path": item.name, "is_dir": True, "clean_name": clean_title(item.name)})
        elif item.is_file() and item.suffix.lower() in extensions:
            key = item.name
            if key not in seen:
                seen.add(key)
                files.append({"name": item.stem, "path": item.name, "is_dir": False, "clean_name": clean_title(item.stem)})

    return files + dirs


def get_file_hash(filename: str) -> str:
    return hashlib.md5(filename.encode()).hexdigest()[:8]


def get_omdb_info(imdb_id: str) -> dict | None:
    try:
        url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={settings.OMDB_API_KEY}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("Response") == "True":
                return data
    except Exception as e:
        logger.error(f"OMDB error: {e}")
    return None


def search_omdb_by_title(title: str, clean: bool = False) -> dict | None:
    if clean:
        title = clean_title(title)
    try:
        params = urllib.parse.urlencode({"t": title, "apikey": settings.OMDB_API_KEY})
        url = f"http://www.omdbapi.com/?{params}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("Response") == "True":
                return data
    except Exception as e:
        logger.error(f"OMDB search error: {e}")
    return None


async def get_library_info(session, file_hash: str):
    from sqlalchemy import select
    from models.media import MediaLibraryInfo
    result = await session.execute(select(MediaLibraryInfo).where(MediaLibraryInfo.file_hash == file_hash))
    return result.scalar_one_or_none()


async def save_library_info(session, file_hash: str, imdb_id: str, info: dict):
    from models.media import MediaLibraryInfo
    existing = await get_library_info(session, file_hash)
    if existing:
        existing.imdb_id = imdb_id
        existing.title = info.get('Title', '')
        existing.year = info.get('Year')
        existing.rating = info.get('imdbRating')
        existing.genre = info.get('Genre')
        existing.runtime = info.get('Runtime')
        existing.plot = info.get('Plot')
    else:
        obj = MediaLibraryInfo(
            file_hash=file_hash,
            imdb_id=imdb_id,
            title=info.get('Title', ''),
            year=info.get('Year'),
            rating=info.get('imdbRating'),
            genre=info.get('Genre'),
            runtime=info.get('Runtime'),
            plot=info.get('Plot'),
        )
        session.add(obj)
    await session.commit()


async def get_library_info_by_filename(session, filename: str):
    from sqlalchemy import text
    result = await session.execute(
        text("SELECT imdb_id, title, year, rating, genre, runtime, plot FROM media_imdb WHERE filename = :fn"),
        {"fn": filename}
    )
    row = result.fetchone()
    if row:
        return {
            "imdb_id": row[0], "title": row[1], "year": row[2],
            "rating": row[3], "genre": row[4], "runtime": row[5], "plot": row[6]
        }
    return None


async def save_library_info_by_filename(session, filename: str, imdb_id: str, info: dict, added_by: int):
    from sqlalchemy import text
    await session.execute(
        text("""
            INSERT INTO media_imdb (filename, imdb_id, title, year, rating, genre, runtime, plot, added_by)
            VALUES (:fn, :iid, :title, :year, :rating, :genre, :runtime, :plot, :ab)
            ON CONFLICT (filename) DO UPDATE SET
                imdb_id = :iid, title = :title, year = :year, rating = :rating,
                genre = :genre, runtime = :runtime, plot = :plot
        """),
        {
            "fn": filename, "iid": imdb_id,
            "title": info.get("Title", ""), "year": info.get("Year"),
            "rating": info.get("imdbRating"), "genre": info.get("Genre"),
            "runtime": info.get("Runtime"), "plot": info.get("Plot"),
            "ab": added_by
        }
    )
    await session.commit()


async def get_display_name(session, filename: str) -> str | None:
    from sqlalchemy import text
    result = await session.execute(
        text("SELECT display_name FROM media_imdb WHERE filename = :fn"),
        {"fn": filename}
    )
    row = result.fetchone()
    return row[0] if row and row[0] else None


async def save_display_name(session, filename: str, display_name: str, added_by: int):
    from sqlalchemy import text
    await session.execute(
        text("""
            INSERT INTO media_imdb (filename, imdb_id, display_name, added_by)
            VALUES (:fn, '', :dn, :ab)
            ON CONFLICT (filename) DO UPDATE SET display_name = :dn
        """),
        {"fn": filename, "dn": display_name, "ab": added_by}
    )
    await session.commit()
