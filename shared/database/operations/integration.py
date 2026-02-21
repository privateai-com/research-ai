"""Integration operations between bot and agent systems."""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, and_

from ..connection import SessionLocal
from ..models import (
    User,
    UserTask,
    TaskQueue,
    ResearchTopic,
    Finding,
    PaperAnalysis,
    ArxivPaper,
)
from ..enums import TaskStatus, UserPlan
from .generic_task import create_task


async def get_next_queued_task() -> Optional[UserTask]:
    """Get next task from queue for agent processing.

    This function bridges the new UserTask/TaskQueue system with the agent.

    :returns: Next UserTask ready for processing or None if queue is empty
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserTask)
            .join(TaskQueue)
            .where(UserTask.status == TaskStatus.QUEUED)
            .order_by(TaskQueue.priority.asc(), TaskQueue.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def start_task_processing(task_id: int) -> bool:
    """Start processing a queued task.

    Updates task status to PROCESSING and records start time.

    :param task_id: Task ID
    :returns: True if successfully started, False if task not found or already processing
    """
    async with SessionLocal() as session:
        task = await session.get(UserTask, task_id)
        if task is None or task.status != TaskStatus.QUEUED:
            return False

        task.status = TaskStatus.PROCESSING
        task.processing_started_at = datetime.now()
        task.updated_at = datetime.now()

        queue_result = await session.execute(
            select(TaskQueue).where(TaskQueue.task_id == task.id)
        )
        queue_entry = queue_result.scalar_one_or_none()
        if queue_entry:
            queue_entry.started_at = datetime.now()
            queue_entry.updated_at = datetime.now()

        await session.commit()
        return True


async def complete_task_processing(
    task_id: int, success: bool = True, error_message: Optional[str] = None
) -> bool:
    """Complete task processing and update status.

    :param task_id: Task ID
    :param success: Whether task completed successfully
    :param error_message: Error message if task failed
    :returns: True if successfully completed
    """
    async with SessionLocal() as session:
        task = await session.get(UserTask, task_id)
        if task is None:
            return False

        processing_time = 0.0
        if task.processing_started_at:
            end_time = datetime.now()
            processing_time = (end_time - task.processing_started_at).total_seconds()

        queue_result = await session.execute(
            select(TaskQueue).where(TaskQueue.task_id == task.id)
        )
        queue_entry = queue_result.scalar_one_or_none()

        if success:
            task.cycles_completed = task.cycles_completed + 1

            if task.cycles_completed >= task.max_cycles:
                task.status = TaskStatus.COMPLETED
                task.processing_completed_at = datetime.now()

                if queue_entry:
                    await session.delete(queue_entry)

                results = await get_user_task_results(task.id)
                has_results = len(results) > 0

                await _notify_cycle_limit_reached(task, has_results)
            else:
                task.status = TaskStatus.QUEUED

                if queue_entry:
                    queue_entry.worker_id = None
                    queue_entry.started_at = None
                    queue_entry.updated_at = datetime.now()
        else:
            task.status = TaskStatus.FAILED
            task.processing_completed_at = datetime.now()
            task.error_message = error_message

            if queue_entry:
                await session.delete(queue_entry)

        task.updated_at = datetime.now()

        await session.commit()

        from .task_statistics import update_task_statistics

        await update_task_statistics(processing_time, success)

        return True


async def create_research_topic_for_user_task(
    user_task: UserTask,
) -> Optional[ResearchTopic]:
    """Create a ResearchTopic from UserTask for agent compatibility.

    This bridges the new UserTask system with the legacy ResearchTopic system
    that the agent pipeline expects.

    :param user_task: UserTask instance
    :returns: ResearchTopic instance or None if user not found
    """
    async with SessionLocal() as session:
        # Get user by internal ID
        user = await session.get(User, user_task.user_id)
        if user is None:
            return None

        existing_result = await session.execute(
            select(ResearchTopic).where(
                and_(
                    ResearchTopic.user_id == user.telegram_id,
                    ResearchTopic.target_topic == user_task.description,
                    ResearchTopic.is_active,
                )
            )
        )
        existing_topic = existing_result.scalar_one_or_none()

        if existing_topic:
            return existing_topic

        topic = ResearchTopic(
            user_id=user.telegram_id,
            target_topic=user_task.description,
            search_area=user_task.title or user_task.description[:100],
            is_active=True,
        )

        session.add(topic)
        await session.commit()
        await session.refresh(topic)

        return topic


async def link_analysis_to_user_task(
    analysis: PaperAnalysis, user_task: UserTask
) -> None:
    """Link a paper analysis to a user task for proper result tracking.

    Creates a Finding record that connects the analysis to the user's task.

    :param analysis: PaperAnalysis instance
    :param user_task: UserTask instance
    """
    async with SessionLocal() as session:
        finding = Finding(
            task_id=user_task.id,
            paper_id=analysis.paper_id,
            relevance=analysis.relevance,
            summary=analysis.summary,
        )

        session.add(finding)
        await session.commit()


async def get_user_task_results(task_id: int) -> List[Tuple[PaperAnalysis, ArxivPaper]]:
    """Get analysis results for a user task.

    :param task_id: UserTask ID
    :returns: List of (PaperAnalysis, ArxivPaper) tuples
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(PaperAnalysis, ArxivPaper)
            .join(Finding, PaperAnalysis.paper_id == Finding.paper_id)
            .join(ArxivPaper, PaperAnalysis.paper_id == ArxivPaper.id)
            .where(Finding.task_id == task_id)
            .order_by(PaperAnalysis.relevance.desc())
        )
        rows = result.all()
        return [(row[0], row[1]) for row in rows]


async def create_user_task(user_id: int, description: str) -> UserTask:
    """Create a user task (legacy function for compatibility).

    :param user_id: Telegram user ID (will be converted to internal user ID)
    :param description: Task description
    :returns: UserTask instance
    """
    from .user import get_or_create_user

    user = await get_or_create_user(telegram_id=user_id)

    from .task import create_user_task_with_queue

    task, _ = await create_user_task_with_queue(user, description)
    return task


async def cleanup_orphaned_queue_entries() -> int:
    """Clean up queue entries for tasks that are already completed or failed.

    This function should be called on agent startup to remove stale queue entries
    that may have been left behind from previous runs.

    :returns: Number of orphaned entries cleaned up.
    """
    async with SessionLocal() as session:
        result = await session.execute(
            select(TaskQueue)
            .join(UserTask)
            .where(UserTask.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED]))
        )
        orphaned_entries = list(result.scalars().all())

        for entry in orphaned_entries:
            await session.delete(entry)

        await session.commit()
        return len(orphaned_entries)


async def _notify_cycle_limit_reached(user_task: UserTask, has_results: bool) -> None:
    """Send notification to user when cycle limit is reached.

    :param user_task: The completed user task
    :param has_results: Whether the task produced any results
    """
    async with SessionLocal() as session:
        user = await session.get(User, user_task.user_id)
        if user is None:
            return

        telegram_id = user.telegram_id
        plan_name = "Premium" if user.plan == UserPlan.PREMIUM else "Free"

        if has_results:
            message = f"""
🎉 <b>Task #{user_task.id} completed!</b>

✅ <b>Results found for your query:</b>
📝 <i>{user_task.description[:100]}{"..." if len(user_task.description) > 100 else ""}</i>

🔄 <b>Cycles completed:</b> {user_task.cycles_completed}/{user_task.max_cycles} (Plan: {plan_name})

🤖 Hope the results were helpful! 

💡 <b>Want to continue research?</b>
• Create a new task with a refined query
• Or get a Premium subscription for unlimited search cycles

Use /task to create a new task or /status to view results.
            """.strip()
        else:
            message = f"""
🔄 <b>Task #{user_task.id} completed</b>

📝 <i>{user_task.description[:100]}{"..." if len(user_task.description) > 100 else ""}</i>

🔄 <b>Cycles completed:</b> {user_task.cycles_completed}/{user_task.max_cycles} (Plan: {plan_name})

❌ <b>Unfortunately, no results found for this query.</b>

💡 <b>Recommendations:</b>
• Try reformulating the query more specifically
• Use different keywords
• Or get a Premium subscription for more search cycles

Use /task to create a new task with a refined query.
            """.strip()

        data = {"task_type": "cycle_limit_notification", "user_id": telegram_id}
        await create_task(
            task_type="cycle_limit_notification",
            data=data,
            status="completed",
            result=message,
        )
