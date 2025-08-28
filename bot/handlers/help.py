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
        📚 <b>Comprehensive Help Guide</b>

        Choose a category below to learn more about using your AI research assistant:
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Getting Started", callback_data="help_getting_started")],
            [InlineKeyboardButton(text="🔬 Research Tasks", callback_data="help_research_tasks")],
            [InlineKeyboardButton(text="📊 Results & Analytics", callback_data="help_results")],
            [InlineKeyboardButton(text="⚙️ Settings & Notifications", callback_data="help_settings")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="help_faq")],
            [InlineKeyboardButton(text="🆘 Troubleshooting", callback_data="help_troubleshooting")]
        ])

        await send_or_edit_message(
            message, help_text, keyboard
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
        • Wait for the AI to search and analyze papers (2-30 minutes)

        <b>2. Monitor Progress</b>
        • Press "📊 Status" to see active tasks
        • The AI searches arXiv, PubMed, and Google Scholar
        • Get notifications when complete (if enabled)

        <b>3. Review Results</b>
        • Press "📚 Results" to see findings
        • Browse through discovered papers
        • Read AI summaries and relevance scores (0-100%)
        • Click source links to view papers

        <b>4. Optimize Your Experience</b>
        • Use specific research queries for better results
        • Enable notifications with /notifications_on
        • Check your usage limits with /account

        <b>💡 Pro Tips:</b>
        • Be specific: "cancer immunotherapy 2023" > "cancer"
        • Use current topics for best results
        • Check results regularly for new findings
        • Try different query styles and specificity levels

        <b>Example Research Topics:</b>
        • "CRISPR gene editing applications"
        • "renewable energy storage solutions"
        • "artificial intelligence in healthcare"
        • "climate change mitigation strategies"
        • "machine learning for drug discovery"
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔬 Try First Task", callback_data="new_task_wizard")],
            [InlineKeyboardButton(text="📖 Advanced Tips", callback_data="help_advanced_tips")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])
        
        await send_or_edit_message(
            callback.message, getting_started_text, keyboard, navigation_context=True
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
        • Free plan: 10 tasks/day, 3 concurrent maximum
        • Only free plan is currently available

        <b>⏱️ Processing Time:</b>
        • Simple topics: 2-5 minutes
        • Complex topics: 10-30 minutes
        • Depends on research availability in databases

        <b>🔍 Databases Searched:</b>
        • arXiv (physics, math, computer science)
        • PubMed (biomedical research)
        • Google Scholar (broad academic coverage)
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Task Templates", callback_data="help_task_templates")],
            [InlineKeyboardButton(text="⏱️ Processing Details", callback_data="help_processing")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])
        
        await send_or_edit_message(
            callback.message, research_help_text, keyboard, navigation_context=True
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
        • Source links (arXiv, DOI, PubMed, Google Scholar)

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

        <b>🔍 Source Links:</b>
        • arXiv: Direct link to preprint
        • DOI: Link to published paper
        • PubMed: Link to biomedical abstract
        • Google Scholar: Additional search results

        <b>💾 Result Management:</b>
        • Results are saved in your account
        • View anytime through "📚 Results" button
        • Save individual results (feature in development)
        • Export functionality not currently available

        <b>🔔 Notifications:</b>
        • Enable with /notifications_on
        • Get alerts for high-relevance results (75%+)
        • Disable with /notifications_off
        • Share results in group chats with /group_on

        <b>📱 Navigation:</b>
        • Use pagination buttons for more results
        • Click individual results for details
        • Return to task list with back buttons
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Relevance Guide", callback_data="help_relevance")],
            [InlineKeyboardButton(text="🔔 Notifications", callback_data="help_notifications")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])
        
        await send_or_edit_message(
            callback.message, results_help_text, keyboard, navigation_context=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing results help: {e}")
        await callback.answer("❌ Error showing results help.")


# Zen Mode help removed - feature not currently implemented
# TODO: Add Zen mode help when feature is enabled


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
        A: We search across three academic databases (arXiv, PubMed, and Google Scholar) and use AI to analyze relevance and provide summaries of the most important findings.

        <b>Q: How accurate are the AI summaries?</b>
        A: Our AI provides summaries based on paper abstracts and content, but we always recommend reviewing the original papers for complete and accurate information.

        <b>Q: Can I search for papers in other languages?</b>
        A: Currently we focus on English-language academic papers, as these databases primarily contain English content.

        <b>Q: How recent are the papers?</b>
        A: We search across recent papers (typically last 5-10 years) and include seminal works when relevant. The exact time range depends on the database and topic.

        <b>Q: Is my research data private?</b>
        A: Yes, your research queries and results are stored privately and not shared with third parties.

        <b>Q: Can I use this for commercial research?</b>
        A: Yes, you can use the bot for commercial research purposes within our fair usage guidelines.

        <b>Q: What if I find irrelevant results?</b>
        A: Try using more specific search terms, add context like years or methodologies, or try synonyms and related terms to get better results.

        <b>Q: How long does a research task take?</b>
        A: Simple topics take 2-5 minutes, while complex or broad topics can take 10-30 minutes depending on the amount of relevant research available.

        <b>Q: Can I run multiple research tasks at once?</b>
        A: Yes, you can run up to 3 tasks concurrently on the free plan. Check /account for your current limits.

        <b>Q: What databases do you search?</b>
        A: We search three databases: arXiv (physics, math, computer science), PubMed (biomedical research), and Google Scholar (broad academic coverage).

        <b>Q: How do relevance scores work?</b>
        A: Scores from 0-100% indicate how well each paper matches your search query, with higher scores being more relevant to your specific research needs.

        <b>Q: Can I save or export results?</b>
        A: Results are saved in your account. You can view them anytime, but export functionality (PDF, CSV, BibTeX) is not currently available.

        <b>Q: Are there paid plans available?</b>
        A: Currently only the free plan is available. Premium features may be added in future updates.
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔬 Try Research Task", callback_data="new_task_wizard")],
            [InlineKeyboardButton(text="🆘 Troubleshooting", callback_data="help_troubleshooting")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])
        
        await send_or_edit_message(
            callback.message, faq_text, keyboard, navigation_context=True
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
            [InlineKeyboardButton(text="⚙️ Settings & Notifications", callback_data="help_settings")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="help_faq")],
            [InlineKeyboardButton(text="🆘 Troubleshooting", callback_data="help_troubleshooting")]
        ])
        
        await send_or_edit_message(
            callback.message, help_text, keyboard, navigation_context=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing help main menu: {e}")
        await callback.answer("❌ Error showing help menu.")


@router.callback_query(lambda c: c.data == "help_settings")
async def callback_help_settings(callback: CallbackQuery) -> None:
    """Show settings and notifications help.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        settings_help_text = dedent("""
        ⚙️ <b>Settings & Notifications Guide</b>

        <b>🔔 Notification Settings:</b>

        <b>Enable Notifications:</b>
        Use /notifications_on to receive alerts when:
        • Your research tasks are completed
        • New results become available (75%+ relevance threshold)

        <b>Disable Notifications:</b>
        Use /notifications_off to stop receiving notifications.

        <b>🎯 Notification Types:</b>
        • <b>Task Complete:</b> When AI analysis finishes
        • <b>New Results:</b> When papers are found and analyzed
        • <b>Group Sharing:</b> Share results in group chats

        <b>📊 Account Information:</b>
        Use /account to view:
        • Your current plan and limits
        • Task usage statistics
        • Account status and features

        <b>🔧 Current Features:</b>
        • Free plan: 10 tasks/day, 3 concurrent
        • Automatic result delivery
        • Relevance-based paper ranking
        • Search across arXiv, PubMed, Google Scholar
        • Group chat result sharing

        <b>💡 Tips:</b>
        • Enable notifications for important research
        • Monitor your usage with /account
        • Use /group_on in group chats to share results
        • Only free plan is currently available
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Enable Notifications", callback_data="notifications_on")],
            [InlineKeyboardButton(text="🔕 Disable Notifications", callback_data="notifications_off")],
            [InlineKeyboardButton(text="📊 View Account", callback_data="show_account")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])

        await send_or_edit_message(
            callback.message, settings_help_text, keyboard, navigation_context=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing settings help: {e}")
        await callback.answer("❌ Error showing settings help.")


@router.callback_query(lambda c: c.data == "help_troubleshooting")
async def callback_help_troubleshooting(callback: CallbackQuery) -> None:
    """Show troubleshooting guide.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        troubleshooting_text = dedent("""
        🆘 <b>Troubleshooting Guide</b>

        <b>🔄 Task Issues:</b>

        <b>"Task is taking too long"</b>
        • Complex topics can take 10-30 minutes
        • Check status with "📊 Status" button
        • Try more specific search terms
        • Some topics have more research available than others

        <b>"No results found"</b>
        • Try broader or different keywords
        • Check spelling and terminology
        • Some topics may have limited research in our databases
        • Try searching in English if using other languages

        <b>"Irrelevant results"</b>
        • Use more specific search terms
        • Add context (e.g., "2023", "clinical trial")
        • Try synonyms or related terms
        • Use technical terminology

        <b>📱 Bot Issues:</b>

        <b>"Bot not responding"</b>
        • Check your internet connection
        • Try restarting the conversation with /start
        • The bot may be processing tasks (check /status)

        <b>"Buttons not working"</b>
        • Refresh the message
        • Try using text commands instead
        • Restart the bot if needed
        • Some buttons may not be implemented yet

        <b>🔍 Search Optimization:</b>

        <b>Improve Your Queries:</b>
        • Add year: "machine learning 2023"
        • Specify field: "cardiology research methods"
        • Use technical terms: "neural network architecture"
        • Add context: "clinical applications of CRISPR"

        <b>🎯 Best Practices:</b>
        • Start with broad topics, then narrow down
        • Use current terminology and buzzwords
        • Include specific methodologies when known
        • Try multiple related search terms
        • Use English for best results

        <b>📊 Understanding Limits:</b>
        • Free plan: 10 tasks/day, 3 concurrent maximum
        • Check /account for your current usage
        • Tasks are processed sequentially when limit reached

        <b>📞 Still Need Help?</b>
        • Check /help_detailed for more guides
        • Review FAQ section for common questions
        • We search arXiv, PubMed, and Google Scholar databases
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Try New Task", callback_data="new_task_wizard")],
            [InlineKeyboardButton(text="❓ FAQ", callback_data="help_faq")],
            [InlineKeyboardButton(text="◀️ Back to Help", callback_data="help_main_menu")]
        ])

        await send_or_edit_message(
            callback.message, troubleshooting_text, keyboard, navigation_context=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing troubleshooting help: {e}")
        await callback.answer("❌ Error showing troubleshooting help.")


# TODO: Implement additional help sections when features are available:
# - /help_advanced_tips - Advanced usage patterns
# - /help_api - API documentation (if applicable)
# - /help_contact - Support contact information
