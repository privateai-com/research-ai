from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from shared.db import update_user_settings
from shared.logging import get_logger


router = Router(name="notifications")
logger = get_logger(__name__)


@router.message(Command("notifications_on"))
async def command_notifications_on(message: Message) -> None:
    """Enable notifications with default settings."""
    if not message.from_user:
        await message.answer("❌ Error: could not determine user.")
        return

    user_id = message.from_user.id

    try:
        # Set reasonable defaults
        await update_user_settings(user_id, instant_notification_threshold=75.0)
        await message.answer(
            "✅ Notifications enabled for important findings (75%+ relevance)"
        )
        logger.info(f"User {user_id} enabled notifications")
    except Exception as e:
        logger.error(f"Error enabling notifications: {e}")
        await message.answer("❌ Error enabling notifications")


@router.message(Command("notifications_off"))
async def command_notifications_off(message: Message) -> None:
    """Disable all notifications."""
    if not message.from_user:
        await message.answer("❌ Error: could not determine user.")
        return

    user_id = message.from_user.id

    try:
        # Set threshold to 100 to effectively disable
        await update_user_settings(user_id, instant_notification_threshold=100.0)
        await message.answer("✅ Notifications disabled")
        logger.info(f"User {user_id} disabled notifications")
    except Exception as e:
        logger.error(f"Error disabling notifications: {e}")
        await message.answer("❌ Error disabling notifications")


@router.message(Command("group_on"))
async def command_group_on(message: Message) -> None:
    """Enable group notifications in current chat."""
    if not message.from_user:
        await message.answer("❌ Error: could not determine user.")
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    if message.chat.type not in ["group", "supergroup"]:
        await message.answer("❌ This command only works in group chats")
        return

    try:
        await update_user_settings(user_id, group_chat_id=chat_id)
        await message.answer("✅ Group notifications enabled")
        logger.info(f"User {user_id} enabled group notifications in {chat_id}")
    except Exception as e:
        logger.error(f"Error setting group: {e}")
        await message.answer("❌ Error enabling group notifications")


@router.message(Command("group_off"))
async def command_group_off(message: Message) -> None:
    """Disable group notifications, return to personal chat."""
    if not message.from_user:
        await message.answer("❌ Error: could not determine user.")
        return

    user_id = message.from_user.id

    try:
        await update_user_settings(user_id, group_chat_id=None)
        await message.answer("✅ Back to personal notifications")
        logger.info(f"User {user_id} disabled group notifications")
    except Exception as e:
        logger.error(f"Error unsetting group: {e}")
        await message.answer("❌ Error disabling group notifications")
