"""
Message handling utilities and smart message management.

USER COMMUNICATION RULES:
==========================================

WHEN TO SEND NEW MESSAGES:
- First interaction (/start, /help)
- Creating new entities (new tasks)
- Error handling and exceptions
- Responses to commands without context

WHEN TO EDIT EXISTING MESSAGES:
- Navigation through menus and sections (navigation_context=True)
- Task status updates (function_context_key)
- Results pagination (navigation_context=True)
- Transitions between screens of the same context (navigation_context=True)

FUNCTION-SPECIFIC MESSAGE EDITING:
- Use function_context_key to edit messages created by specific functions
- Each function can have its own tracked message for updates
- Context keys are generated using generate_context_key()

Key Features:
- Smart message editing with content change detection
- Automatic fallback from edit to send operations
- Memory-efficient message tracking with size limits
- Content normalization for accurate comparison
- Keyboard comparison for InlineKeyboardMarkup objects

Example:
    # For navigation always use navigation_context=True
    await send_or_edit_message(
        message, "New content", keyboard, navigation_context=True
    )

    # For new actions - regular messages
    await send_or_edit_message(
        message, "Task created!", keyboard
    )

    # For function-specific editing
    context_key = f"status_{user_id}"
    await send_or_edit_message(
        message, "Status updated", keyboard, function_context_key=context_key
    )
"""

from typing import Dict, Optional, Any
from aiogram.types import Message, InlineKeyboardMarkup, MaybeInaccessibleMessage
from aiogram.enums import ParseMode

from shared.logging import get_logger

logger = get_logger(__name__)

# Global dictionary to track the last bot messages per user
_last_bot_messages: Dict[int, Message] = {}
# Dictionary to store the last message content
_last_message_content: Dict[int, Dict[str, Any]] = {}
# Dictionary to track function-specific messages for editing
_function_context_messages: Dict[str, Message] = {}

# Maximum number of tracked users
MAX_TRACKED_USERS = 500
# Maximum message content size (characters)
MAX_CONTENT_SIZE = 4000


def normalize_text(text: str) -> str:
    """Normalize text for comparison by removing extra whitespace."""
    if not text:
        return ""
    return " ".join(text.split())


def compare_inline_keyboards(
    kb1: Optional[InlineKeyboardMarkup], kb2: Optional[InlineKeyboardMarkup]
) -> bool:
    """Compare two InlineKeyboardMarkup objects for equality."""
    if kb1 is None and kb2 is None:
        return True
    if kb1 is None or kb2 is None:
        return False

    # Convert to dict for comparison
    try:
        kb1_dict = kb1.model_dump() if hasattr(kb1, "model_dump") else kb1.__dict__
        kb2_dict = kb2.model_dump() if hasattr(kb2, "model_dump") else kb2.__dict__
        return kb1_dict == kb2_dict
    except Exception:
        # If comparison fails, assume they are different
        return False


def has_message_content_changed(
    message: Message, new_text: str, new_keyboard: Optional[InlineKeyboardMarkup]
) -> bool:
    """Check if message content has actually changed."""
    if not message or not hasattr(message, "message_id"):
        return True

    user_id = message.from_user.id if message.from_user else None

    if not user_id:
        return True

    # Get current message content
    current_content = _last_message_content.get(user_id, {})

    # Normalize texts for comparison
    normalized_new_text = normalize_text(new_text)
    current_text = normalize_text(current_content.get("text", ""))

    # Compare text
    text_changed = normalized_new_text != current_text

    # Compare keyboards
    current_keyboard = current_content.get("keyboard")
    keyboard_changed = not compare_inline_keyboards(current_keyboard, new_keyboard)

    # Update stored content
    _last_message_content[user_id] = {
        "text": normalized_new_text,
        "keyboard": new_keyboard,
    }

    return text_changed or keyboard_changed


async def track_bot_message(
    user_id: int,
    message: Message,
    text: Optional[str] = None,
    keyboard: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """Track the last message sent by bot to user for potential editing.

    :param user_id: Telegram user ID
    :param message: Message sent by bot
    :param text: Message text (optional, for content tracking)
    :param keyboard: Message keyboard (optional, for content tracking)
    """
    # Limit dictionary size to prevent memory leaks
    if len(_last_bot_messages) > MAX_TRACKED_USERS:
        # Remove old entries (remove 20% of the oldest)
        items_to_remove = list(_last_bot_messages.keys())[:MAX_TRACKED_USERS // 5]
        for key in items_to_remove:
            _last_bot_messages.pop(key, None)
            _last_message_content.pop(key, None)

    _last_bot_messages[user_id] = message

    # Save message content if provided
    if text is not None:
        # Limit text size for memory efficiency
        normalized_text = normalize_text(text)
        if len(normalized_text) > MAX_CONTENT_SIZE:
            normalized_text = normalized_text[:MAX_CONTENT_SIZE] + "..."

        inline_keyboard = (
            keyboard if isinstance(keyboard, InlineKeyboardMarkup) else None
        )
        _last_message_content[user_id] = {
            "text": normalized_text,
            "keyboard": inline_keyboard,
        }


async def get_last_bot_message(user_id: int) -> Optional[Message]:
    """Get the last message sent by bot to user.

    :param user_id: Telegram user ID
    :return: Last bot message or None
    """
    return _last_bot_messages.get(user_id)


async def clear_user_message_history(user_id: int) -> None:
    """Clear message history for a specific user.

    :param user_id: Telegram user ID
    """
    _last_bot_messages.pop(user_id, None)
    _last_message_content.pop(user_id, None)


async def set_function_context_message(context_key: str, message: Message) -> None:
    """Set a message for a specific function context for later editing.

    :param context_key: Unique key identifying the function context (e.g., 'status_user_123')
    :param message: Message to be tracked for this context
    """
    # Limit the size of context messages dictionary
    if len(_function_context_messages) > MAX_TRACKED_USERS:
        # Remove oldest entries (first 20%)
        items_to_remove = list(_function_context_messages.keys())[:MAX_TRACKED_USERS // 5]
        for key in items_to_remove:
            _function_context_messages.pop(key, None)

    _function_context_messages[context_key] = message


async def get_function_context_message(context_key: str) -> Optional[Message]:
    """Get a message for a specific function context.

    :param context_key: Unique key identifying the function context
    :return: Message if found, None otherwise
    """
    return _function_context_messages.get(context_key)


async def clear_function_context_message(context_key: str) -> None:
    """Clear a function context message.

    :param context_key: Unique key identifying the function context
    """
    _function_context_messages.pop(context_key, None)


def generate_context_key(function_name: str, user_id: int, *args: Any) -> str:
    """Generate a unique context key for a function.

    :param function_name: Name of the function (e.g., 'status', 'help', 'tasks')
    :param user_id: User ID
    :param args: Additional arguments to make key unique
    :return: Unique context key
    """
    key_parts = [function_name, str(user_id)]
    key_parts.extend(str(arg) for arg in args)
    return "_".join(key_parts)


def get_message_content_stats() -> Dict[str, int]:
    """Get statistics about stored message content.

    :returns: Dictionary with statistics
    """
    total_content_size = sum(
        len(content.get("text", "")) for content in _last_message_content.values()
    )

    return {
        "tracked_messages": len(_last_bot_messages),
        "stored_content": len(_last_message_content),
        "function_context_messages": len(_function_context_messages),
        "max_users_limit": MAX_TRACKED_USERS,
        "max_content_size": MAX_CONTENT_SIZE,
        "total_content_chars": total_content_size,
        "memory_usage_estimate_kb": (
            len(_last_bot_messages) * 2 + len(_function_context_messages) * 2 + total_content_size // 500
        ),  # More accurate estimate
    }


async def send_or_edit_message(
    message: Message | MaybeInaccessibleMessage,
    text: str,
    keyboard=None,
    edit_mode: bool = False,
    navigation_context: bool = False,
    function_context_key: Optional[str] = None,
) -> Message:
    """Send new message or edit existing one with smart fallback.

    Usage rules:
    - NEW messages: on first interaction, entity creation, errors
    - EDITING: on navigation, status updates, pagination
    - FUNCTION CONTEXT: specify function_context_key to edit function-specific message

    :param message: Telegram message object
    :param text: Message text
    :param keyboard: Inline keyboard markup (optional)
    :param edit_mode: If True, try to edit existing message first
    :param navigation_context: If True, always prefer editing for navigation flows
    :param function_context_key: Key to identify function-specific message for editing
    :return: Sent or edited message
    """
    if not isinstance(message, Message):
        message = safe_message_from_callback(message)
        if message is None:
            raise ValueError("Message is not accessible")
    
    user_id = message.from_user.id if message.from_user else None

    # Check if we have a function-specific message to edit
    if function_context_key:
        context_message = await get_function_context_message(function_context_key)
        if context_message:
            # Edit the function-specific message
            inline_keyboard = (
                keyboard if isinstance(keyboard, InlineKeyboardMarkup) else None
            )

            if not has_message_content_changed(context_message, text, inline_keyboard):
                # Content hasn't changed, return existing message
                logger.debug(f"Function context message content unchanged, skipping edit for {function_context_key}")
                return context_message

            try:
                await context_message.edit_text(
                    text, parse_mode=ParseMode.HTML, reply_markup=inline_keyboard
                )
                # Update stored content after successful editing
                if user_id:
                    _last_message_content[user_id] = {
                        "text": normalize_text(text),
                        "keyboard": inline_keyboard,
                    }
                return context_message
            except Exception as e:
                logger.warning(f"Failed to edit function context message {function_context_key}: {e}")
                # Continue with normal flow

    if edit_mode or navigation_context:
        # For navigation always prefer editing
        inline_keyboard = (
            keyboard if isinstance(keyboard, InlineKeyboardMarkup) else None
        )

        if not has_message_content_changed(message, text, inline_keyboard):
            # Content hasn't changed, return existing message
            logger.debug("Message content unchanged, skipping edit")
            return message

        try:
            await message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=inline_keyboard
            )
            # Update stored content after successful editing
            if user_id:
                _last_message_content[user_id] = {
                    "text": normalize_text(text),
                    "keyboard": inline_keyboard,
                }
            return message
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            # For navigation fallback to sending new message
            sent_message = await message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,  # type: ignore
            )
            if user_id:
                await track_bot_message(user_id, sent_message, text, inline_keyboard)
            return sent_message
    else:
        # Send new message
        sent_message = await message.answer(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,  # type: ignore
        )

        if user_id:
            inline_keyboard = (
                keyboard if isinstance(keyboard, InlineKeyboardMarkup) else None
            )
            await track_bot_message(user_id, sent_message, text, inline_keyboard)

            # Save message for function context if specified
            if function_context_key:
                await set_function_context_message(function_context_key, sent_message)

        return sent_message


def safe_message_from_callback(callback_message) -> Optional[Message]:
    """Safely extract Message from callback if accessible.

    :param callback_message: Potentially inaccessible message from callback
    :return: Message if accessible, None otherwise
    """
    if callback_message and hasattr(callback_message, "edit_text"):
        return callback_message  # type: ignore
    return None
