from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.media import Media, MediaCategory

async def get_all_media(session: AsyncSession, category_id: int | None = None) -> list[Media]:
    query = select(Media).order_by(Media.created_at.desc())
    if category_id is not None:
        query = query.where(Media.category_id == category_id)
    result = await session.execute(query)
    return result.scalars().all()

async def get_media(session: AsyncSession, media_id: int) -> Media | None:
    result = await session.execute(
        select(Media).where(Media.id == media_id)
    )
    return result.scalar_one_or_none()

async def add_media(
    session: AsyncSession,
    title: str,
    file_id: str,
    file_type: str,
    added_by: int,
    description: str | None = None,
    category_id: int | None = None
) -> Media:
    media = Media(
        title=title,
        file_id=file_id,
        file_type=file_type,
        added_by=added_by,
        description=description,
        category_id=category_id
    )
    session.add(media)
    await session.commit()
    await session.refresh(media)
    return media

async def update_media(
    session: AsyncSession,
    media_id: int,
    title: str | None = None,
    description: str | None = None,
    file_id: str | None = None,
    category_id: int | None = None,
) -> Media | None:
    media = await get_media(session, media_id)
    if not media:
        return None
    if title:
        media.title = title
    if description is not None:
        media.description = description
    if file_id:
        media.file_id = file_id
    if category_id is not None:
        media.category_id = category_id
    await session.commit()
    return media

async def delete_media(session: AsyncSession, media_id: int) -> bool:
    media = await get_media(session, media_id)
    if not media:
        return False
    await session.delete(media)
    await session.commit()
    return True

async def search_media(session: AsyncSession, query: str) -> list[Media]:
    result = await session.execute(
        select(Media).where(Media.title.ilike(f"%{query}%"))
    )
    return result.scalars().all()

async def get_all_categories(session: AsyncSession) -> list[MediaCategory]:
    result = await session.execute(
        select(MediaCategory).order_by(MediaCategory.name)
    )
    return result.scalars().all()

async def get_category(session: AsyncSession, category_id: int) -> MediaCategory | None:
    result = await session.execute(
        select(MediaCategory).where(MediaCategory.id == category_id)
    )
    return result.scalar_one_or_none()

async def create_category(session: AsyncSession, name: str, created_by: int) -> MediaCategory:
    cat = MediaCategory(name=name, created_by=created_by)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat

async def delete_category(session: AsyncSession, category_id: int) -> bool:
    cat = await get_category(session, category_id)
    if not cat:
        return False
    await session.delete(cat)
    await session.commit()
    return True
