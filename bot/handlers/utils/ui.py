"""
UI components and keyboard layouts for the bot.

This module contains reusable UI elements, keyboards, and display utilities
that are shared across different handlers.
"""

from typing import Optional

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from shared.db import UserPlan, TaskStatus


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Create main menu keyboard with essential buttons only.

    :returns: Main menu keyboard for easy navigation
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔬 New Task")],
            [
                KeyboardButton(text="📊 Status"),
                KeyboardButton(text="📚 Results"),
            ],
            [KeyboardButton(text="❓ Help")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Choose what you need 👇",
    )
    return keyboard


def get_plan_display_name(plan: UserPlan) -> str:
    """Get display name for user plan.

    :param plan: User plan enum
    :returns: Display name for the plan
    """
    if plan == UserPlan.FREE:
        return "Free"
    elif plan == UserPlan.PREMIUM:
        return "Premium"
    else:
        return "Unknown"


def get_status_emoji(status: TaskStatus) -> str:
    """Get emoji for task status.

    :param status: Task status
    :returns: Emoji representing the status
    """
    if status == TaskStatus.QUEUED:
        return "⏳"
    elif status == TaskStatus.PROCESSING:
        return "🔄"
    elif status == TaskStatus.COMPLETED:
        return "✅"
    elif status == TaskStatus.FAILED:
        return "❌"
    elif status == TaskStatus.CANCELLED:
        return "🚫"
    elif status == TaskStatus.PAUSED:
        return "⏸️"
    else:
        return "❓"


def create_task_details_keyboard(
    task_id: int, has_results: bool = False, task_status: Optional[TaskStatus] = None
) -> InlineKeyboardMarkup:
    """Create keyboard for task details view.

    :param task_id: Task ID
    :param has_results: Whether task has results to show
    :param task_status: Current task status for action buttons
    :returns: Inline keyboard markup
    """
    buttons = []

    # Add action buttons based on task status
    if task_status:
        action_buttons = []

        if task_status in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
            # Can cancel or pause active tasks
            action_buttons.append(
                InlineKeyboardButton(
                    text="🚫 Cancel", callback_data=f"cancel_task_{task_id}"
                )
            )
            if task_status == TaskStatus.PROCESSING:
                action_buttons.append(
                    InlineKeyboardButton(
                        text="⏸️ Pause", callback_data=f"pause_task_{task_id}"
                    )
                )
        elif task_status == TaskStatus.PAUSED:
            # Can resume paused tasks
            action_buttons.append(
                InlineKeyboardButton(
                    text="▶️ Resume", callback_data=f"resume_task_{task_id}"
                )
            )
            action_buttons.append(
                InlineKeyboardButton(
                    text="🚫 Cancel", callback_data=f"cancel_task_{task_id}"
                )
            )

        if action_buttons:
            buttons.append(action_buttons)

    if has_results:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📚 View Results", callback_data=f"view_task_results_{task_id}"
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="🔙 Back to Status", callback_data="back_to_status"
                )
            ],
            [InlineKeyboardButton(text="🔬 New Task", callback_data="new_task_wizard")],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_task_list_keyboard(
    tasks, current_page: int = 0, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Create keyboard for task list with pagination.

    :param tasks: List of tasks to display
    :param current_page: Current page number
    :param total_pages: Total number of pages
    :returns: Inline keyboard markup
    """
    buttons = []

    # Add task buttons (max 3 per page)
    start_idx = current_page * 3
    end_idx = min(start_idx + 3, len(tasks))

    for i, task in enumerate(tasks[start_idx:end_idx], start_idx):
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📋 #{task.id}: {task.description[:30]}...",
                    callback_data=f"task_details_{task.id}",
                )
            ]
        )

    # Add pagination buttons
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"task_pagination_page_{current_page - 1}",
            )
        )
    if current_page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Next", callback_data=f"task_pagination_page_{current_page + 1}"
            )
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    # Add utility buttons
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔄 Refresh", callback_data="task_pagination_refresh"
            )
        ]
    )
    buttons.append(
        [InlineKeyboardButton(text="📊 Status", callback_data="back_to_status")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_results_keyboard(
    task_id: int, current_page: int = 0, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Create keyboard for results view with pagination.

    :param task_id: Task ID
    :param current_page: Current page number
    :param total_pages: Total number of pages
    :returns: Inline keyboard markup
    """
    buttons = []

    # Add pagination buttons
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"results_pagination_page_{current_page - 1}",
            )
        )
    if current_page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="➡️ Next",
                callback_data=f"results_pagination_page_{current_page + 1}",
            )
        )

    if nav_buttons:
        buttons.append(nav_buttons)

    # Add navigation buttons
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="🔙 Back to Tasks", callback_data="back_to_tasks"
                ),
                InlineKeyboardButton(text="📊 Status", callback_data="back_to_status"),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Refresh", callback_data="results_pagination_refresh"
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_result_detail_keyboard(result_idx: int) -> InlineKeyboardMarkup:
    """Create keyboard for individual result view.

    :param result_idx: Result index
    :returns: Inline keyboard markup
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💾 Save Result", callback_data=f"save_result_{result_idx}"
                ),
                InlineKeyboardButton(
                    text="🔍 More Sources", callback_data=f"more_sources_{result_idx}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Back to Results", callback_data="back_to_results"
                )
            ],
        ]
    )


def create_source_keyboard(
    result_idx: int,
    arxiv_id: Optional[str] = None,
    doi: Optional[str] = None,
    pmid: Optional[str] = None,
    title: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """Create keyboard for additional sources.

    :param result_idx: Result index
    :param arxiv_id: ArXiv ID if available
    :param doi: DOI if available
    :param pmid: PubMed ID if available
    :param title: Paper title for Google Scholar search
    :returns: Inline keyboard markup
    """
    buttons = []

    # Add source buttons
    if arxiv_id:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📚 arXiv",
                    url=f"https://arxiv.org/abs/{arxiv_id}",
                    callback_data=f"track_click_arxiv_{result_idx}",
                )
            ]
        )

    if doi:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔬 DOI",
                    url=f"https://doi.org/{doi}",
                    callback_data=f"track_click_doi_{result_idx}",
                )
            ]
        )

    if pmid:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🧬 PubMed",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    callback_data=f"track_click_pubmed_{result_idx}",
                )
            ]
        )

    if title:
        import urllib.parse

        search_query = urllib.parse.quote(title)
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔍 Google Scholar",
                    url=f"https://scholar.google.com/scholar?q={search_query}",
                    callback_data=f"track_click_scholar_{result_idx}",
                )
            ]
        )

    # Add back button
    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 Back to Result", callback_data=f"show_result_{result_idx}"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_status_keyboard(
    active_tasks, completed_tasks, paused_tasks=None, cancelled_tasks=None
) -> InlineKeyboardMarkup:
    """Create keyboard for status view.

    :param active_tasks: List of active tasks
    :param completed_tasks: List of completed tasks
    :param paused_tasks: List of paused tasks
    :param cancelled_tasks: List of cancelled tasks
    :returns: Inline keyboard markup
    """
    if paused_tasks is None:
        paused_tasks = []
    if cancelled_tasks is None:
        cancelled_tasks = []

    buttons = []

    # Add active task buttons (max 2)
    for task in active_tasks[:2]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📋 Active #{task.id}",
                    callback_data=f"task_details_{task.id}",
                )
            ]
        )

    # Add paused task buttons (max 2)
    for task in paused_tasks[:2]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"⏸️ Paused #{task.id}",
                    callback_data=f"task_details_{task.id}",
                )
            ]
        )

    # Add refresh button for active tasks
    if active_tasks:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔄 Refresh Status", callback_data="refresh_status"
                )
            ]
        )

    # Add cancelled task buttons (max 1)
    for task in cancelled_tasks[:1]:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🚫 Cancelled #{task.id}",
                    callback_data=f"task_details_{task.id}",
                )
            ]
        )

    # Add results button if there are completed tasks
    if completed_tasks:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📚 View Results", callback_data="show_results_list"
                )
            ]
        )

    # Add new task button
    buttons.append(
        [InlineKeyboardButton(text="🔬 New Task", callback_data="new_task_wizard")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_empty_state_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for empty state (no tasks).

    :returns: Inline keyboard markup
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔬 New Task", callback_data="new_task_wizard")]
        ]
    )
