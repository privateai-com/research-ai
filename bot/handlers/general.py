from aiogram import Router, F

from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from textwrap import dedent
from shared.logging import get_logger

from bot.handlers.utils.messages import send_or_edit_message
from bot.handlers.utils.ui import get_main_menu_keyboard

router = Router(name="general")

logger = get_logger(__name__)


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_name = "friend"
    if message.from_user and message.from_user.full_name:
        user_name = message.from_user.full_name

    welcome_text = dedent(f"""
    👋 <b>Hello, {user_name}!</b>

    I find and analyze research papers for you across scientific databases.

    <b>🔬 Quick start:</b>
    • Press "🔬 New Task" to research any topic
    • I'll search, analyze, and send you the best findings
    • Check "📊 Status" to see progress

    Ready to explore? 👇
    """)

    await send_or_edit_message(
        message, welcome_text, get_main_menu_keyboard(), auto_edit_recent=True
    )


@router.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    """Show help message with easy navigation."""
    await show_help_guide(message)


@router.message(Command("commands"))
async def command_commands_handler(message: Message) -> None:
    """Show all available commands."""
    await show_help_guide(message)


@router.message(F.text == "❓ Help")
async def menu_help_handler(message: Message) -> None:
    """Handle help button from main menu."""
    await show_help_guide(message)


async def show_help_guide(message: Message) -> None:
    """Show simple help guide.

    :param message: Telegram message to respond to
    """
    help_text = dedent("""
    ❓ <b>Simple Commands</b>

    <b>📱 Main Buttons:</b>
    🔬 New Task - Create research task
    📊 Status - Check task progress  
    📚 Results - View findings
    ❓ Help - This message

    <b>⚙️ Optional Commands:</b>
    /account - View your plan
    /notifications_on - Enable alerts
    /notifications_off - Disable alerts
    /group_on - Share in group (use in group)
    /group_off - Back to personal chat

    <b>💡 Examples:</b>
    "cancer treatment", "solar energy", "AI applications"

    That's all you need to know!
    """)

    await send_or_edit_message(message, help_text, auto_edit_recent=True)
