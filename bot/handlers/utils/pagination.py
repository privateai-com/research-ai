from typing import List, Tuple, Any, Callable, Awaitable, Optional
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    MaybeInaccessibleMessage,
)
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery

from bot.handlers.utils.utils import cut_text
from shared.logging import get_logger

logger = get_logger(__name__)


class PaginationHandler:
    """Generic pagination handler for bot messages."""

    def __init__(
        self,
        items: List[Any],
        per_page: int = 5,
        title: str = "Items",
        item_formatter: Optional[Callable[[Any, int], str]] = None,
        callback_prefix: str = "pagination",
    ):
        """Initialize pagination handler.

        :param items: List of items to paginate
        :param per_page: Number of items per page
        :param title: Title for the pagination message
        :param item_formatter: Function to format individual items
        :param callback_prefix: Prefix for callback data
        """
        self.items = items
        self.per_page = per_page
        self.title = title
        self.item_formatter = item_formatter or self._default_item_formatter
        self.callback_prefix = callback_prefix
        self.total_pages = (len(items) + per_page - 1) // per_page

    def _default_item_formatter(self, item: Any, index: int) -> str:
        """Default item formatter.

        :param item: Item to format
        :param index: Item index
        :return: Formatted item string
        """
        if hasattr(item, "title") and callable(getattr(item, "title", None)):
            title = item.title()
        elif hasattr(item, "title"):
            title = str(item.title)
        elif hasattr(item, "description") and callable(
            getattr(item, "description", None)
        ):
            title = item.description()
        elif hasattr(item, "description"):
            title = str(item.description)
        else:
            title = str(item)

        return f"📄 {cut_text(title, 35)}"

    def get_page_data(self, page: int) -> Tuple[str, InlineKeyboardMarkup]:
        """Get page content and keyboard.

        :param page: Page number (0-based)
        :return: Tuple of (text, keyboard)
        """
        if not self.items:
            return f"📚 <b>No {self.title.lower()} found</b>", InlineKeyboardMarkup(
                inline_keyboard=[]
            )

        start_idx = page * self.per_page
        end_idx = start_idx + self.per_page
        page_items = self.items[start_idx:end_idx]

        # Create text
        text = f"📚 <b>{self.title}</b>\n"
        text += f"📊 <b>Page {page + 1} of {self.total_pages}</b> ({len(self.items)} total)\n\n"

        # Create keyboard with item buttons
        keyboard_buttons = []

        for i, item in enumerate(page_items):
            item_idx = start_idx + i
            button_text = self.item_formatter(item, item_idx)
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"{self.callback_prefix}_item_{item_idx}",
                    )
                ]
            )

        # Add pagination controls
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Previous",
                    callback_data=f"{self.callback_prefix}_page_{page - 1}",
                )
            )
        if page < self.total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="➡️ Next",
                    callback_data=f"{self.callback_prefix}_page_{page + 1}",
                )
            )

        if nav_buttons:
            keyboard_buttons.append(nav_buttons)

        # Add utility buttons
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text="🔄 Refresh", callback_data=f"{self.callback_prefix}_refresh"
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        return text, keyboard

    def get_item(self, index: int) -> Any:
        """Get item by index.

        :param index: Item index
        :return: Item at index
        """
        if 0 <= index < len(self.items):
            return self.items[index]
        return None


class TaskPaginationHandler(PaginationHandler):
    """Specialized pagination handler for tasks."""

    def __init__(self, tasks: List[Any]):
        """Initialize task pagination handler.

        :param tasks: List of tasks
        """
        super().__init__(
            items=tasks,
            per_page=5,
            title="Your Tasks",
            item_formatter=self._task_formatter,
            callback_prefix="task_pagination",
        )

    def _task_formatter(self, task: Any, index: int) -> str:
        """Format task for display.

        :param task: Task object
        :param index: Task index
        :return: Formatted task string
        """
        status_emoji = self._get_status_emoji(task.status)
        description = cut_text(task.description, 30)
        return f"{status_emoji} #{task.id}: {description}"

    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for task status.

        :param status: Task status
        :return: Status emoji
        """
        status_map = {
            "queued": "⏳",
            "processing": "🔄",
            "completed": "✅",
            "failed": "❌",
        }
        return status_map.get(status.lower(), "❓")


class ResultsPaginationHandler(PaginationHandler):
    """Specialized pagination handler for results."""

    def __init__(self, results: List[Tuple[Any, Any]]):
        """Initialize results pagination handler.

        :param results: List of (analysis, paper) tuples
        """
        super().__init__(
            items=results,
            per_page=5,
            title="Research Results",
            item_formatter=self._result_formatter,
            callback_prefix="results_pagination",
        )

    def _result_formatter(self, result: Tuple[Any, Any], index: int) -> str:
        """Format result for display.

        :param result: (analysis, paper) tuple
        :param index: Result index
        :return: Formatted result string
        """
        analysis, paper = result
        title = cut_text(paper.title, 35)
        relevance = analysis.relevance
        return f"📄 {title} ({relevance:.0f}%)"


async def handle_pagination_callback(
    callback: CallbackQuery,
    pagination_handler: PaginationHandler,
    page: int,
    message_editor: Callable[
        [MaybeInaccessibleMessage, str, InlineKeyboardMarkup], Awaitable[None]
    ],
) -> None:
    """Handle pagination callback.

    :param callback: Callback query
    :param pagination_handler: Pagination handler instance
    :param page: Page number
    :param message_editor: Function to edit message
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    text, keyboard = pagination_handler.get_page_data(page)

    try:
        await message_editor(callback.message, text, keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error updating pagination: {e}")
        await callback.answer("❌ Error updating page")


async def handle_pagination_refresh(
    callback: CallbackQuery,
    pagination_handler: PaginationHandler,
    message_editor: Callable[
        [MaybeInaccessibleMessage, str, InlineKeyboardMarkup], Awaitable[None]
    ],
) -> None:
    """Handle pagination refresh.

    :param callback: Callback query
    :param pagination_handler: Pagination handler instance
    :param message_editor: Function to edit message
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    text, keyboard = pagination_handler.get_page_data(0)  # Go to first page

    try:
        await message_editor(callback.message, text, keyboard)
        await callback.answer("✅ Refreshed!")
    except Exception as e:
        logger.error(f"Error refreshing pagination: {e}")
        await callback.answer("❌ Error refreshing")


async def edit_message_with_pagination(
    message: MaybeInaccessibleMessage, text: str, keyboard: InlineKeyboardMarkup
) -> None:
    """Edit message with pagination content.

    :param message: Message to edit
    :param text: New text content
    :param keyboard: New keyboard
    """
    try:
        await message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)  # type: ignore
    except Exception as e:
        logger.debug(f"Failed to edit message: {e}")
        try:
            if hasattr(message, "answer"):
                await message.answer(
                    text, parse_mode=ParseMode.HTML, reply_markup=keyboard
                )  # type: ignore
        except Exception as e2:
            logger.warning(f"Failed to send new pagination message: {e2}")
            # Last resort: try to send via bot if message has bot
            try:
                if hasattr(message, "bot") and hasattr(message, "chat"):
                    await message.bot.send_message(  # type: ignore
                        chat_id=message.chat.id,  # type: ignore
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard,
                    )
            except Exception as e3:
                logger.error(f"Completely failed to send pagination message: {e3}")
