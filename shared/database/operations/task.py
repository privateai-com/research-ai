"""Task management operations."""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from ..connection import SessionLocal
from ..models import User, UserTask, TaskQueue
from ..enums import UserPlan, TaskStatus
from .queue import add_task_to_queue

logger = logging.getLogger(__name__)


async def create_user_task_with_queue(
    user: User, description: str
) -> Tuple[UserTask, TaskQueue]:
    """Create a new user task and add it to the processing queue.

    :param user: User instance
    :param description: Task description
    :returns: Tuple of (UserTask, TaskQueue)
    """
    async with SessionLocal() as session:
        max_cycles = 100 if user.plan == UserPlan.PREMIUM else 5

        task = UserTask(
            user_id=user.id,
            title=description[:100] + "..." if len(description) > 100 else description,
            description=description,
            status=TaskStatus.QUEUED,
            max_cycles=max_cycles,
        )

        session.add(task)
        await session.commit()
        await session.refresh(task)

        queue_entry = await add_task_to_queue(task)

        user.daily_tasks_created += 1
        user.updated_at = datetime.now()
        await session.merge(user)
        await session.commit()

        return task, queue_entry


async def get_user_tasks(user_id: int) -> List[UserTask]:
    """Get all tasks for a user with eager loading to avoid lazy loading issues.

    :param user_id: Internal user ID
    :returns: List of UserTask instances
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserTask)
            .options(selectinload(UserTask.queue_entry))
            .where(UserTask.user_id == user_id)
            .order_by(UserTask.created_at.desc())
        )
        return list(result.scalars().all())


async def update_user_task_status(task_id: int, status: TaskStatus) -> None:
    """Update task status.

    :param task_id: Task ID
    :param status: New status
    """
    async with SessionLocal() as session:
        task = await session.get(UserTask, task_id)
        if task is None:
            return
        task.status = status
        task.updated_at = datetime.now()
        await session.commit()


async def update_user_task_status_for_user(
    user_id: int, task_id: int, status: TaskStatus
) -> bool:
    """Safely update task status ensuring ownership by user.

    :param user_id: Internal user ID
    :param task_id: Task ID
    :param status: New status
    :returns: True if updated successfully, False if user not found
    """
    async with SessionLocal() as session:
        task = await session.get(UserTask, task_id)
        if task is None or task.user_id != user_id:
            return False
        task.status = status
        task.updated_at = datetime.now()
        await session.commit()
        return True


async def deactivate_user_tasks(user_id: int) -> None:
    """Deactivate all active tasks for a user.

    :param user_id: Internal user ID
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserTask).where(
                and_(UserTask.user_id == user_id, UserTask.status == TaskStatus.ACTIVE)
            )
        )
        tasks = result.scalars().all()
        for t in tasks:
            t.status = TaskStatus.PAUSED
            t.updated_at = datetime.now()
        await session.commit()


async def list_active_user_tasks() -> List[UserTask]:
    """List all active user tasks.

    :returns: List of active UserTask instances
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserTask)
            .where(UserTask.status == TaskStatus.ACTIVE)
            .order_by(UserTask.created_at.asc())
        )
        return list(result.scalars().all())


async def get_most_recent_active_user_task() -> Optional[UserTask]:
    """Return the most recently updated active user task, or None if none exist.

    :returns: A single UserTask instance or None when no active tasks.
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserTask)
            .where(UserTask.status == TaskStatus.ACTIVE)
            .order_by(UserTask.updated_at.desc(), UserTask.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()


async def list_user_tasks(user_id: int) -> List[UserTask]:
    """List all tasks for a user.

    :param user_id: Internal user ID
    :returns: List of UserTask instances
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserTask)
            .where(UserTask.user_id == user_id)
            .order_by(UserTask.created_at.desc())
        )
        return list(result.scalars().all())


async def cancel_user_task(user_id: int, task_id: int) -> bool:
    """Cancel a user task if it belongs to the user and is in cancellable state.

    :param user_id: Internal user ID
    :param task_id: Task ID to cancel
    :returns: True if cancelled successfully, False otherwise
    """
    try:
        async with SessionLocal() as session:
            stmt = (
                select(UserTask)
                .options(selectinload(UserTask.queue_entry))
                .where(UserTask.id == task_id)
            )
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if task is None or task.user_id != user_id:
                return False

            if task.status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                return False

            task.status = TaskStatus.CANCELLED
            task.processing_completed_at = datetime.now()
            task.updated_at = datetime.now()

            if task.queue_entry:
                await session.delete(task.queue_entry)

            await session.commit()
            return True
    except Exception as e:
        logger.error(
            f"Error in cancel_user_task for user {user_id}, task {task_id}: {e}",
            exc_info=True,
        )
        return False


def cancel_user_task_sync(user_id: int, task_id: int) -> bool:
    """Synchronous version of cancel_user_task for use in callback handlers.

    :param user_id: Internal user ID
    :param task_id: Task ID to cancel
    :returns: True if cancelled successfully, False otherwise
    """
    try:
        import asyncio

        try:
            asyncio.get_running_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, cancel_user_task(user_id, task_id)
                )
                return future.result()
        except RuntimeError:
            return asyncio.run(cancel_user_task(user_id, task_id))

    except Exception as e:
        logger.error(
            f"Error in cancel_user_task_sync for user {user_id}, task {task_id}: {e}",
            exc_info=True,
        )
        return False


def pause_user_task_sync(user_id: int, task_id: int) -> bool:
    """Synchronous version of pause_user_task for use in callback handlers.

    :param user_id: Internal user ID
    :param task_id: Task ID to pause
    :returns: True if paused successfully, False otherwise
    """
    try:
        import asyncio

        try:
            asyncio.get_running_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, pause_user_task(user_id, task_id))
                return future.result()
        except RuntimeError:
            return asyncio.run(pause_user_task(user_id, task_id))

    except Exception as e:
        logger.error(
            f"Error in pause_user_task_sync for user {user_id}, task {task_id}: {e}",
            exc_info=True,
        )
        return False


async def pause_user_task(user_id: int, task_id: int) -> bool:
    """Pause a user task if it belongs to the user and is in pausable state.

    :param user_id: Internal user ID
    :param task_id: Task ID to pause
    :returns: True if paused successfully, False otherwise
    """
    try:
        async with SessionLocal() as session:
            stmt = (
                select(UserTask)
                .options(selectinload(UserTask.queue_entry))
                .where(UserTask.id == task_id)
            )
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if task is None or task.user_id != user_id:
                return False

            if task.status not in [TaskStatus.PROCESSING, TaskStatus.QUEUED]:
                return False

            task.status = TaskStatus.PAUSED
            task.updated_at = datetime.now()

            if task.queue_entry:
                await session.delete(task.queue_entry)

            await session.commit()
            return True
    except Exception as e:
        logger.error(
            f"Error in pause_user_task for user {user_id}, task {task_id}: {e}",
            exc_info=True,
        )
        return False


async def resume_user_task(user_id: int, task_id: int) -> bool:
    """Resume a paused user task.

    :param user_id: Internal user ID
    :param task_id: Task ID to resume
    :returns: True if resumed successfully, False otherwise
    """
    try:
        async with SessionLocal() as session:
            task = await session.get(UserTask, task_id)
            if task is None or task.user_id != user_id:
                return False

            if task.status != TaskStatus.PAUSED:
                return False

            task.status = TaskStatus.QUEUED
            task.updated_at = datetime.now()

            from .queue import add_task_to_queue

            await add_task_to_queue(task)

            await session.commit()
            return True
    except Exception as e:
        logger.error(
            f"Error in resume_user_task for user {user_id}, task {task_id}: {e}",
            exc_info=True,
        )
        return False


def resume_user_task_sync(user_id: int, task_id: int) -> bool:
    """Synchronous version of resume_user_task for use in callback handlers.

    :param user_id: Internal user ID
    :param task_id: Task ID to resume
    :returns: True if resumed successfully, False otherwise
    """
    try:
        import asyncio

        try:
            asyncio.get_running_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, resume_user_task(user_id, task_id)
                )
                return future.result()
        except RuntimeError:
            return asyncio.run(resume_user_task(user_id, task_id))

    except Exception as e:
        logger.error(
            f"Error in resume_user_task_sync for user {user_id}, task {task_id}: {e}",
            exc_info=True,
        )
        return False


async def cancel_all_user_tasks(user_id: int) -> int:
    """Cancel all active tasks for a user.

    :param user_id: Internal user ID
    :returns: Number of tasks cancelled
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserTask)
            .options(selectinload(UserTask.queue_entry))
            .where(
                and_(
                    UserTask.user_id == user_id,
                    UserTask.status.in_([TaskStatus.QUEUED, TaskStatus.PROCESSING]),
                )
            )
        )
        tasks = result.scalars().all()

        cancelled_count = 0
        for task in tasks:
            task.status = TaskStatus.CANCELLED
            task.processing_completed_at = datetime.now()
            task.updated_at = datetime.now()

            if task.queue_entry:
                await session.delete(task.queue_entry)

            cancelled_count += 1

        await session.commit()
        return cancelled_count
