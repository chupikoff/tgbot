from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.media import Media

async def get_all_media(session: AsyncSession) -> list[Media]:
    result = await session.execute(
        select(Media).order_by(Media.created_at.desc())
    )
    return result.scalars().all()

async def get_media(session: AsyncSession, media_id: int) -> Media | None:
    result = await session.execute(
        select(Media).where(Media.id == media_id)
    )
    return result.scalar_one_or_none()

async def add_media(session: AsyncSession, title: str, file_id: str, file_type: str, added_by: int) -> Media:
    media = Media(
        title=title,
        file_id=file_id,
        file_type=file_type,
        added_by=added_by
    )
    session.add(media)
    await session.commit()
    await session.refresh(media)
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
