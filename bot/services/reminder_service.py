from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.reminder import Reminder
from datetime import datetime


async def get_reminders(session: AsyncSession, owner_id: int) -> list[Reminder]:
    result = await session.execute(
        select(Reminder).where(Reminder.owner_id == owner_id, Reminder.is_sent == False)
        .order_by(Reminder.remind_at)
    )
    return result.scalars().all()


async def get_reminder(session: AsyncSession, reminder_id: int) -> Reminder | None:
    result = await session.execute(select(Reminder).where(Reminder.id == reminder_id))
    return result.scalar_one_or_none()


async def create_reminder(session: AsyncSession, owner_id: int, text: str, remind_at: datetime) -> Reminder:
    reminder = Reminder(owner_id=owner_id, text=text, remind_at=remind_at)
    session.add(reminder)
    await session.commit()
    return reminder


async def delete_reminder(session: AsyncSession, reminder_id: int):
    reminder = await get_reminder(session, reminder_id)
    if reminder:
        await session.delete(reminder)
        await session.commit()


async def get_pending_reminders(session: AsyncSession) -> list[Reminder]:
    result = await session.execute(
        select(Reminder).where(Reminder.is_sent == False, Reminder.remind_at <= datetime.now())
    )
    return result.scalars().all()


async def mark_sent(session: AsyncSession, reminder: Reminder):
    reminder.is_sent = True
    await session.commit()
