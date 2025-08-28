"""
Task display and formatting functions.

This module contains all functions responsible for displaying task-related
information, status updates, results, and user interface formatting.
"""

from textwrap import dedent
from typing import Optional
from aiogram.types import Message

from shared.db import get_user_tasks, list_recent_analyses_for_user, TaskStatus
from bot.handlers.utils.messages import send_or_edit_message, safe_message_from_callback
from bot.handlers.utils.ui import (
    get_status_emoji,
    get_plan_display_name,
    create_status_keyboard,
    create_empty_state_keyboard,
    create_result_detail_keyboard,
    create_source_keyboard,
    create_task_details_keyboard,
)
from bot.handlers.utils.pagination import TaskPaginationHandler, ResultsPaginationHandler
from bot.handlers.utils.utils import escape_html, cut_text
from shared.logging import get_logger

logger = get_logger(__name__)


async def show_detailed_status(
    message: Message, user, *, edit_mode: bool = False, navigation_context: bool = False, function_context_key: Optional[str] = None
) -> None:
    """Show detailed interactive status.

    :param message: Telegram message
    :param user: User object
    :param edit_mode: If True, edit existing message instead of sending new one
    :param navigation_context: If True, use navigation context for message handling
    :param function_context_key: Key for function-specific message tracking
    """
    user_tasks = await get_user_tasks(user.id)

    if not user_tasks:
        status_text = '📊 <b>No tasks yet</b>\n\nPress "🔬 New Task" to get started!'
        keyboard = create_empty_state_keyboard()

        await send_or_edit_message(
            message, status_text, keyboard, edit_mode,
            navigation_context=navigation_context,
            function_context_key=function_context_key
        )
        return

    # Group tasks by status
    active_tasks = [
        t for t in user_tasks if t.status in [TaskStatus.QUEUED, TaskStatus.PROCESSING]
    ]
    paused_tasks = [t for t in user_tasks if t.status == TaskStatus.PAUSED]
    cancelled_tasks = [t for t in user_tasks if t.status == TaskStatus.CANCELLED]
    completed_tasks = [t for t in user_tasks if t.status == TaskStatus.COMPLETED]
    failed_tasks = [t for t in user_tasks if t.status == TaskStatus.FAILED]

    # Create status text
    status_text = "📊 <b>Tasks Dashboard</b>\n\n"

    # Account summary
    status_text += f"👤 <b>Account:</b> {get_plan_display_name(user.plan)}\n"
    status_text += (
        f"📈 <b>Usage:</b> {user.daily_tasks_created}/{user.daily_task_limit} daily\n\n"
    )

    # Active tasks with detailed info
    if active_tasks:
        status_text += "🔄 <b>Active Tasks:</b>\n"
        for task in active_tasks[:5]:
            emoji = get_status_emoji(task.status)
            status_text += f"{emoji} <b>#{task.id}</b>: {escape_html(cut_text(task.description, 40))}\n"

            # Add agent activity info
            if task.status == TaskStatus.PROCESSING:
                status_text += (
                    "   🤖 <i>Searching databases and analyzing papers...</i>\n"
                )
                # Estimate next result based on cycles
                if task.cycles_completed < task.max_cycles:
                    cycles_left = task.max_cycles - task.cycles_completed
                    status_text += f"   📊 Progress: {task.cycles_completed}/{task.max_cycles} cycles\n"
                    if cycles_left <= 3:
                        status_text += "   ⏱️ <i>Final results coming soon!</i>\n"
                    else:
                        est_minutes = cycles_left * 2  # Rough estimate
                        status_text += (
                            f"   ⏱️ <i>Next update in ~{est_minutes} minutes</i>\n"
                        )
            elif task.status == TaskStatus.QUEUED:
                status_text += "   ⏳ <i>Waiting in queue...</i>\n"

            status_text += "\n"
    else:
        status_text += "🔄 <b>No active tasks</b>\n\n"

    # Show paused tasks
    if paused_tasks:
        status_text += "⏸️ <b>Paused Tasks:</b>\n"
        for task in paused_tasks[:3]:  # Show first 3 paused tasks
            emoji = get_status_emoji(task.status)
            status_text += f"{emoji} <b>#{task.id}</b>: {escape_html(cut_text(task.description, 40))}\n"
            status_text += "   ⏸️ <i>Task is paused</i>\n\n"

    # Show cancelled tasks
    if cancelled_tasks:
        status_text += "🚫 <b>Cancelled Tasks:</b>\n"
        for task in cancelled_tasks[:3]:  # Show first 3 cancelled tasks
            emoji = get_status_emoji(task.status)
            status_text += f"{emoji} <b>#{task.id}</b>: {escape_html(cut_text(task.description, 40))}\n"
            status_text += "   🚫 <i>Task was cancelled</i>\n\n"

    # Summary stats
    if completed_tasks or failed_tasks or paused_tasks or cancelled_tasks:
        status_text += "📈 <b>Summary:</b>\n"
        if active_tasks:
            status_text += f"   🔄 Active: {len(active_tasks)}\n"
        if paused_tasks:
            status_text += f"   ⏸️ Paused: {len(paused_tasks)}\n"
        if cancelled_tasks:
            status_text += f"   🚫 Cancelled: {len(cancelled_tasks)}\n"
        if completed_tasks:
            status_text += f"   ✅ Completed: {len(completed_tasks)}\n"
        if failed_tasks:
            status_text += f"   ❌ Failed: {len(failed_tasks)}\n"

    keyboard = create_status_keyboard(active_tasks, completed_tasks, paused_tasks, cancelled_tasks)

    await send_or_edit_message(message, status_text, keyboard, edit_mode, navigation_context=navigation_context)


async def show_task_selection(
    message: Message, user, page: int = 0, *, edit_mode: bool = False, navigation_context: bool = False
) -> None:
    """Show task selection for viewing results.

    :param message: Telegram message
    :param user: User object
    :param page: Page number for pagination
    :param edit_mode: If True, edit existing message instead of sending new one
    :param navigation_context: If True, use navigation context for message handling
    """
    # Get user tasks
    user_tasks = await get_user_tasks(user.id)

    if not user_tasks:
        text = "📚 <b>No tasks yet</b>\n\nCreate a task and wait for findings!"
        keyboard = create_empty_state_keyboard()

        await send_or_edit_message(message, text, keyboard, edit_mode, navigation_context=navigation_context)
        return

    # Create task pagination handler
    task_pagination = TaskPaginationHandler(user_tasks)
    text, keyboard = task_pagination.get_page_data(page)

    await send_or_edit_message(message, text, keyboard, edit_mode, navigation_context=navigation_context)


async def show_task_results(
    message: Message, user, task_id: int, page: int = 0, *, edit_mode: bool = False, navigation_context: bool = False
) -> None:
    """Show results for a specific task.

    :param message: Telegram message
    :param user: User object
    :param task_id: Task ID to show results for
    :param page: Page number for pagination
    :param edit_mode: If True, edit existing message instead of sending new one
    :param navigation_context: If True, use navigation context for message handling
    """
    # Get results for specific task
    try:
        # Try old system first (ResearchTopic) - this is what agent currently uses
        all_analyses = await list_recent_analyses_for_user(user.id, limit=100)

        # For now, show all analyses since task_id filtering might not be available
        # This can be improved when the data model supports it
        task_analyses = all_analyses

        # If no results in old system, try new system (UserTask + Finding)
        if not task_analyses:
            try:
                # Import here to avoid circular imports
                from shared.db import get_user_task_results

                task_analyses = await get_user_task_results(task_id)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"Error getting task results: {e}")
        task_analyses = []

    if not task_analyses:
        text = f"📚 <b>No results for Task #{task_id}</b>\n\nThis task may still be processing or has no findings yet."
        keyboard = create_empty_state_keyboard()

        await send_or_edit_message(message, text, keyboard, edit_mode, navigation_context=navigation_context)
        return

    # Create results pagination handler
    results_pagination = ResultsPaginationHandler(task_analyses)
    text, keyboard = results_pagination.get_page_data(page)

    await send_or_edit_message(message, text, keyboard, edit_mode, navigation_context=navigation_context)


async def show_individual_result(
    message: Message, analysis, paper, result_idx: int
) -> None:
    """Show individual result in detailed view.

    :param message: Telegram message
    :param analysis: Analysis object
    :param paper: Paper object
    :param result_idx: Result index for navigation
    """
    # Create AI summary format
    result_text = f"🔬 <b>Research Finding #{result_idx + 1}</b>\n\n"

    # Paper title and relevance
    result_text += f"📄 <b>{escape_html(paper.title)}</b>\n"
    result_text += f"📊 <b>Relevance:</b> {analysis.relevance:.1f}%\n\n"

    # AI Summary (use analysis summary or create from paper)
    if analysis.summary:
        result_text += "🤖 <b>AI Summary:</b>\n"
        result_text += f"<i>{escape_html(analysis.summary)}</i>\n\n"
    elif hasattr(paper, "abstract") and paper.abstract:
        result_text += "📝 <b>Abstract:</b>\n"
        result_text += f"<i>{escape_html(cut_text(paper.abstract, 300))}</i>\n\n"

    # Authors and metadata
    if hasattr(paper, "authors") and paper.authors:
        authors_text = ", ".join(paper.authors[:3])  # Show first 3 authors
        if len(paper.authors) > 3:
            authors_text += f" + {len(paper.authors) - 3} more"
        result_text += f"👥 <b>Authors:</b> {escape_html(authors_text)}\n"

    if hasattr(paper, "published_date") and paper.published_date:
        result_text += (
            f"📅 <b>Published:</b> {paper.published_date.strftime('%Y-%m-%d')}\n"
        )

    # Analysis metadata
    result_text += (
        f"🕐 <b>Found:</b> {analysis.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    )

    keyboard = create_result_detail_keyboard(result_idx)

    message_obj = safe_message_from_callback(message)
    if message_obj:
        await send_or_edit_message(message_obj, result_text, keyboard, navigation_context=True)


async def show_additional_sources(message: Message, paper, result_idx: int) -> None:
    """Show additional source options for a paper.

    :param message: Telegram message
    :param paper: Paper object
    :param result_idx: Result index for navigation
    """
    sources_text = f"🔍 <b>Additional Sources for Result #{result_idx + 1}</b>\n\n"
    sources_text += f"📄 <b>{escape_html(paper.title)}</b>\n\n"

    # Create additional source buttons
    keyboard = create_source_keyboard(
        result_idx=result_idx,
        arxiv_id=getattr(paper, "arxiv_id", None),
        doi=getattr(paper, "doi", None),
        pmid=getattr(paper, "pmid", None),
        title=getattr(paper, "title", None),
    )

    message_obj = safe_message_from_callback(message)
    if message_obj:
        await send_or_edit_message(message_obj, sources_text, keyboard, navigation_context=True)


async def show_task_details(message: Message, user, task_id: int) -> None:
    """Show detailed information about a specific task.

    :param message: Telegram message
    :param user: User object
    :param task_id: Task ID to show details for
    """
    # Get task details
    user_tasks = await get_user_tasks(user.id)
    task = next((t for t in user_tasks if t.id == task_id), None)

    if not task:
        await send_or_edit_message(message, "❌ Task not found.")
        return

    # Create detailed task information
    from shared.db import get_user_task_results

    task_results = await get_user_task_results(task_id)
    results_count = len(task_results) if task_results else 0

    details_text = dedent(f"""
    📋 <b>Task Details #{task.id}</b>

    <b>Description:</b> {escape_html(task.description)}
    <b>Status:</b> {get_status_emoji(task.status)} {task.status}
    <b>Created:</b> {task.created_at.strftime('%Y-%m-%d %H:%M')}
    <b>Results found:</b> {results_count}
    """)

    if task.status == TaskStatus.PROCESSING:
        details_text += (
            f"\n<b>Progress:</b> Cycle {task.cycles_completed}/{task.max_cycles}"
        )

    # Create keyboard with actions
    has_results = (
        task.status in [TaskStatus.COMPLETED, TaskStatus.PROCESSING]
        and results_count > 0
    )
    keyboard = create_task_details_keyboard(task_id, has_results, task.status)

    await send_or_edit_message(message, details_text, keyboard, navigation_context=True)
