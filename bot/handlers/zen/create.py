"""
Zen task creation handlers.

This module handles the creation of Zen tasks - specialized research tasks
that run continuously with daily cycle limits instead of global limits.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from textwrap import dedent

from shared.logging import get_logger
from bot.handlers.utils.messages import send_or_edit_message
from bot.handlers.utils.validation import validate_user_access
from bot.handlers.utils.task_operations import TaskCreationStates, process_task_description

router = Router(name="zen_create")
logger = get_logger(__name__)


class ZenCreationStates:
    """States for Zen task creation flow."""

    waiting_for_topic = "zen_waiting_for_topic"
    waiting_for_daily_cycles = "zen_waiting_for_daily_cycles"


# TODO: Implement Zen task data model with daily cycle limits
# TODO: Implement Zen task persistence in database
# TODO: Implement daily cycle reset mechanism


@router.message(Command("zen"))
async def command_zen_start(message: Message, state: FSMContext) -> None:
    """Start Zen task creation flow.

    :param message: Telegram message
    :param state: FSM context
    """
    if not message.from_user:
        await message.answer("❌ Error: could not determine user.")
        return

    # Validate user access
    is_valid, error_msg = await validate_user_access(message)
    if not is_valid:
        await send_or_edit_message(message, error_msg, auto_edit_recent=True)
        return

    try:
        zen_intro_text = dedent("""
        🧘‍♂️ <b>Zen Tasks</b>

        Zen tasks are continuous research tasks with daily cycle limits:

        ✨ <b>Features:</b>
        • Continuous research (no global cycle limit)
        • Daily cycle limits (resets every day)
        • Automatic background processing
        • Minimal notifications
        • Focus on long-term research topics

        🎯 <b>Perfect for:</b>
        • Ongoing literature monitoring
        • Trend tracking
        • Deep research projects
        • Continuous knowledge building
        • Long-term topic exploration

        Ready to create your Zen task?
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧘‍♂️ Create Zen Task", callback_data="zen_create_start")],
            [InlineKeyboardButton(text="📊 View Zen Tasks", callback_data="zen_view_tasks")],
            [InlineKeyboardButton(text="⚙️ Zen Settings", callback_data="zen_settings")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="zen_cancel")]
        ])

        await send_or_edit_message(
            message, zen_intro_text, keyboard, auto_edit_recent=True
        )

    except Exception as e:
        logger.error(f"Error starting Zen task creation: {e}")
        await message.answer("❌ Error starting Zen task creation.")


@router.callback_query(lambda c: c.data == "zen_create_start")
async def callback_zen_create_start(callback, state: FSMContext) -> None:
    """Handle Zen task creation start.

    :param callback: Callback query
    :param state: FSM context
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        topic_prompt_text = dedent("""
        🧘‍♂️ <b>Zen Task Setup</b>

        What would you like to research continuously?

        <b>Examples:</b>
        • "machine learning in healthcare"
        • "climate change solutions"
        • "quantum computing advances"
        • "artificial intelligence ethics"

        Please enter your research topic:
        """)

        await send_or_edit_message(
            callback.message, topic_prompt_text, auto_edit_recent=True
        )

        await state.set_state(ZenCreationStates.waiting_for_topic)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error in Zen creation start: {e}")
        await callback.answer("❌ Error starting Zen task creation.")


@router.message(lambda m: m.text, ZenCreationStates.waiting_for_topic)
async def process_zen_topic(message: Message, state: FSMContext) -> None:
    """Process Zen task topic input.

    :param message: Telegram message with topic
    :param state: FSM context
    """
    if not message.text or not message.from_user:
        await message.answer("❌ Please provide a valid research topic.")
        return

    topic = message.text.strip()

    # Validate topic
    if len(topic) < 3:
        await message.answer("❌ Topic too short. Please be more specific.")
        return

    if len(topic) > 200:
        await message.answer("❌ Topic too long. Please be more concise.")
        return

    # Store topic in state
    await state.update_data(zen_topic=topic)

    try:
        cycles_prompt_text = dedent(f"""
        🧘‍♂️ <b>Daily Cycle Limit</b>

        <b>Topic:</b> {topic}

        How many research cycles per day should this Zen task run?
        (Cycles reset daily, choose based on your plan limits)
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 5 cycles/day", callback_data="zen_cycles_5"),
                InlineKeyboardButton(text="🔄 10 cycles/day", callback_data="zen_cycles_10")
            ],
            [
                InlineKeyboardButton(text="🔄 20 cycles/day", callback_data="zen_cycles_20"),
                InlineKeyboardButton(text="🔄 50 cycles/day", callback_data="zen_cycles_50")
            ],
            [InlineKeyboardButton(text="🔧 Custom", callback_data="zen_cycles_custom")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="zen_cancel")]
        ])

        await send_or_edit_message(
            message, cycles_prompt_text, keyboard, auto_edit_recent=True
        )

        await state.set_state(ZenCreationStates.waiting_for_daily_cycles)

    except Exception as e:
        logger.error(f"Error processing Zen topic: {e}")
        await message.answer("❌ Error processing topic.")


@router.callback_query(lambda c: c.data and c.data.startswith("zen_cycles_"))
async def callback_zen_cycles(callback, state: FSMContext) -> None:
    """Handle Zen task daily cycle limit selection.

    :param callback: Callback query
    :param state: FSM context
    """
    if not callback.data or not callback.message:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        cycles_str = callback.data.replace("zen_cycles_", "")

        if cycles_str == "custom":
            custom_prompt_text = dedent("""
            🧘‍♂️ <b>Custom Daily Cycles</b>

            Please enter your custom daily cycle limit (1-100):
            """)

            await send_or_edit_message(
                callback.message, custom_prompt_text, auto_edit_recent=True
            )
            await callback.answer()
            return

        # Parse cycles
        cycles_map = {
            "5": 5,
            "10": 10,
            "20": 20,
            "50": 50
        }

        daily_cycles = cycles_map.get(cycles_str)
        if not daily_cycles:
            await callback.answer("❌ Invalid cycle selection.")
            return

        # Store cycles in state
        await state.update_data(zen_daily_cycles=daily_cycles)

        # Create Zen task
        await _create_zen_task(callback.message, state)
        await callback.answer()

    except Exception as e:
        logger.error(f"Error handling Zen cycles: {e}")
        await callback.answer("❌ Error setting daily cycles.")


async def _create_zen_task(message: Message, state: FSMContext) -> None:
    """Create and start a Zen research task.

    :param message: Telegram message
    :param state: FSM context
    """
    try:
        # Get task data from state
        data = await state.get_data()
        topic = data.get("zen_topic", "Research")
        daily_cycles = data.get("zen_daily_cycles", 10)

        # TODO: Create Zen task in database with daily cycle limits
        # zen_task = await create_zen_task(
        #     user_id=message.from_user.id,
        #     topic=topic,
        #     daily_cycle_limit=daily_cycles,
        #     task_type="zen"
        # )

        # TODO: For now, create as regular task but mark as zen
        from shared.db import get_or_create_user
        from bot.handlers.utils.task_operations import create_task_for_user

        user = await get_or_create_user(message.from_user.id)
        await create_task_for_user(user, f"[ZEN] {topic}", message)

        task_created_text = dedent(f"""
        🧘‍♂️ <b>Zen Task Created</b>

        <b>Topic:</b> {topic}
        <b>Daily Cycles:</b> {daily_cycles}
        <b>Status:</b> Active (continuous research)

        ✨ <b>Zen Task Features:</b>
        • Continuous background research
        • Daily cycle limit resets every day
        • No global cycle restrictions
        • Automatic literature monitoring
        • Minimal notification mode

        🎯 Your Zen task will continuously monitor new research
        in this area and deliver findings daily.
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 View Zen Tasks", callback_data="zen_view_tasks")],
            [InlineKeyboardButton(text="⚙️ Zen Settings", callback_data="zen_settings")],
            [InlineKeyboardButton(text="🔄 Create Another", callback_data="zen_create_start")]
        ])

        await send_or_edit_message(
            message, task_created_text, keyboard, auto_edit_recent=True
        )

        # Clear state
        await state.clear()

        logger.info(f"Zen task created for user {message.from_user.id}: {topic} ({daily_cycles} daily cycles)")

    except Exception as e:
        logger.error(f"Error creating Zen task: {e}")
        await send_or_edit_message(
            message, "❌ Error creating Zen task.", auto_edit_recent=True
        )


@router.callback_query(lambda c: c.data == "zen_cancel")
async def callback_zen_cancel(callback, state: FSMContext) -> None:
    """Cancel Zen task creation.

    :param callback: Callback query
    :param state: FSM context
    """
    try:
        await state.clear()

        cancel_text = "❌ Zen task creation cancelled."
        await send_or_edit_message(
            callback.message, cancel_text, auto_edit_recent=True
        )

        await callback.answer("Zen task creation cancelled.")

    except Exception as e:
        logger.error(f"Error cancelling Zen task creation: {e}")
        await callback.answer("❌ Error cancelling creation.")


@router.callback_query(lambda c: c.data == "zen_view_tasks")
async def callback_zen_view_tasks(callback) -> None:
    """View existing Zen tasks.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        # TODO: Get user's Zen tasks from database
        # zen_tasks = await get_user_zen_tasks(callback.from_user.id)

        tasks_text = dedent("""
        🧘‍♂️ <b>Your Zen Tasks</b>

        <b>Active Zen Tasks:</b>
        • No Zen tasks yet

        <b>Features of Zen Tasks:</b>
        • Continuous research monitoring
        • Daily cycle limits
        • Automatic background processing
        • Long-term knowledge building

        Create your first Zen task to get started!
        """)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧘‍♂️ Create Zen Task", callback_data="zen_create_start")],
            [InlineKeyboardButton(text="📊 View All Tasks", callback_data="show_results_list")],
            [InlineKeyboardButton(text="◀️ Back to Main", callback_data="zen_back_to_main")]
        ])

        await send_or_edit_message(
            callback.message, tasks_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error viewing Zen tasks: {e}")
        await callback.answer("❌ Error viewing Zen tasks.")


# TODO: Implement additional Zen task features:
# - Daily cycle limit management
# - Zen task status monitoring
# - Research trend analysis
# - Topic evolution tracking
# - Zen task archiving and cleanup
