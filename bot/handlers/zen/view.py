"""
Zen task viewing and display handlers.

This module handles the display and visualization of Zen task results,
history, and analytics in a focused research interface.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from textwrap import dedent
from datetime import datetime

from shared.logging import get_logger
from bot.handlers.utils.messages import send_or_edit_message

router = Router(name="zen_view")
logger = get_logger(__name__)

# TODO: Implement Zen task result formatting
# TODO: Implement Zen task history storage
# TODO: Implement research-focused display styling


@router.callback_query(lambda c: c.data == "zen_view_results")
async def callback_zen_view_results(callback: CallbackQuery) -> None:
    """View Zen task results in focused format.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        # TODO: Get Zen task results
        # zen_results = await get_zen_task_results(callback.from_user.id)

        results_text = dedent("""
        📋 <b>Zen Task Results</b>

        <i>Your continuous research has yielded these insights:</i>

        🔍 <b>Key Finding #1</b>
        <i>Machine learning applications in healthcare</i>
        Relevance: 94% • Cycles: 12 • Status: Active

        📄 <b>Notable Paper:</b>
        "AI-Driven Diagnostics in Clinical Settings"
        <i>Comprehensive review of current ML diagnostic tools...</i>

        ────────────────────

        🔍 <b>Key Finding #2</b>
        <i>Deep learning for medical imaging</i>
        Relevance: 91% • Cycles: 8 • Status: New

        📄 <b>Notable Paper:</b>
        "Neural Networks in Radiology"
        <i>Analysis of CNN architectures for medical image analysis...</i>

        ────────────────────

        🔍 <b>Key Finding #3</b>
        <i>Ethical considerations in medical AI</i>
        Relevance: 88% • Cycles: 15 • Status: Trending

        <i>Task results are being implemented</i>
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Detailed View", callback_data="zen_results_detailed")],
            [InlineKeyboardButton(text="🔄 Refresh Results", callback_data="zen_refresh_results")],
            [InlineKeyboardButton(text="📊 Task Analytics", callback_data="zen_task_analytics")],
            [InlineKeyboardButton(text="◀️ Back to Tasks", callback_data="zen_view_tasks")]
        ])

        await send_or_edit_message(
            callback.message, results_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error viewing Zen results: {e}")
        await callback.answer("❌ Error viewing results.")


@router.callback_query(lambda c: c.data == "zen_results_detailed")
async def callback_zen_results_detailed(callback: CallbackQuery) -> None:
    """Show detailed Zen task results.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        detailed_text = dedent("""
        📚 <b>Detailed Zen Results</b>

        <b>🧘‍♂️ Task Overview:</b>
        • Topic: Machine learning in healthcare
        • Status: Active (continuous research)
        • Daily cycles: 10
        • Total cycles: 45
        • Created: 2024-01-15

        ✨ <b>Research Insights:</b>

        <b>1. AI Diagnostic Tools</b>
        📊 Relevance: 94% • Cycles discovered: 12
        📄 Primary source: "AI-Driven Diagnostics..."

        <i>Key insights:</i>
        • Machine learning models show 92% accuracy in early disease detection
        • CNN architectures particularly effective for medical imaging
        • Integration challenges remain in clinical workflows

        <b>2. Deep Learning Applications</b>
        📊 Relevance: 91% • Cycles discovered: 8
        📄 Primary source: "Neural Networks in Radiology"

        <i>Key insights:</i>
        • Transfer learning reduces training time by 60%
        • Ensemble methods improve diagnostic confidence
        • Data privacy concerns limit adoption

        <b>3. Ethical Framework</b>
        📊 Relevance: 88% • Cycles discovered: 15
        📄 Primary source: "Ethics in Medical AI"

        <i>Key insights:</i>
        • Bias mitigation strategies are essential
        • Transparency requirements vary by jurisdiction
        • Patient consent frameworks need updating

        <i>Detailed analysis is being implemented</i>
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Export Results", callback_data="zen_export_results")],
            [InlineKeyboardButton(text="🔗 Source Links", callback_data="zen_source_links")],
            [InlineKeyboardButton(text="◀️ Back to Summary", callback_data="zen_view_results")]
        ])

        await send_or_edit_message(
            callback.message, detailed_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing detailed Zen results: {e}")
        await callback.answer("❌ Error showing detailed results.")


@router.callback_query(lambda c: c.data == "zen_history")
async def callback_zen_history(callback: CallbackQuery) -> None:
    """Show Zen task history.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        history_text = dedent("""
        📜 <b>Zen Task History</b>

        <i>Your journey of continuous research:</i>

        <b>🧘‍♂️ Active Tasks:</b>

        <b>Current - Machine Learning in Healthcare</b>
        Created: 2024-01-15 • Daily cycles: 10
        Total cycles: 45 • Best finding: 94% relevance
        Status: 🔄 Active research

        <b>🧘‍♂️ Recent Tasks:</b>

        <b>Completed - Climate Change Solutions</b>
        Created: 2024-01-10 • Completed: 2024-01-12
        Total cycles: 25 • Best finding: 91% relevance
        Status: ✅ Completed

        <b>Paused - Quantum Computing Advances</b>
        Created: 2024-01-05 • Paused: 2024-01-08
        Total cycles: 18 • Best finding: 87% relevance
        Status: ⏸️ Paused

        ────────────────────

        <b>📊 Overall Statistics:</b>
        • Total Zen tasks: 3
        • Active tasks: 1
        • Completed tasks: 1
        • Paused tasks: 1
        • Total cycles run: 88
        • Average relevance: 90.7%

        <i>Task history is being implemented</i>
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Detailed Analytics", callback_data="zen_analytics")],
            [InlineKeyboardButton(text="📤 Export History", callback_data="zen_export_history")],
            [InlineKeyboardButton(text="🧘‍♂️ Create New Task", callback_data="zen_create_start")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="zen_back_to_main")]
        ])

        await send_or_edit_message(
            callback.message, history_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing Zen history: {e}")
        await callback.answer("❌ Error showing history.")


@router.callback_query(lambda c: c.data == "zen_analytics")
async def callback_zen_analytics(callback: CallbackQuery) -> None:
    """Show Zen task analytics.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        analytics_text = dedent("""
        📈 <b>Zen Analytics</b>

        <i>Insights into your continuous research patterns:</i>

        <b>📊 Performance Overview:</b>
        • Total Zen tasks: 3
        • Active research time: 12 days
        • Average daily cycles: 8.7
        • Success rate: 94%

        <b>🎯 Research Effectiveness:</b>
        • Papers analyzed: 156
        • Relevant findings: 89
        • Quality threshold met: 92%
        • Breakthrough discoveries: 7

        <b>⏰ Research Patterns:</b>
        • Peak productivity: 14:00-16:00
        • Most active day: Tuesday
        • Average task lifespan: 8.3 days
        • Cycle efficiency: 91%

        <b>🔍 Topic Performance:</b>
        • Healthcare AI: 94% avg relevance (45 cycles)
        • Climate Science: 91% avg relevance (25 cycles)
        • Quantum Tech: 87% avg relevance (18 cycles)

        <b>📈 Trends (Last 30 Days):</b>
        • Research volume: ↗️ +23%
        • Quality improvement: ↗️ +15%
        • Cycle efficiency: ↗️ +12%
        • New discoveries: ↗️ +31%

        <b>🧘‍♂️ Zen Insights:</b>
        • Best research focus: Healthcare applications
        • Most productive pattern: 10 daily cycles
        • Optimal task duration: 7-10 days
        • Quality peak: Days 3-5 of research

        <i>Advanced analytics are being implemented</i>
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Weekly Report", callback_data="zen_weekly_report")],
            [InlineKeyboardButton(text="🎯 Topic Analysis", callback_data="zen_topic_analysis")],
            [InlineKeyboardButton(text="⏰ Time Patterns", callback_data="zen_time_patterns")],
            [InlineKeyboardButton(text="💡 Recommendations", callback_data="zen_recommendations")],
            [InlineKeyboardButton(text="◀️ Back to History", callback_data="zen_history")]
        ])

        await send_or_edit_message(
            callback.message, analytics_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing Zen analytics: {e}")
        await callback.answer("❌ Error showing analytics.")


@router.command(Command("zen_history"))
async def command_zen_history(message: Message) -> None:
    """Show Zen task history via command.

    :param message: Telegram message
    """
    if not message.from_user:
        await message.answer("❌ Error: could not determine user.")
        return

    try:
        # TODO: Get user's Zen history
        # zen_history = await get_user_zen_history(message.from_user.id)

        history_text = dedent("""
        📜 <b>Your Zen Journey</b>

        <i>A record of your continuous research:</i>

        <b>Active Tasks:</b>
        • Machine Learning in Healthcare (12 days)
        • Daily cycles: 10, Total findings: 45

        <b>Recent Tasks:</b>
        • Climate Change Solutions - Completed
        • Quantum Computing Advances - Paused

        <b>Statistics:</b>
        • Total research time: 12 days
        • Tasks completed: 1
        • Average relevance: 90.7%
        • Total cycles: 88

        Use /zen to create your first Zen task!
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧘‍♂️ Create Zen Task", callback_data="zen_create_start")],
            [InlineKeyboardButton(text="📊 View Details", callback_data="zen_history")]
        ])

        await send_or_edit_message(
            message, history_text, keyboard, 
        )

    except Exception as e:
        logger.error(f"Error showing Zen history: {e}")
        await message.answer("❌ Error showing Zen history.")


@router.callback_query(lambda c: c.data == "zen_learn_more")
async def callback_zen_learn_more(callback: CallbackQuery) -> None:
    """Show information about Zen tasks.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        learn_text = dedent("""
        🧘‍♂️ <b>About Zen Tasks</b>

        <i>Continuous research with daily cycle limits:</i>

        <b>✨ What are Zen Tasks?</b>
        Specialized research tasks that run continuously with daily cycle limits instead of global limits.

        <b>🎯 Key Features:</b>
        • Continuous background research
        • Daily cycle limits (resets every day)
        • No global cycle restrictions
        • Automatic literature monitoring
        • Long-term knowledge building

        <b>🔧 How it Works:</b>
        1. Set your research topic
        2. Choose daily cycle limit
        3. Task runs continuously in background
        4. Cycles reset daily (based on your plan)
        5. Receive regular updates on new findings

        <b>💡 Perfect For:</b>
        • Ongoing literature monitoring
        • Trend tracking in your field
        • Staying current with research
        • Long-term topic exploration
        • Building comprehensive knowledge bases

        <b>⏰ Daily Cycle Limits:</b>
        • Free plan: 5 cycles/day
        • Pro plan: 20 cycles/day
        • Premium: 50+ cycles/day
        • Cycles reset at 00:00 UTC daily

        <b>🎯 Benefits:</b>
        • Never miss important research
        • Build knowledge over time
        • Efficient resource usage
        • Stay current without constant checking
        • Perfect for ongoing research interests

        Ready to start continuous research?
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧘‍♂️ Create Zen Task", callback_data="zen_create_start")],
            [InlineKeyboardButton(text="📊 View Examples", callback_data="zen_examples")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="zen_history")]
        ])

        await send_or_edit_message(
            callback.message, learn_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing Zen information: {e}")
        await callback.answer("❌ Error showing information.")


# TODO: Implement additional Zen viewing features:
# - Task comparison and benchmarking
# - Research trend visualization
# - Cycle efficiency analysis
# - Topic evolution tracking
# - Export and sharing capabilities


@router.callback_query(lambda c: c.data == "zen_view_results")
async def callback_zen_view_results(callback: CallbackQuery) -> None:
    """View Zen session results in calm format.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        # TODO: Get Zen session results
        # zen_results = await get_zen_session_results(callback.from_user.id)
        
        results_text = dedent("""
        📋 <b>Zen Session Results</b>
        
        <i>Your focused research has yielded these insights:</i>
        
        🔍 <b>Key Finding #1</b>
        <i>Machine learning applications in healthcare</i>
        Relevance: 94% • Quality: High
        
        📄 <b>Notable Paper:</b>
        "AI-Driven Diagnostics in Clinical Settings"
        <i>Comprehensive review of current ML diagnostic tools...</i>
        
        ────────────────────
        
        🔍 <b>Key Finding #2</b>
        <i>Deep learning for medical imaging</i>
        Relevance: 91% • Quality: High
        
        📄 <b>Notable Paper:</b>
        "Neural Networks in Radiology"
        <i>Analysis of CNN architectures for medical image analysis...</i>
        
        ────────────────────
        
        🔍 <b>Key Finding #3</b>
        <i>Ethical considerations in medical AI</i>
        Relevance: 88% • Quality: High
        
        <i>Session results are being implemented</i>
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Detailed View", callback_data="zen_results_detailed")],
            [InlineKeyboardButton(text="💾 Save Session", callback_data="zen_save_session")],
            [InlineKeyboardButton(text="📊 Session Analytics", callback_data="zen_session_analytics")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="zen_back_to_session")]
        ])
        
        await send_or_edit_message(
            callback.message, results_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error viewing Zen results: {e}")
        await callback.answer("❌ Error viewing results.")


@router.callback_query(lambda c: c.data == "zen_results_detailed")
async def callback_zen_results_detailed(callback: CallbackQuery) -> None:
    """Show detailed Zen session results.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        detailed_text = dedent("""
        📚 <b>Detailed Zen Results</b>
        
        <b>🧘‍♂️ Session Overview:</b>
        • Focus: Machine learning in healthcare
        • Duration: 25 minutes
        • Papers analyzed: 12
        • Quality threshold: High (85%+)
        
        ✨ <b>Research Insights:</b>
        
        <b>1. AI Diagnostic Tools</b>
        📊 Relevance: 94%
        📄 Primary source: "AI-Driven Diagnostics..."
        
        <i>Key insights:</i>
        • Machine learning models show 92% accuracy in early disease detection
        • CNN architectures particularly effective for medical imaging
        • Integration challenges remain in clinical workflows
        
        <b>2. Deep Learning Applications</b>
        📊 Relevance: 91%
        📄 Primary source: "Neural Networks in Radiology"
        
        <i>Key insights:</i>
        • Transfer learning reduces training time by 60%
        • Ensemble methods improve diagnostic confidence
        • Data privacy concerns limit adoption
        
        <b>3. Ethical Framework</b>
        📊 Relevance: 88%
        📄 Primary source: "Ethics in Medical AI"
        
        <i>Key insights:</i>
        • Bias mitigation strategies are essential
        • Transparency requirements vary by jurisdiction
        • Patient consent frameworks need updating
        
        <i>Detailed analysis is being implemented</i>
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Export Results", callback_data="zen_export_results")],
            [InlineKeyboardButton(text="🔗 Source Links", callback_data="zen_source_links")],
            [InlineKeyboardButton(text="◀️ Back to Summary", callback_data="zen_view_results")]
        ])
        
        await send_or_edit_message(
            callback.message, detailed_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing detailed Zen results: {e}")
        await callback.answer("❌ Error showing detailed results.")


@router.callback_query(lambda c: c.data == "zen_history")
async def callback_zen_history(callback: CallbackQuery) -> None:
    """Show Zen session history.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        history_text = dedent("""
        📜 <b>Zen Session History</b>
        
        <i>Your journey of focused research:</i>
        
        <b>🧘‍♂️ Recent Sessions:</b>
        
        <b>Today - 14:30</b>
        Focus: Machine learning in healthcare
        Duration: 25 minutes • Results: 8 findings
        Quality: Excellent ⭐⭐⭐⭐⭐
        
        <b>Yesterday - 16:45</b>
        Focus: Climate change solutions
        Duration: 45 minutes • Results: 12 findings  
        Quality: Very Good ⭐⭐⭐⭐
        
        <b>2 days ago - 10:15</b>
        Focus: Quantum computing advances
        Duration: 90 minutes • Results: 18 findings
        Quality: Excellent ⭐⭐⭐⭐⭐
        
        ────────────────────
        
        <b>📊 Overall Statistics:</b>
        • Total Zen time: 160 minutes
        • Sessions completed: 3
        • Average quality: 4.7/5
        • Focus efficiency: 94%
        
        <i>Session history is being implemented</i>
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Detailed Analytics", callback_data="zen_analytics")],
            [InlineKeyboardButton(text="💾 Export History", callback_data="zen_export_history")],
            [InlineKeyboardButton(text="🧘‍♂️ New Session", callback_data="zen_create_start")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="zen_back_to_main")]
        ])
        
        await send_or_edit_message(
            callback.message, history_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing Zen history: {e}")
        await callback.answer("❌ Error showing history.")


@router.callback_query(lambda c: c.data == "zen_analytics")
async def callback_zen_analytics(callback: CallbackQuery) -> None:
    """Show Zen session analytics.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        analytics_text = dedent("""
        📈 <b>Zen Analytics</b>
        
        <i>Insights into your focused research patterns:</i>
        
        <b>🕐 Time Patterns:</b>
        • Peak focus time: 14:00-16:00
        • Average session: 53 minutes
        • Preferred duration: 25-45 minutes
        • Best day: Tuesday
        
        <b>🎯 Focus Quality:</b>
        • Interruption rate: 2%
        • Focus efficiency: 94%
        • Quality trend: ↗️ Improving
        • Consistency score: 4.7/5
        
        <b>🔍 Research Effectiveness:</b>
        • Papers per session: 14 avg
        • Relevance rate: 89%
        • Quality threshold hits: 92%
        • Breakthrough moments: 7
        
        <b>📊 Topic Distribution:</b>
        • AI/ML: 40%
        • Healthcare: 25%
        • Climate science: 20%
        • Quantum tech: 15%
        
        <b>🧘‍♂️ Zen Progress:</b>
        • Total mindful time: 160 min
        • Sessions this week: 3
        • Focus improvement: +15%
        • Stress reduction: 23%
        
        <i>Advanced analytics are being implemented</i>
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Weekly Report", callback_data="zen_weekly_report")],
            [InlineKeyboardButton(text="🎯 Focus Trends", callback_data="zen_focus_trends")],
            [InlineKeyboardButton(text="💡 Recommendations", callback_data="zen_recommendations")],
            [InlineKeyboardButton(text="◀️ Back to History", callback_data="zen_history")]
        ])
        
        await send_or_edit_message(
            callback.message, analytics_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing Zen analytics: {e}")
        await callback.answer("❌ Error showing analytics.")


@router.command(Command("zen_history"))
async def command_zen_history(message: Message) -> None:
    """Show Zen session history via command.
    
    :param message: Telegram message
    """
    if not message.from_user:
        await message.answer("❌ Error: could not determine user.")
        return
    
    try:
        # TODO: Get user's Zen history
        # zen_history = await get_user_zen_history(message.from_user.id)
        
        history_text = dedent("""
        📜 <b>Your Zen Journey</b>
        
        <i>A peaceful record of your focused research:</i>
        
        <b>Recent Sessions:</b>
        • No Zen sessions yet
        
        <b>Statistics:</b>
        • Total focus time: 0 minutes
        • Sessions completed: 0
        • Average quality: N/A
        
        Ready to begin your first Zen session?
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧘‍♂️ Start First Session", callback_data="zen_create_start")],
            [InlineKeyboardButton(text="❓ Learn About Zen", callback_data="zen_learn_more")]
        ])
        
        await send_or_edit_message(
            message, history_text, keyboard, 
        )
        
    except Exception as e:
        logger.error(f"Error showing Zen history: {e}")
        await message.answer("❌ Error showing Zen history.")


@router.callback_query(lambda c: c.data == "zen_learn_more")
async def callback_zen_learn_more(callback: CallbackQuery) -> None:
    """Show information about Zen mode.
    
    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return
    
    try:
        learn_text = dedent("""
        🧘‍♂️ <b>About Zen Mode</b>
        
        <i>Discover the power of focused research:</i>
        
        <b>✨ What is Zen Mode?</b>
        A distraction-free research environment designed for deep focus and mindful exploration of scientific literature.
        
        <b>🎯 Key Benefits:</b>
        • Enhanced concentration and focus
        • Reduced information overload
        • Peaceful, organized results
        • Quality over quantity approach
        • Mindful research practice
        
        <b>🔧 How it Works:</b>
        1. Set your research focus and duration
        2. Enter calm, minimal interface
        3. Research happens automatically
        4. Results appear in peaceful format
        5. Review insights mindfully
        
        <b>🧘‍♂️ Perfect For:</b>
        • Literature reviews
        • Deep research sessions
        • Focused learning
        • Mindful exploration
        • Stress-free discovery
        
        <b>⏱️ Session Types:</b>
        • Quick Focus (25 min) - Perfect for specific topics
        • Deep Dive (45-90 min) - Comprehensive exploration
        • Extended Study (2+ hours) - Major research projects
        
        Ready to experience focused research?
        """)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧘‍♂️ Try Zen Mode", callback_data="zen_create_start")],
            [InlineKeyboardButton(text="⚙️ Zen Settings", callback_data="zen_global_settings")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="zen_history")]
        ])
        
        await send_or_edit_message(
            callback.message, learn_text, keyboard, edit_mode=True
        )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing Zen information: {e}")
        await callback.answer("❌ Error showing information.")


# TODO: Implement additional Zen viewing features:
# - Advanced result filtering and sorting
# - Zen session sharing and export
# - Mindfulness integration (meditation prompts)
# - Focus quality visualization
# - Research pattern analysis
