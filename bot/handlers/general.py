from aiogram import Router, F

from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
)
from textwrap import dedent
from shared.logging import get_logger

from bot.handlers.utils.messages import send_or_edit_message
from bot.handlers.utils.ui import get_main_menu_keyboard

router = Router(name="general")

logger = get_logger(__name__)


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """Handle start command with comprehensive welcome message.

    :param message: Telegram message
    """
    user_name = "friend"
    if message.from_user and message.from_user.full_name:
        user_name = message.from_user.full_name

    welcome_text = dedent(f"""
    🚀 <b>Welcome, {user_name}!</b>

    I'm your AI research assistant that helps you discover and analyze scientific papers from academic databases.

    <b>🎯 What I can do:</b>
    • Search through arXiv, PubMed, and Google Scholar
    • Provide AI-powered summaries and analysis
    • Find the most relevant studies for your topic
    • Deliver results with relevance scores (0-100%)
    • Support research task creation and monitoring

    <b>⚡ Quick Start (3 steps):</b>
    1️⃣ Press "🔬 New Task" below
    2️⃣ Enter your research topic (e.g., "machine learning", "climate change")
    3️⃣ Get AI-curated results with summaries

    <b>💡 Pro Tips:</b>
    • Use specific queries for better results
    • Try topics like "CRISPR gene editing" or "renewable energy storage"
    • Check "❓ Help" for detailed guides and examples

    Ready to start your research journey? 👇
    """)

    await send_or_edit_message(message, welcome_text, get_main_menu_keyboard())


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
    """Show comprehensive help guide with examples and tips.

    :param message: Telegram message to respond to
    """
    help_text = dedent("""
    ❓ <b>How to Use Your Research Assistant</b>

    <b>🚀 Getting Started:</b>
    1. Press "🔬 New Task" to create a research task
    2. Enter your topic (see examples below)
    3. Wait for AI analysis (2-30 minutes depending on complexity)
    4. Check "📊 Status" to see progress
    5. View results in "📚 Results"

    <b>📝 Writing Effective Research Queries:</b>

    <b>✅ Good Examples:</b>
    • "machine learning for drug discovery"
    • "CRISPR gene editing applications"
    • "climate change mitigation strategies"
    • "artificial intelligence in healthcare"

    <b>❌ Less Effective:</b>
    • "AI" (too broad)
    • "science" (too vague)
    • "latest research" (no specific topic)

    <b>🎯 Research Types:</b>
    • <b>Specific:</b> "mRNA vaccines side effects"
    • <b>Broad:</b> "renewable energy technologies"
    • <b>Comparative:</b> "electric vs hydrogen vehicles"

    <b>⚙️ Additional Commands:</b>
    /help_detailed - Comprehensive help with tutorials
    /account - View your plan and usage
    /notifications_on - Enable result notifications
    /notifications_off - Disable notifications
    /group_on - Share results in group chat
    /group_off - Back to personal notifications

    <b>📊 Understanding Results:</b>
    • Relevance scores (0-100%) show how well papers match your query
    • AI summaries highlight key findings
    • Source links to arXiv, DOI, PubMed, Google Scholar
    • Results from arXiv, PubMed, and Google Scholar databases

    <b>💡 Pro Tips:</b>
    • Be specific for better results
    • Use current topics for recent papers
    • Check results regularly for new findings
    • Try different query styles

    <b>🆘 Need More Help?</b>
    Use /help_detailed for step-by-step tutorials!
    """)

    await send_or_edit_message(message, help_text)
