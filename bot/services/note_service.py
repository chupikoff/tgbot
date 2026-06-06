from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from models.note import Note, Category

async def get_categories(session: AsyncSession, owner_id: int) -> list[Category]:
    result = await session.execute(
        select(Category).where(
            or_(Category.owner_id == owner_id, Category.is_shared == True)
        )
    )
    return result.scalars().all()

async def get_category(session: AsyncSession, category_id: int) -> Category | None:
    result = await session.execute(
        select(Category).where(Category.id == category_id)
    )
    return result.scalar_one_or_none()

async def create_category(session: AsyncSession, name: str, owner_id: int, is_shared: bool = False) -> Category:
    category = Category(name=name, owner_id=owner_id, is_shared=is_shared)
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category

async def delete_category(session: AsyncSession, category_id: int) -> bool:
    category = await get_category(session, category_id)
    if not category:
        return False
    await session.delete(category)
    await session.commit()
    return True

async def get_notes(session: AsyncSession, owner_id: int, is_shared: bool = False) -> list[Note]:
    if is_shared:
        result = await session.execute(
            select(Note).where(Note.is_shared == True)
        )
    else:
        result = await session.execute(
            select(Note).where(Note.owner_id == owner_id, Note.is_shared == False)
        )
    return result.scalars().all()

async def get_note(session: AsyncSession, note_id: int) -> Note | None:
    result = await session.execute(
        select(Note).where(Note.id == note_id)
    )
    return result.scalar_one_or_none()

async def create_note(
    session: AsyncSession,
    title: str,
    content: str,
    owner_id: int,
    is_shared: bool = False,
    category_id: int | None = None,
    image_file_id: str | None = None
) -> Note:
    note = Note(
        title=title,
        content=content,
        owner_id=owner_id,
        is_shared=is_shared,
        category_id=category_id,
        image_file_id=image_file_id
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note

async def update_note(
    session: AsyncSession,
    note_id: int,
    title: str | None = None,
    content: str | None = None,
    category_id: int | None = None,
    image_file_id: str | None = None,
    remove_image: bool = False
) -> Note | None:
    note = await get_note(session, note_id)
    if not note:
        return None
    if title:
        note.title = title
    if content:
        note.content = content
    if category_id is not None:
        note.category_id = category_id
    if image_file_id:
        note.image_file_id = image_file_id
    if remove_image:
        note.image_file_id = None
    await session.commit()
    return note

async def delete_note(session: AsyncSession, note_id: int) -> bool:
    note = await get_note(session, note_id)
    if not note:
        return False
    await session.delete(note)
    await session.commit()
    return True

async def search_notes(session: AsyncSession, owner_id: int, query: str) -> list[Note]:
    result = await session.execute(
        select(Note).where(
            or_(Note.owner_id == owner_id, Note.is_shared == True),
            or_(
                Note.title.ilike(f"%{query}%"),
                Note.content.ilike(f"%{query}%")
            )
        )
    )
    return result.scalars().all()
