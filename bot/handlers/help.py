"""
Help and documentation handlers.

This module provides comprehensive help, tutorials, and documentation
for users to understand and effectively use the research AI bot.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from textwrap import dedent

from shared.logging import get_logger
from bot.handlers.utils.messages import send_or_edit_message

router = Router(name="help")
logger = get_logger(__name__)


@router.message(Command("help_detailed"))
async def command_help_detailed(message: Message) -> None:
    """Show detailed help with categories.
    
    :param message: Telegram message
    """
    try:
        help_text = dedent("""
        📚 <b>Comprehensive Help</b>
        
        Welcome to your AI research assistant! Choose a help category:
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Getting Started", callback_data="help_getting_started")],
            [InlineKeyboardButton(text="🔬 Research Tasks", callback_data="help_research_tasks")],
            [InlineKeyboardButton(text="📊 Results & Analytics", callback_data="help_results")],
            [InlineKeyboardButton(text="⚙️ Settings & Plans", callback_data="help_settings")],
            [InlineKeyboardButton(text="🧘‍♂️ Zen Mode", callback_data="help_zen_mode")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="help_faq")],
            [InlineKeyboardButton(text="🆘 Troubleshooting", callback_data="help_troubleshooting")]
        ])
        
        await send_or_edit_message(
            message, help_text, keyboard, auto_edit_recent=True
        )
        
    except Exception as e:
        logger.error(f"Error showing detailed help: {e}")
        await message.answer("❌ Error showing help.")


@router.callback_query(lambda c: c.data == "help_getting_started")
async def callback_help_getting_started(callback: CallbackQuery) -> None:
    """Show getting started guide.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        getting_started_text = dedent("""
        🚀 <b>Getting Started Guide</b>
        
        <b>1. Create Your First Task</b>
        • Press "🔬 New Task" button
        • Enter a research topic (e.g., "machine learning")
        • Wait for the AI to analyze and find papers
        
        <b>2. Monitor Progress</b>
        • Press "📊 Status" to see active tasks
        • Watch as the AI searches databases
        • Get real-time updates on findings
        
        <b>3. Review Results</b>
        • Press "📚 Results" to see findings
        • Browse through discovered papers
        • Read AI summaries and relevance scores
        
        <b>4. Optimize Your Experience</b>
        • Use specific research queries
        • Set up notifications for important findings
        • Try Zen mode for focused sessions
        
        <b>💡 Pro Tips:</b>
        • Be specific: "cancer immunotherapy" > "cancer"
        • Use current topics for best results
        • Check results regularly for new findings
        • Experiment with different query styles
        
        <b>Example Research Topics:</b>
        • "CRISPR gene editing applications"
        • "renewable energy storage solutions"
        • "artificial intelligence in healthcare"
        • "climate change mitigation strategies"
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔬 Try First Task", callback_data="new_task_wizard")],
            [InlineKeyboardButton(text="📖 Advanced Tips", callback_data="help_advanced_tips")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])
        
        await send_or_edit_message(
            callback.message, getting_started_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing getting started help: {e}")
        await callback.answer("❌ Error showing guide.")


@router.callback_query(lambda c: c.data == "help_research_tasks")
async def callback_help_research_tasks(callback: CallbackQuery) -> None:
    """Show research tasks help.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        research_help_text = dedent("""
        🔬 <b>Research Tasks Guide</b>
        
        <b>Creating Effective Tasks:</b>
        
        <b>✅ Good Examples:</b>
        • "machine learning for drug discovery"
        • "solar panel efficiency improvements 2023"
        • "ADHD treatment methods comparison"
        • "quantum computing error correction"
        
        <b>❌ Less Effective:</b>
        • "AI" (too broad)
        • "medicine" (too general)
        • "recent papers" (no specific topic)
        
        <b>🎯 Task Types:</b>
        
        <b>Specific Research:</b>
        Best for: Targeted investigations
        Example: "mRNA vaccine side effects"
        
        <b>Broad Exploration:</b>
        Best for: Topic overviews
        Example: "renewable energy technologies"
        
        <b>Comparative Analysis:</b>
        Best for: Technology comparisons
        Example: "electric vs hydrogen vehicles"
        
        <b>Trend Monitoring:</b>
        Best for: Latest developments
        Example: "ChatGPT impact on education 2024"
        
        <b>📊 Task Limits:</b>
        • Free plan: 10 tasks/day, 3 concurrent
        • Pro plan: 50 tasks/day, 10 concurrent
        • Premium: Unlimited tasks, 25 concurrent
        
        <b>⏱️ Processing Time:</b>
        • Initial results: 2-5 minutes
        • Complete analysis: 10-30 minutes
        • Complex topics: Up to 1 hour
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Task Templates", callback_data="help_task_templates")],
            [InlineKeyboardButton(text="⏱️ Processing Details", callback_data="help_processing")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])
        
        await send_or_edit_message(
            callback.message, research_help_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing research tasks help: {e}")
        await callback.answer("❌ Error showing research help.")


@router.callback_query(lambda c: c.data == "help_results")
async def callback_help_results(callback: CallbackQuery) -> None:
    """Show results and analytics help.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        results_help_text = dedent("""
        📊 <b>Results & Analytics Guide</b>
        
        <b>Understanding Your Results:</b>
        
        <b>📄 Paper Information:</b>
        • Title and authors
        • Publication date and venue  
        • Relevance score (0-100%)
        • AI-generated summary
        • Source links (arXiv, DOI, PubMed)
        
        <b>🎯 Relevance Scores:</b>
        • 90-100%: Highly relevant, key papers
        • 75-89%: Very relevant, important findings
        • 60-74%: Moderately relevant, supporting info
        • Below 60%: Less relevant, background context
        
        <b>🤖 AI Summaries:</b>
        • Key findings and conclusions
        • Methodology highlights
        • Relevance to your query
        • Important limitations or caveats
        
        <b>📈 Analytics Features:</b>
        • Task progress tracking
        • Quality metrics
        • Research trends
        • Finding categorization
        
        <b>💾 Result Management:</b>
        • Save favorite papers
        • Export results
        • Share findings
        • Create reading lists
        
        <b>🔔 Notifications:</b>
        • Set relevance thresholds
        • Get alerts for important findings
        • Choose notification frequency
        • Configure group sharing
        
        <b>📱 Mobile Optimization:</b>
        • Swipe through results
        • Quick relevance filtering
        • Offline reading support
        • Voice summaries (coming soon)
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Relevance Guide", callback_data="help_relevance")],
            [InlineKeyboardButton(text="🔔 Notifications", callback_data="help_notifications")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])
        
        await send_or_edit_message(
            callback.message, results_help_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing results help: {e}")
        await callback.answer("❌ Error showing results help.")


@router.callback_query(lambda c: c.data == "help_zen_mode")
async def callback_help_zen_mode(callback: CallbackQuery) -> None:
    """Show Zen mode help.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        zen_help_text = dedent("""
        🧘‍♂️ <b>Zen Mode Guide</b>
        
        <b>What is Zen Mode?</b>
        A focused, distraction-free research environment designed for deep concentration and mindful exploration.
        
        <b>✨ Key Features:</b>
        • Minimalist interface design
        • Notification suppression
        • Single-task focus
        • Calm result presentation
        • Progress meditation
        • Ambient environments
        
        <b>⏱️ Session Types:</b>
        
        <b>Quick Focus (25 min):</b>
        Perfect for specific questions or targeted research
        
        <b>Deep Dive (45-90 min):</b>
        Ideal for comprehensive topic exploration
        
        <b>Extended Study (2+ hours):</b>
        For major research projects or literature reviews
        
        <b>🎯 When to Use Zen Mode:</b>
        • Literature reviews
        • Thesis research
        • Deep learning sessions
        • Avoiding distractions
        • Mindful research practice
        • Stress reduction while studying
        
        <b>🔧 How to Start:</b>
        1. Use command: /zen
        2. Set your research focus
        3. Choose session duration
        4. Enter Zen environment
        5. Research happens automatically
        6. Review results mindfully
        
        <b>🧘‍♂️ Zen Benefits:</b>
        • Improved focus quality
        • Reduced information overload
        • Better retention
        • Less research anxiety
        • Enhanced comprehension
        • Peaceful discovery process
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧘‍♂️ Try Zen Mode", callback_data="zen_create_start")],
            [InlineKeyboardButton(text="⚙️ Zen Settings", callback_data="help_zen_settings")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])
        
        await send_or_edit_message(
            callback.message, zen_help_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing Zen help: {e}")
        await callback.answer("❌ Error showing Zen help.")


@router.callback_query(lambda c: c.data == "help_faq")
async def callback_help_faq(callback: CallbackQuery) -> None:
    """Show frequently asked questions.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        faq_text = dedent("""
        ❓ <b>Frequently Asked Questions</b>
        
        <b>Q: How does the AI find papers?</b>
        A: We search multiple databases (arXiv, PubMed, Google Scholar) and use AI to analyze relevance and quality.
        
        <b>Q: How accurate are the AI summaries?</b>
        A: Our AI provides high-quality summaries but always verify important information with the original papers.
        
        <b>Q: Can I search for papers in other languages?</b>
        A: Currently we focus on English papers, but multi-language support is planned.
        
        <b>Q: How recent are the papers?</b>
        A: We include papers from the last 5 years primarily, with some older seminal works when relevant.
        
        <b>Q: Can I export my results?</b>
        A: Yes! You can export results as PDF, CSV, or BibTeX formats (feature in development).
        
        <b>Q: Is my research data private?</b>
        A: Yes, your research queries and results are private and not shared with third parties.
        
        <b>Q: How do I upgrade my plan?</b>
        A: Use /account to see upgrade options or contact support for assistance.
        
        <b>Q: Can I use this for commercial research?</b>
        A: Yes, but check our terms of service for specific commercial use guidelines.
        
        <b>Q: What if I find irrelevant results?</b>
        A: Use more specific queries, adjust relevance thresholds, or try different search terms.
        
        <b>Q: Can I collaborate with team members?</b>
        A: Team features are in development. Currently you can share results via group chats.
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Contact Support", callback_data="help_contact")],
            [InlineKeyboardButton(text="📖 Terms of Service", callback_data="help_terms")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])
        
        await send_or_edit_message(
            callback.message, faq_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing FAQ: {e}")
        await callback.answer("❌ Error showing FAQ.")


@router.callback_query(lambda c: c.data == "help_main_menu")
async def callback_help_main_menu(callback: CallbackQuery) -> None:
    """Return to main help menu.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        help_text = dedent("""
        📚 <b>Comprehensive Help</b>
        
        Welcome to your AI research assistant! Choose a help category:
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Getting Started", callback_data="help_getting_started")],
            [InlineKeyboardButton(text="🔬 Research Tasks", callback_data="help_research_tasks")],
            [InlineKeyboardButton(text="📊 Results & Analytics", callback_data="help_results")],
            [InlineKeyboardButton(text="⚙️ Settings & Plans", callback_data="help_settings")],
            [InlineKeyboardButton(text="🧘‍♂️ Zen Mode", callback_data="help_zen_mode")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="help_faq")],
            [InlineKeyboardButton(text="🆘 Troubleshooting", callback_data="help_troubleshooting")]
        ])
        
        await send_or_edit_message(
            callback.message, help_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing help main menu: {e}")
        await callback.answer("❌ Error showing help menu.")


# TODO: Implement additional help sections:
# - /help_troubleshooting - Common issues and solutions
# - /help_settings - Settings and configuration guide
# - /help_advanced_tips - Advanced usage patterns
# - /help_api - API documentation (if applicable)
# - /help_contact - Support contact information
