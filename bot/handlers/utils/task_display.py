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
    create_task_details_keyboard,
)
from bot.handlers.utils.pagination import (
    TaskPaginationHandler,
    ResultsPaginationHandler,
)
from bot.handlers.utils.utils import escape_html, cut_text
from shared.logging import get_logger

logger = get_logger(__name__)


async def show_detailed_status(
    message: Message,
    user,
    *,
    edit_mode: bool = False,
    navigation_context: bool = False,
    function_context_key: Optional[str] = None,
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
            message,
            status_text,
            keyboard,
            edit_mode,
            navigation_context=navigation_context,
            function_context_key=function_context_key,
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

    # Create enhanced status text
    status_text = "📊 <b>Research Tasks Dashboard</b>\n\n"

    # Account summary with enhanced formatting
    status_text += f"👤 <b>Account:</b> {get_plan_display_name(user.plan)}\n"

    # Usage indicator with progress bar
    usage_percentage = (
        (user.daily_tasks_created / user.daily_task_limit) * 100
        if user.daily_task_limit > 0
        else 0
    )
    usage_bar = "🟩" * min(10, int(usage_percentage / 10)) + "⬜" * max(
        0, 10 - int(usage_percentage / 10)
    )
    status_text += f"📈 <b>Daily Usage:</b> {user.daily_tasks_created}/{user.daily_task_limit} {usage_bar}\n\n"

    # Active tasks with enhanced detailed info
    if active_tasks:
        status_text += "🔄 <b>Active Tasks:</b>\n"
        for task in active_tasks[:5]:
            emoji = get_status_emoji(task.status)
            status_text += f"{emoji} <b>#{task.id}:</b> {escape_html(cut_text(task.description, 35))}\n"

            # Add enhanced agent activity info
            if task.status == TaskStatus.PROCESSING:
                status_text += "   🤖 <i>AI agent actively researching...</i>\n"

                # Progress bar for cycles
                if (
                    hasattr(task, "cycles_completed")
                    and hasattr(task, "max_cycles")
                    and task.max_cycles > 0
                ):
                    cycles_completed = getattr(task, "cycles_completed", 0)
                    max_cycles = getattr(task, "max_cycles", 1)
                    progress_pct = (cycles_completed / max_cycles) * 100
                    progress_bars = int(progress_pct / 10)
                    progress_display = "🟩" * progress_bars + "⬜" * (
                        10 - progress_bars
                    )

                    status_text += f"   📊 <b>Progress:</b> {cycles_completed}/{max_cycles} cycles {progress_display}\n"

                    # Time estimates
                    cycles_left = max_cycles - cycles_completed
                    if cycles_left <= 2:
                        status_text += "   ⏱️ <i>🎯 Final results coming soon!</i>\n"
                    elif cycles_left <= 5:
                        est_minutes = cycles_left * 3  # More conservative estimate
                        status_text += (
                            f"   ⏱️ <i>⏰ Est. completion: ~{est_minutes} min</i>\n"
                        )
                    else:
                        status_text += (
                            "   ⏱️ <i>🔍 Comprehensive search in progress...</i>\n"
                        )
                else:
                    status_text += "   📊 <i>Processing research databases...</i>\n"

            elif task.status == TaskStatus.QUEUED:
                # Show queue position if available
                status_text += "   ⏳ <i>Queued for processing...</i>\n"
                status_text += "   🚀 <i>Will start within minutes</i>\n"

            status_text += "\n"
    else:
        status_text += "🔄 <b>No active tasks</b>\n"
        status_text += "💡 <i>Create a new task to start researching!</i>\n\n"

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

    keyboard = create_status_keyboard(
        active_tasks, completed_tasks, paused_tasks, cancelled_tasks
    )

    await send_or_edit_message(
        message, status_text, keyboard, edit_mode, navigation_context=navigation_context
    )


async def show_task_selection(
    message: Message,
    user,
    page: int = 0,
    *,
    edit_mode: bool = False,
    navigation_context: bool = False,
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

        await send_or_edit_message(
            message, text, keyboard, edit_mode, navigation_context=navigation_context
        )
        return

    # Create task pagination handler
    task_pagination = TaskPaginationHandler(user_tasks)
    text, keyboard = task_pagination.get_page_data(page)

    await send_or_edit_message(
        message, text, keyboard, edit_mode, navigation_context=navigation_context
    )


async def show_task_results(
    message: Message,
    user,
    task_id: int,
    page: int = 0,
    *,
    edit_mode: bool = False,
    navigation_context: bool = False,
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

        # Filter by task_id if possible (this is a workaround until proper task-result mapping is implemented)
        task_analyses = all_analyses  # For now, show all recent analyses

        # If no results in old system, try new system (UserTask + Finding)
        if not task_analyses:
            try:
                # Import here to avoid circular imports
                from shared.db import get_user_task_results

                task_analyses = await get_user_task_results(task_id)
            except Exception as db_error:
                logger.warning(
                    f"Failed to get task results for task {task_id}: {db_error}"
                )
                task_analyses = []

    except Exception as e:
        logger.error(f"Error getting task results: {e}")
        task_analyses = []

    if not task_analyses:
        text = dedent(f"""
        📚 <b>No results for Task #{task_id}</b>

        🔍 <b>Possible reasons:</b>
        • Task is still being processed by the AI agent
        • No relevant papers found matching your criteria
        • Task may have encountered an error

        💡 <b>What you can do:</b>
        • Check task status with <b>📊 Status</b> button
        • Wait a few more minutes if task is still processing
        • Try creating a new task with different keywords

        🔄 Results will appear here automatically once processing completes.
        """)

        keyboard = create_empty_state_keyboard()

        await send_or_edit_message(
            message, text, keyboard, edit_mode, navigation_context=navigation_context
        )
        return

    # Create results pagination handler with improved formatting
    results_pagination = ResultsPaginationHandler(task_analyses)
    text, keyboard = results_pagination.get_page_data(page)

    # Add task-specific header to the results
    enhanced_text = f"📚 <b>Results for Task #{task_id}</b>\n\n{text}"

    await send_or_edit_message(
        message,
        enhanced_text,
        keyboard,
        edit_mode,
        navigation_context=navigation_context,
    )


async def show_individual_result(
    message: Message, analysis, paper, result_idx: int
) -> None:
    """Show individual result in detailed view with enhanced formatting.

    :param message: Telegram message
    :param analysis: Analysis object
    :param paper: Paper object
    :param result_idx: Result index for navigation
    """
    # Create enhanced result display
    result_text = f"🔬 <b>Research Finding #{result_idx + 1}</b>\n\n"

    # Paper title with relevance indicator
    relevance_indicator = (
        "🟢" if analysis.relevance >= 80 else "🟡" if analysis.relevance >= 60 else "🟠"
    )
    result_text += f"📄 <b>{escape_html(paper.title)}</b>\n"
    result_text += (
        f"{relevance_indicator} <b>Relevance:</b> {analysis.relevance:.1f}%\n\n"
    )

    # AI Summary with better formatting
    if analysis.summary and analysis.summary.strip():
        result_text += "🤖 <b>AI Analysis:</b>\n"
        result_text += f"<i>{escape_html(cut_text(analysis.summary, 400))}</i>\n\n"
    elif hasattr(paper, "abstract") and paper.abstract:
        result_text += "📝 <b>Abstract:</b>\n"
        result_text += f"<i>{escape_html(cut_text(paper.abstract, 350))}</i>\n\n"
    else:
        result_text += "📝 <b>Summary:</b> <i>No summary available</i>\n\n"

    # Enhanced metadata section
    metadata_lines = []

    # Authors with improved formatting
    if hasattr(paper, "authors") and paper.authors:
        if isinstance(paper.authors, list) and paper.authors:
            authors_list = [
                str(author).strip() for author in paper.authors if str(author).strip()
            ]
            if authors_list:
                if len(authors_list) <= 3:
                    authors_text = ", ".join(authors_list)
                else:
                    authors_text = (
                        ", ".join(authors_list[:3])
                        + f" <i>+{len(authors_list) - 3} more</i>"
                    )
                metadata_lines.append(f"👥 <b>Authors:</b> {escape_html(authors_text)}")

    # Publication date
    if hasattr(paper, "published_date") and paper.published_date:
        metadata_lines.append(
            f"📅 <b>Published:</b> {paper.published_date.strftime('%Y-%m-%d')}"
        )
    elif hasattr(paper, "published") and paper.published:
        try:
            pub_date = (
                paper.published.strftime("%Y-%m-%d")
                if hasattr(paper.published, "strftime")
                else str(paper.published)
            )
            metadata_lines.append(f"📅 <b>Published:</b> {pub_date}")
        except (AttributeError, ValueError, TypeError):
            # Skip if publication date cannot be formatted
            pass

    # Journal or source
    if hasattr(paper, "journal_ref") and paper.journal_ref:
        metadata_lines.append(
            f"📖 <b>Journal:</b> {escape_html(cut_text(paper.journal_ref, 50))}"
        )

    # Categories if available
    if hasattr(paper, "categories") and paper.categories:
        if isinstance(paper.categories, list) and paper.categories:
            categories_text = ", ".join(paper.categories[:3])
            metadata_lines.append(
                f"🏷️ <b>Categories:</b> {escape_html(categories_text)}"
            )

    # Add metadata to result text
    if metadata_lines:
        result_text += "\n".join(metadata_lines) + "\n\n"

    # Add original source link
    if hasattr(paper, "abs_url") and paper.abs_url:
        result_text += (
            f"🔗 <b>Original Source:</b> <a href='{paper.abs_url}'>View Paper</a>\n"
        )

    # Analysis metadata
    result_text += (
        f"🕐 <b>Found:</b> {analysis.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    )

    keyboard = create_result_detail_keyboard(result_idx)

    message_obj = safe_message_from_callback(message)
    if message_obj:
        await send_or_edit_message(
            message_obj, result_text, keyboard, navigation_context=True
        )


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
    <b>Created:</b> {task.created_at.strftime("%Y-%m-%d %H:%M")}
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
