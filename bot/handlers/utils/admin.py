"""
Administrative utilities and permission checking.

This module provides centralized admin authentication and authorization
functionality for the bot. All admin handlers should use these utilities
instead of implementing their own permission checks.
"""

import os
from typing import Set
from functools import wraps

from shared.logging import get_logger

logger = get_logger(__name__)


# Load admin user IDs from environment variable or use default
def _load_admin_user_ids() -> Set[int]:
    """Load admin user IDs from environment or configuration.

    :returns: Set of admin user IDs
    """
    admin_ids_str = os.getenv("TELEGRAM_ADMIN_USER_IDS")
    try:
        # Support comma-separated list of IDs
        admin_ids = {
            int(id_str.strip()) for id_str in admin_ids_str.split(",") if id_str.strip()
        }
        logger.info(f"Loaded {len(admin_ids)} admin user IDs from configuration")
        return admin_ids
    except ValueError as e:
        logger.error(f"Error parsing admin user IDs: {e}, using default")
        return {}


ADMIN_USER_IDS: Set[int] = _load_admin_user_ids()


async def is_admin(user_id: int) -> bool:
    """Check if user has admin privileges.

    :param user_id: Telegram user ID to check
    :returns: True if user is admin, False otherwise
    """
    return user_id in ADMIN_USER_IDS


def admin_required(func):
    """Decorator to require admin privileges for a handler function.

    :param func: Handler function to decorate
    :returns: Decorated function with admin check
    """

    @wraps(func)
    async def wrapper(message, *args, **kwargs):
        if not message.from_user:
            await message.answer("❌ Error: could not determine user.")
            return

        if not await is_admin(message.from_user.id):
            await message.answer("❌ Access denied. Admin privileges required.")
            logger.warning(
                f"Non-admin user {message.from_user.id} attempted to access admin function: {func.__name__}"
            )
            return

        return await func(message, *args, **kwargs)

    return wrapper


def add_admin_user(user_id: int) -> bool:
    """Add a user to admin list (runtime only).

    :param user_id: User ID to add as admin
    :returns: True if added successfully
    """
    try:
        ADMIN_USER_IDS.add(user_id)
        logger.info(f"Added user {user_id} to admin list")
        return True
    except Exception as e:
        logger.error(f"Error adding admin user {user_id}: {e}")
        return False


def remove_admin_user(user_id: int) -> bool:
    """Remove a user from admin list (runtime only).

    :param user_id: User ID to remove from admin list
    :returns: True if removed successfully
    """
    try:
        ADMIN_USER_IDS.discard(user_id)
        logger.info(f"Removed user {user_id} from admin list")
        return True
    except Exception as e:
        logger.error(f"Error removing admin user {user_id}: {e}")
        return False


def get_admin_users() -> Set[int]:
    """Get current list of admin users.

    :returns: Set of admin user IDs
    """
    return ADMIN_USER_IDS.copy()


def get_admin_count() -> int:
    """Get number of admin users.

    :returns: Number of admin users
    """
    return len(ADMIN_USER_IDS)
