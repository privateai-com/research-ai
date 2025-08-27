"""
Message handling utilities and smart message management.

This module provides utilities for sending, editing, and tracking bot messages
with automatic fallback and memory management. It includes intelligent content
change detection to avoid unnecessary API calls and prevent Telegram's
"message is not modified" errors.

Key Features:
- Smart message editing with content change detection
- Automatic fallback from edit to send operations
- Memory-efficient message tracking with size limits
- Content normalization for accurate comparison
- Keyboard comparison for InlineKeyboardMarkup objects

Example:
    # Smart editing with change detection
    await send_or_edit_message(
        message, "New content", keyboard, edit_mode=True
    )

    # Auto-edit recent message if content changed
    await send_or_edit_message(
        message, "Updated content", keyboard, auto_edit_recent=True
    )
"""

from typing import Dict, Optional, Any
from aiogram.types import Message, InlineKeyboardMarkup, MaybeInaccessibleMessage
from aiogram.enums import ParseMode

from shared.logging import get_logger

logger = get_logger(__name__)

# Глобальный словарь для отслеживания последних сообщений бота по пользователю
_last_bot_messages: Dict[int, Message] = {}
# Словарь для хранения последнего содержимого сообщений
_last_message_content: Dict[int, Dict[str, Any]] = {}


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
    # Ограничиваем размер словарей, чтобы избежать утечек памяти
    if len(_last_bot_messages) > 1000:
        # Удаляем старые записи (первые 200)
        items_to_remove = list(_last_bot_messages.keys())[:200]
        for key in items_to_remove:
            _last_bot_messages.pop(key, None)
            _last_message_content.pop(key, None)

    if len(_last_message_content) > 1000:
        # Очищаем словарь содержимого сообщений
        items_to_remove = list(_last_message_content.keys())[:200]
        for key in items_to_remove:
            _last_message_content.pop(key, None)

    _last_bot_messages[user_id] = message

    # Сохраняем содержимое сообщения, если передано
    if text is not None:
        inline_keyboard = (
            keyboard if isinstance(keyboard, InlineKeyboardMarkup) else None
        )
        _last_message_content[user_id] = {
            "text": normalize_text(text),
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


def get_message_content_stats() -> Dict[str, int]:
    """Get statistics about stored message content.

    :returns: Dictionary with statistics
    """
    return {
        "tracked_messages": len(_last_bot_messages),
        "stored_content": len(_last_message_content),
        "memory_usage_estimate_kb": (
            len(_last_bot_messages) + len(_last_message_content)
        )
        * 2,  # Rough estimate
    }


async def send_or_edit_message(
    message: Message | MaybeInaccessibleMessage,
    text: str,
    keyboard=None,
    edit_mode: bool = False,
    auto_edit_recent: bool = True,
) -> Message:
    """Send new message or edit existing one with smart fallback.

    :param message: Telegram message object
    :param text: Message text
    :param keyboard: Inline keyboard markup (optional)
    :param edit_mode: If True, try to edit existing message first
    :param auto_edit_recent: If True and edit_mode is False, try to edit recent bot message
    :return: Sent or edited message
    """
    if not isinstance(message, Message):
        message = safe_message_from_callback(message)
        if message is None:
            raise ValueError("Message is not accessible")
    
    user_id = message.from_user.id if message.from_user else None

    if edit_mode:
        # Проверяем, изменилось ли содержимое
        inline_keyboard = (
            keyboard if isinstance(keyboard, InlineKeyboardMarkup) else None
        )

        if not has_message_content_changed(message, text, inline_keyboard):
            # Содержимое не изменилось, возвращаем существующее сообщение
            logger.debug("Message content unchanged, skipping edit")
            return message

        try:
            await message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=inline_keyboard
            )
            # Обновляем сохраненное содержимое после успешного редактирования
            if user_id:
                _last_message_content[user_id] = {
                    "text": normalize_text(text),
                    "keyboard": inline_keyboard,
                }
            return message
        except Exception as e:
            logger.warning(f"Failed to edit message: {e}")
            sent_message = await message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,  # type: ignore
            )
            if user_id:
                await track_bot_message(user_id, sent_message, text, inline_keyboard)
            return sent_message
    else:
        # Try to edit recent bot message if auto_edit_recent is enabled
        if auto_edit_recent and user_id:
            last_bot_message = await get_last_bot_message(user_id)
            if last_bot_message:
                # Проверяем, изменилось ли содержимое перед редактированием
                inline_keyboard = (
                    keyboard if isinstance(keyboard, InlineKeyboardMarkup) else None
                )

                if not has_message_content_changed(
                    last_bot_message, text, inline_keyboard
                ):
                    # Содержимое не изменилось, возвращаем существующее сообщение
                    logger.debug("Recent message content unchanged, skipping auto-edit")
                    return last_bot_message

                try:
                    await last_bot_message.edit_text(
                        text, parse_mode=ParseMode.HTML, reply_markup=inline_keyboard
                    )
                    # Обновляем сохраненное содержимое после успешного редактирования
                    if user_id:
                        _last_message_content[user_id] = {
                            "text": normalize_text(text),
                            "keyboard": inline_keyboard,
                        }
                    return last_bot_message
                except Exception as e:
                    logger.debug(f"Failed to auto-edit recent message: {e}")
                    # Continue with sending new message

        # Отправляем новое сообщение
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

        return sent_message


def safe_message_from_callback(callback_message) -> Optional[Message]:
    """Safely extract Message from callback if accessible.

    :param callback_message: Potentially inaccessible message from callback
    :return: Message if accessible, None otherwise
    """
    if callback_message and hasattr(callback_message, "edit_text"):
        return callback_message  # type: ignore
    return None
