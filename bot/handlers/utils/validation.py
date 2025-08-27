"""
Data validation and business rule checks.

This module contains all validation logic, rate limiting, and business rule
enforcement that is shared across different handlers.
"""

from aiogram.types import Message
from shared.db import get_or_create_user, check_rate_limit, check_user_can_create_task
from shared.logging import get_logger

logger = get_logger(__name__)


async def validate_user_access(message: Message) -> tuple[bool, str]:
    """Validate user access and permissions.

    :param message: Telegram message
    :returns: Tuple of (is_valid, error_message)
    """
    if not message.from_user:
        return False, "❌ Error: could not determine user."

    try:
        await get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        return True, ""
    except Exception as e:
        logger.error(f"Error validating user access: {e}")
        return False, "❌ Error validating user access."


async def validate_rate_limit(message: Message, action: str) -> tuple[bool, str]:
    """Check rate limiting for user actions.

    :param message: Telegram message
    :param action: Action being performed
    :returns: Tuple of (is_allowed, error_message)
    """
    if not message.from_user:
        return False, "❌ Error: could not determine user."

    try:
        result = await check_rate_limit(message.from_user.id, action)
        is_allowed = result[0] if isinstance(result, tuple) else result

        if not is_allowed:
            return False, "❌ Rate limit exceeded. Please wait before trying again."

        return True, ""
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return False, "❌ Error checking rate limit."


async def validate_task_creation(message: Message) -> tuple[bool, str]:
    """Validate if user can create a new task.

    :param message: Telegram message
    :returns: Tuple of (can_create, error_message)
    """
    if not message.from_user:
        return False, "❌ Error: could not determine user."

    try:
        user = await get_or_create_user(message.from_user.id)
        can_create, reason = await check_user_can_create_task(user)

        if not can_create:
            from bot.handlers.utils.ui import get_plan_display_name

            plan_name = get_plan_display_name(user.plan)
            error_msg = f"🚫 Cannot create task ({plan_name} plan)\n\n{reason}"
            return False, error_msg

        return True, ""
    except Exception as e:
        logger.error(f"Error validating task creation: {e}")
        return False, "❌ Error validating task creation."


def validate_task_description(description: str) -> tuple[bool, str]:
    """Validate task description.

    :param description: Task description to validate
    :returns: Tuple of (is_valid, error_message)
    """
    if not description:
        return False, "❌ Please provide a valid research topic."

    description = description.strip()

    if len(description) < 3:
        return (
            False,
            "❌ Topic too short. Please be more specific (minimum 3 characters).",
        )

    if len(description) > 500:
        return (
            False,
            "❌ Topic too long. Please be more concise (maximum 500 characters).",
        )

    return True, ""


def validate_pagination_params(
    page: int, total_pages: int | None = None
) -> tuple[bool, str]:
    """Validate pagination parameters.

    :param page: Page number to validate
    :param total_pages: Total number of pages (optional)
    :returns: Tuple of (is_valid, error_message)
    """
    if page < 0:
        return False, "❌ Error: invalid page number."

    if total_pages is not None and page >= total_pages:
        return False, "❌ Error: page number out of range."

    return True, ""


def validate_task_id(task_id: int) -> tuple[bool, str]:
    """Validate task ID.

    :param task_id: Task ID to validate
    :returns: Tuple of (is_valid, error_message)
    """
    if task_id <= 0:
        return False, "❌ Error: invalid task ID."

    return True, ""


def validate_result_index(result_idx: int, total_results: int) -> tuple[bool, str]:
    """Validate result index.

    :param result_idx: Result index to validate
    :param total_results: Total number of results
    :returns: Tuple of (is_valid, error_message)
    """
    if result_idx < 0:
        return False, "❌ Error: invalid result index."

    if result_idx >= total_results:
        return False, "❌ Error: result not found."

    return True, ""


async def validate_task_ownership(user_id: int, task_id: int) -> tuple[bool, str]:
    """Validate that task belongs to user.

    :param user_id: Telegram user ID
    :param task_id: Task ID to check
    :returns: Tuple of (is_owner, error_message)
    """
    try:
        from shared.db import get_user_tasks

        user_tasks = await get_user_tasks(user_id)

        if not any(t.id == task_id for t in user_tasks):
            return False, "❌ Task not found or access denied."

        return True, ""
    except Exception as e:
        logger.error(f"Error validating task ownership: {e}")
        return False, "❌ Error validating task access."


def validate_callback_data(
    callback_data: str, expected_parts: int
) -> tuple[bool, list[str]]:
    """Validate callback data format.

    :param callback_data: Callback data string
    :param expected_parts: Expected number of parts when split by '_'
    :returns: Tuple of (is_valid, parts_list)
    """
    if not callback_data:
        return False, []

    parts = callback_data.split("_")

    if len(parts) < expected_parts:
        return False, parts

    return True, parts


def validate_numeric_param(param_str: str, param_name: str) -> tuple[bool, int, str]:
    """Validate and convert string parameter to integer.

    :param param_str: String parameter to validate
    :param param_name: Parameter name for error messages
    :returns: Tuple of (is_valid, value, error_message)
    """
    if not param_str or not param_str.isdigit():
        return False, 0, f"❌ Error: invalid {param_name} format."

    try:
        value = int(param_str)
        if value < 0:
            return False, 0, f"❌ Error: {param_name} must be non-negative."
        return True, value, ""
    except ValueError:
        return False, 0, f"❌ Error: invalid {param_name} value."
