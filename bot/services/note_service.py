from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from models.note import Note, Category


async def get_notes(session: AsyncSession, owner_id: int, is_shared: bool = False) -> list[Note]:
    if is_shared:
        result = await session.execute(select(Note).where(Note.is_shared == True).order_by(Note.created_at.desc()))
    else:
        result = await session.execute(select(Note).where(Note.owner_id == owner_id, Note.is_shared == False).order_by(Note.created_at.desc()))
    return result.scalars().all()


async def get_note(session: AsyncSession, note_id: int) -> Note | None:
    result = await session.execute(select(Note).where(Note.id == note_id))
    return result.scalar_one_or_none()


async def create_note(session: AsyncSession, title: str, content: str, owner_id: int,
                      is_shared: bool = False, category_id: int | None = None,
                      image_file_id: str | None = None) -> Note:
    note = Note(title=title, content=content, owner_id=owner_id,
                is_shared=is_shared, category_id=category_id, image_file_id=image_file_id)
    session.add(note)
    await session.commit()
    return note


async def update_note(session: AsyncSession, note_id: int, title: str | None = None,
                      content: str | None = None, image_file_id: str | None = None,
                      remove_image: bool = False, category_id: int = -1) -> Note:
    note = await get_note(session, note_id)
    if title:
        note.title = title
    if content:
        note.content = content
    if remove_image:
        note.image_file_id = None
    elif image_file_id:
        note.image_file_id = image_file_id
    if category_id != -1:
        note.category_id = category_id if category_id != 0 else None
    await session.commit()
    return note


async def delete_note(session: AsyncSession, note_id: int):
    note = await get_note(session, note_id)
    if note:
        await session.delete(note)
        await session.commit()


async def get_categories(session: AsyncSession, owner_id: int) -> list[Category]:
    result = await session.execute(
        select(Category).where(or_(Category.owner_id == owner_id, Category.is_shared == True))
        .order_by(Category.name)
    )
    return result.scalars().all()


async def get_category(session: AsyncSession, cat_id: int) -> Category | None:
    result = await session.execute(select(Category).where(Category.id == cat_id))
    return result.scalar_one_or_none()


async def create_category(session: AsyncSession, name: str, owner_id: int, is_shared: bool = False) -> Category:
    cat = Category(name=name, owner_id=owner_id, is_shared=is_shared)
    session.add(cat)
    await session.commit()
    return cat


async def delete_category(session: AsyncSession, cat_id: int):
    cat = await get_category(session, cat_id)
    if cat:
        await session.delete(cat)
        await session.commit()


async def search_notes(session: AsyncSession, owner_id: int, query: str) -> list[Note]:
    result = await session.execute(
        select(Note).where(
            or_(Note.owner_id == owner_id, Note.is_shared == True),
            or_(Note.title.ilike(f"%{query}%"), Note.content.ilike(f"%{query}%"))
        ).order_by(Note.created_at.desc())
    )
    return result.scalars().all()
