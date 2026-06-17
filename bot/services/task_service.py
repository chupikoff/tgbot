from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.task import Task


async def get_tasks(session: AsyncSession, owner_id: int) -> list[Task]:
    result = await session.execute(
        select(Task).where(Task.owner_id == owner_id).order_by(Task.is_done, Task.created_at.desc())
    )
    return result.scalars().all()


async def get_task(session: AsyncSession, task_id: int) -> Task | None:
    result = await session.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def create_task(session: AsyncSession, owner_id: int, text: str) -> Task:
    task = Task(owner_id=owner_id, text=text)
    session.add(task)
    await session.commit()
    return task


async def toggle_task(session: AsyncSession, task_id: int) -> Task:
    task = await get_task(session, task_id)
    task.is_done = not task.is_done
    await session.commit()
    return task


async def delete_task(session: AsyncSession, task_id: int):
    task = await get_task(session, task_id)
    if task:
        await session.delete(task)
        await session.commit()
