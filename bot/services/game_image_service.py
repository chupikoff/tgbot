from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.game import GameImage

async def get_image(session: AsyncSession, key: str) -> GameImage | None:
    result = await session.execute(
        select(GameImage).where(GameImage.key == key)
    )
    return result.scalar_one_or_none()

async def set_image(session: AsyncSession, key: str, file_id: str, added_by: int) -> GameImage:
    existing = await get_image(session, key)
    if existing:
        existing.file_id = file_id
        existing.added_by = added_by
        await session.commit()
        return existing
    image = GameImage(key=key, file_id=file_id, added_by=added_by)
    session.add(image)
    await session.commit()
    await session.refresh(image)
    return image

async def get_all_images(session: AsyncSession) -> list[GameImage]:
    result = await session.execute(select(GameImage))
    return result.scalars().all()

async def delete_image(session: AsyncSession, key: str) -> bool:
    image = await get_image(session, key)
    if not image:
        return False
    await session.delete(image)
    await session.commit()
    return True
