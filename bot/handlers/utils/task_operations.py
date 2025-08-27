"""
Task creation and management operations.

This module handles all task-related operations including creation,
validation, and business logic for task management.
"""

from textwrap import dedent
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from shared.db import (
    get_or_create_user,
    create_user_task_with_queue,
    update_queue_positions,
    get_or_create_task_statistics,
)
from bot.handlers.utils.messages import send_or_edit_message
from bot.handlers.utils.ui import get_main_menu_keyboard
from bot.handlers.utils.validation import (
    validate_user_access,
    validate_rate_limit,
    validate_task_creation,
    validate_task_description,
)
from bot.handlers.utils.utils import escape_html, cut_text
from shared.logging import get_logger

logger = get_logger(__name__)


class TaskCreationStates:
    """States for task creation flow."""

    waiting_for_description = "waiting_for_description"


async def rate_limit_check(message: Message, action: str) -> bool:
    """Check rate limiting for user actions.

    :param message: Telegram message
    :param action: Action being performed
    :returns: True if allowed, False if rate limited
    """
    is_allowed, error_msg = await validate_rate_limit(message, action)
    if not is_allowed:
        await send_or_edit_message(message, error_msg, auto_edit_recent=True)
        return False
    return True


async def create_task_for_user(user, description: str, message: Message) -> None:
    """Create a new task for the user.

    :param user: User object
    :param description: Task description
    :param message: Telegram message for response
    """
    try:
        await update_queue_positions()

        task_result = await create_user_task_with_queue(
            user=user, description=description
        )

        if task_result:
            task, queue_entry = task_result
            await get_or_create_task_statistics()

            success_text = dedent(f"""
            ✅ <b>Task Created Successfully!</b>

            📋 <b>Task #{task.id}:</b> {escape_html(cut_text(description, 60))}
            🎯 <b>Status:</b> Task queued for processing
            🔄 <b>Next:</b> Agent will search research databases

            ⏱️ <b>Estimated time:</b> Results usually start appearing within 5-10 minutes
            """)

            await send_or_edit_message(
                message, success_text, get_main_menu_keyboard(), auto_edit_recent=True
            )

            logger.info(f"Task {task.id} created successfully for user {user.id}")
        else:
            error_text = "❌ Failed to create task. Please try again later."
            await send_or_edit_message(
                message, error_text, get_main_menu_keyboard(), auto_edit_recent=True
            )

    except Exception as e:
        logger.error(f"Error creating task: {e}")
        error_text = "❌ An error occurred while creating the task."
        await send_or_edit_message(
            message, error_text, get_main_menu_keyboard(), auto_edit_recent=True
        )


async def start_simple_task_creation(message: Message, state: FSMContext) -> None:
    """Start simple task creation - direct input.

    :param message: Telegram message
    :param state: FSM context
    """
    # Validate user access
    is_valid, error_msg = await validate_user_access(message)
    if not is_valid:
        await send_or_edit_message(message, error_msg, auto_edit_recent=True)
        return

    # Check rate limiting
    if not await rate_limit_check(message, "task_create"):
        return

    # Validate task creation permissions
    can_create, error_msg = await validate_task_creation(message)
    if not can_create:
        await send_or_edit_message(message, error_msg, auto_edit_recent=True)
        return

    user = await get_or_create_user(message.from_user.id)

    # Show simple prompt for task description
    prompt_text = dedent("""
    🔬 <b>New Research Task</b>

    What would you like me to research?

            <b>Examples:</b>
    • cancer treatment
    • renewable energy
    • machine learning

    Just type your topic below:
    """)

    await send_or_edit_message(message, prompt_text, auto_edit_recent=True)
    await state.set_state(TaskCreationStates.waiting_for_description)


async def process_task_description(message: Message, state: FSMContext) -> None:
    """Process task description input.

    :param message: Telegram message with description
    :param state: FSM context
    """
    if not message.text or not message.from_user:
        error_text = "❌ Please provide a valid research topic."
        await send_or_edit_message(message, error_text, auto_edit_recent=True)
        return

    description = message.text.strip()

    # Validate task description
    is_valid, error_msg = validate_task_description(description)
    if not is_valid:
        await send_or_edit_message(message, error_msg, auto_edit_recent=True)
        return

    # Create task
    user = await get_or_create_user(message.from_user.id)
    await create_task_for_user(user, description, message)
    await state.clear()


async def cancel_task_creation(message: Message, state: FSMContext) -> None:
    """Cancel task creation and clear state.

    :param message: Telegram message
    :param state: FSM context
    """
    await state.clear()
    await send_or_edit_message(
        message,
        "❌ Task creation cancelled.",
        get_main_menu_keyboard(),
        auto_edit_recent=True,
    )
