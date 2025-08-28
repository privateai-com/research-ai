"""
Task handlers for the research AI bot.

This module contains all handlers for task-related operations including
creation, display, and management of research tasks.
"""

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.handlers.utils.messages import (
    send_or_edit_message,
    safe_message_from_callback,
    generate_context_key,
)
from bot.handlers.utils.task_operations import (
    rate_limit_check,
    create_task_for_user,
    start_simple_task_creation,
    process_task_description,
    cancel_task_creation,
    TaskCreationStates,
)
from bot.handlers.utils.task_display import (
    show_detailed_status,
    show_task_selection,
    show_task_results,
    show_individual_result,
    show_additional_sources,
    show_task_details,
)
from bot.handlers.utils.ui import get_main_menu_keyboard
from bot.handlers.utils.validation import validate_user_access
from shared.db import get_or_create_user, get_user_tasks
from shared.database.operations.task import (
    cancel_user_task,
    pause_user_task,
    resume_user_task,
    cancel_all_user_tasks,
)
from shared.logging import get_logger

router = Router(name="tasks")
logger = get_logger(__name__)


# Menu handlers
@router.message(F.text == "🔬 New Task")
async def menu_new_task_handler(message: Message, state: FSMContext) -> None:
    """Handle new task button from main menu."""
    await start_simple_task_creation(message, state)


@router.message(F.text == "📊 Status")
async def menu_status_handler(message: Message) -> None:
    """Handle status button from main menu."""
    await command_status_handler(message)


@router.message(F.text == "📚 Results")
async def menu_history_handler(message: Message) -> None:
    """Handle results button from main menu."""
    await command_history_handler(message)


# Command handlers
@router.callback_query(F.data == "new_task_wizard")
async def callback_new_task_wizard(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle new task wizard callback."""
    message = safe_message_from_callback(callback.message)
    if not message:
        await callback.answer("❌ Error: message not accessible.")
        return

    await start_simple_task_creation(message, state)
    await callback.answer()


@router.message(Command("create"))
async def command_create_task(message: Message, state: FSMContext) -> None:
    """Create new research task with optional description."""
    args = (message.text or "").split()[1:]  # Remove command part

    if args:
        description = " ".join(args)
        if not message.from_user:
            await send_or_edit_message(message, "❌ Error: could not determine user.")
            return

        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        await create_task_for_user(user, description, message)
    else:
        await start_simple_task_creation(message, state)


@router.message(StateFilter(TaskCreationStates.waiting_for_description))
async def process_task_description_handler(message: Message, state: FSMContext) -> None:
    """Process task description input."""
    await process_task_description(message, state)


@router.message(Command("cancel"))
@router.message(F.text.lower().in_(["cancel", "отмена"]))
async def cancel_task_creation_handler(message: Message, state: FSMContext) -> None:
    """Cancel task creation."""
    await cancel_task_creation(message, state)


@router.message(Command("cancel_task"))
async def cancel_task_command_handler(message: Message) -> None:
    """Cancel a specific task by ID."""
    try:
        # Parse command arguments
        args = message.text.split()[1:] if message.text else []
        if not args:
            await send_or_edit_message(
                message,
                "❌ Please specify task ID to cancel.\n\nUsage: /cancel_task <task_id>",
            )
            return

        task_id_str = args[0]
        if not task_id_str.isdigit():
            await send_or_edit_message(
                message,
                "❌ Invalid task ID. Please provide a number.",
            )
            return

        task_id = int(task_id_str)
        user = await get_or_create_user(message.from_user.id)

        # Cancel the task
        success = await cancel_user_task(user.id, task_id)

        if success:
            await send_or_edit_message(
                message,
                f"✅ Task #{task_id} cancelled successfully!",
            )
        else:
            await send_or_edit_message(
                message,
                f"❌ Could not cancel task #{task_id}. It may not exist or already be completed.",
            )

    except Exception as e:
        logger.error(f"Error in cancel_task command: {e}")
        await send_or_edit_message(
            message,
            "❌ Error cancelling task.",
        )


@router.message(Command("pause_task"))
async def pause_task_command_handler(message: Message) -> None:
    """Pause a specific task by ID."""
    try:
        # Parse command arguments
        args = message.text.split()[1:] if message.text else []
        if not args:
            await send_or_edit_message(
                message,
                "❌ Please specify task ID to pause.\n\nUsage: /pause_task <task_id>",
            )
            return

        task_id_str = args[0]
        if not task_id_str.isdigit():
            await send_or_edit_message(
                message,
                "❌ Invalid task ID. Please provide a number.",
            )
            return

        task_id = int(task_id_str)
        user = await get_or_create_user(message.from_user.id)

        # Pause the task
        success = await pause_user_task(user.id, task_id)

        if success:
            await send_or_edit_message(
                message,
                f"⏸️ Task #{task_id} paused successfully!",
            )
        else:
            await send_or_edit_message(
                message,
                f"❌ Could not pause task #{task_id}. It may not be active or may not exist.",
            )

    except Exception as e:
        logger.error(f"Error in pause_task command: {e}")
        await send_or_edit_message(
            message,
            "❌ Error pausing task.",
        )


@router.message(Command("resume_task"))
async def resume_task_command_handler(message: Message) -> None:
    """Resume a paused task by ID."""
    try:
        # Parse command arguments
        args = message.text.split()[1:] if message.text else []
        if not args:
            await send_or_edit_message(
                message,
                "❌ Please specify task ID to resume.\n\nUsage: /resume_task <task_id>",
            )
            return

        task_id_str = args[0]
        if not task_id_str.isdigit():
            await send_or_edit_message(
                message,
                "❌ Invalid task ID. Please provide a number.",
            )
            return

        task_id = int(task_id_str)
        user = await get_or_create_user(message.from_user.id)

        # Resume the task
        success = await resume_user_task(user.id, task_id)

        if success:
            await send_or_edit_message(
                message,
                f"▶️ Task #{task_id} resumed successfully!",
            )
        else:
            await send_or_edit_message(
                message,
                f"❌ Could not resume task #{task_id}. It may not be paused or may not exist.",
            )

    except Exception as e:
        logger.error(f"Error in resume_task command: {e}")
        await send_or_edit_message(
            message,
            "❌ Error resuming task.",
        )


@router.message(Command("cancel_all"))
async def cancel_all_tasks_command_handler(message: Message) -> None:
    """Cancel all active tasks for the user."""
    try:
        user = await get_or_create_user(message.from_user.id)

        # Cancel all active tasks
        cancelled_count = await cancel_all_user_tasks(user.id)

        if cancelled_count > 0:
            await send_or_edit_message(
                message,
                f"✅ Successfully cancelled {cancelled_count} active task(s)!",
            )
        else:
            await send_or_edit_message(
                message,
                "ℹ️ No active tasks to cancel.",
            )

    except Exception as e:
        logger.error(f"Error in cancel_all command: {e}")
        await send_or_edit_message(
            message,
            "❌ Error cancelling tasks.",
        )


@router.message(Command("status"))
async def command_status_handler(message: Message) -> None:
    """Show interactive task status with detailed information."""
    try:
        is_valid, error_msg = await validate_user_access(message)
        if not is_valid:
            await send_or_edit_message(message, error_msg)
            return

        # Rate limiting check
        if not await rate_limit_check(message, "command"):
            return

        user = await get_or_create_user(message.from_user.id)  # type: ignore

        # Generate context key for status function
        context_key = generate_context_key("status", user.id)

        await show_detailed_status(
            message, user, edit_mode=False, function_context_key=context_key
        )

    except Exception as e:
        logger.error(f"Error in /status command: {e}")
        error_text = "❌ An error occurred while getting status."
        await send_or_edit_message(message, error_text)


@router.message(Command("history"))
async def command_history_handler(message: Message) -> None:
    """Show task selection for results."""
    try:
        is_valid, error_msg = await validate_user_access(message)
        if not is_valid:
            await send_or_edit_message(message, error_msg)
            return

        # Rate limiting check
        if not await rate_limit_check(message, "command"):
            return

        user = await get_or_create_user(message.from_user.id)  # type: ignore
        await show_task_selection(
            message, user, edit_mode=False
        )  # Allow auto-edit of recent message

    except Exception as e:
        logger.error(f"Error in /history command: {e}")
        error_text = "❌ An error occurred while getting results."
        await send_or_edit_message(message, error_text)


# Callback handlers for interactive features
@router.callback_query(F.data == "refresh_status")
async def handle_refresh_status(callback: CallbackQuery) -> None:
    """Handle status refresh button."""
    if not callback.from_user:
        await callback.answer("❌ Error: could not determine user.")
        return

    try:
        user = await get_or_create_user(callback.from_user.id)

        # Get the message for editing
        status_message = safe_message_from_callback(callback.message)
        if status_message:
            # Use function context for status updates
            context_key = generate_context_key("status", user.id)
            await show_detailed_status(
                status_message,
                user,
                navigation_context=True,
                function_context_key=context_key,
            )
            await callback.answer("✅ Status updated!")
        else:
            await callback.answer("❌ Error: message not accessible.")
    except Exception as e:
        logger.error(f"Error in refresh_status handler: {e}")
        await callback.answer("❌ Error updating status")


@router.callback_query(F.data == "show_results_list")
async def handle_show_results_list(callback: CallbackQuery) -> None:
    """Show task selection for viewing results."""
    if not callback.from_user:
        await callback.answer("❌ Error: could not determine user.")
        return

    try:
        user = await get_or_create_user(callback.from_user.id)
        message = safe_message_from_callback(callback.message)

        if message:
            await show_task_selection(message, user, 0, navigation_context=True)
            await callback.answer()
        else:
            await callback.answer("❌ Error: message not accessible.")
    except Exception as e:
        logger.error(f"Error in show_results_list handler: {e}")
        await callback.answer("❌ Error loading results list.")


@router.callback_query(F.data.startswith("task_details_"))
async def handle_task_details_callback(callback: CallbackQuery) -> None:
    """Show detailed information about a specific task."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract task ID with validation
        parts = callback.data.split("_")
        if len(parts) < 3 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid task data.")
            return

        task_id = int(parts[-1])
        if task_id <= 0:
            await callback.answer("❌ Error: invalid task ID.")
            return

        user = await get_or_create_user(callback.from_user.id)
        message = safe_message_from_callback(callback.message)

        if not message:
            await callback.answer("❌ Error: message not accessible.")
            return

        await show_task_details(message, user, task_id)
        await callback.answer()

    except ValueError as e:
        logger.error(f"Error parsing task ID: {e}")
        await callback.answer("❌ Error: invalid task ID.")
    except Exception as e:
        logger.error(f"Error in task_details handler: {e}")
        await callback.answer("❌ Error loading task details.")


@router.callback_query(F.data.startswith("view_task_results_"))
async def handle_view_task_results(callback: CallbackQuery) -> None:
    """View results for a specific task from task details."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract task ID with validation
        parts = callback.data.split("_")
        if len(parts) < 4 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid task data.")
            return

        task_id = int(parts[-1])
        if task_id <= 0:
            await callback.answer("❌ Error: invalid task ID.")
            return

        user = await get_or_create_user(callback.from_user.id)
        message = safe_message_from_callback(callback.message)

        if not message:
            await callback.answer("❌ Error: message not accessible.")
            return

        # Check if task belongs to user
        user_tasks = await get_user_tasks(user.id)
        if not any(t.id == task_id for t in user_tasks):
            await callback.answer("❌ Task not found.")
            return

        # Show task results
        await show_task_results(message, user, task_id, 0, navigation_context=True)
        await callback.answer()

    except ValueError as e:
        logger.error(f"Error parsing task ID for results: {e}")
        await callback.answer("❌ Error: invalid task ID.")
    except Exception as e:
        logger.error(f"Error in view_task_results handler: {e}")
        await callback.answer("❌ Error loading task results.")


@router.callback_query(F.data == "back_to_tasks")
async def handle_back_to_tasks(callback: CallbackQuery) -> None:
    """Go back to task selection."""
    if not callback.from_user:
        await callback.answer("❌ Error: could not determine user.")
        return

    user = await get_or_create_user(callback.from_user.id)
    message = safe_message_from_callback(callback.message)

    if message:
        await show_task_selection(message, user, 0, navigation_context=True)

    await callback.answer()


@router.callback_query(F.data == "back_to_status")
async def handle_back_to_status(callback: CallbackQuery) -> None:
    """Go back to status view."""
    if not callback.from_user:
        await callback.answer("❌ Error: could not determine user.")
        return

    user = await get_or_create_user(callback.from_user.id)
    message = safe_message_from_callback(callback.message)

    if message:
        await show_detailed_status(message, user, navigation_context=True)

    await callback.answer()


@router.callback_query(F.data == "back_to_results")
async def handle_back_to_results(callback: CallbackQuery) -> None:
    """Go back to results list."""
    if not callback.from_user:
        await callback.answer("❌ Error: could not determine user.")
        return

    user = await get_or_create_user(callback.from_user.id)
    message = safe_message_from_callback(callback.message)

    if message:
        await show_task_selection(message, user, 0, navigation_context=True)

    await callback.answer()


# Pagination handlers
@router.callback_query(F.data.startswith("task_pagination_page_"))
async def handle_task_pagination(callback: CallbackQuery) -> None:
    """Handle task pagination."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract page number with validation
        parts = callback.data.split("_")
        if len(parts) < 4 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid pagination data.")
            return

        page = int(parts[-1])
        if page < 0:
            await callback.answer("❌ Error: invalid page number.")
            return

        user = await get_or_create_user(callback.from_user.id)
        message = safe_message_from_callback(callback.message)

        if message:
            await show_task_selection(message, user, page, edit_mode=True)
            await callback.answer()
        else:
            await callback.answer("❌ Error: message not accessible.")

    except ValueError as e:
        logger.error(f"Error parsing pagination page: {e}")
        await callback.answer("❌ Error: invalid page number.")
    except Exception as e:
        logger.error(f"Error in task pagination handler: {e}")
        await callback.answer("❌ Error loading page.")


@router.callback_query(F.data.startswith("task_pagination_item_"))
async def handle_task_selection_callback(callback: CallbackQuery) -> None:
    """Handle task selection for viewing results."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract task index with validation
        parts = callback.data.split("_")
        if len(parts) < 4 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid task data.")
            return

        task_idx = int(parts[-1])
        if task_idx < 0:
            await callback.answer("❌ Error: invalid task index.")
            return

        user = await get_or_create_user(callback.from_user.id)
        user_tasks = await get_user_tasks(user.id)

        if task_idx >= len(user_tasks):
            await callback.answer("❌ Task not found.")
            return

        task = user_tasks[task_idx]
        message = safe_message_from_callback(callback.message)

        if message:
            await show_task_results(message, user, task.id, navigation_context=True)
            await callback.answer()
        else:
            await callback.answer("❌ Error: message not accessible.")

    except ValueError as e:
        logger.error(f"Error parsing task index: {e}")
        await callback.answer("❌ Error: invalid task index.")
    except Exception as e:
        logger.error(f"Error in task selection handler: {e}")
        await callback.answer("❌ Error loading task results.")


@router.callback_query(F.data == "task_pagination_refresh")
async def handle_task_refresh(callback: CallbackQuery) -> None:
    """Handle task list refresh."""
    if not callback.from_user:
        await callback.answer("❌ Error: could not determine user.")
        return

    user = await get_or_create_user(callback.from_user.id)
    message = safe_message_from_callback(callback.message)

    if message:
        await show_task_selection(message, user, 0, navigation_context=True)

    await callback.answer("✅ Task list refreshed!")


# Results pagination handlers
@router.callback_query(F.data.startswith("results_pagination_page_"))
async def handle_results_pagination(callback: CallbackQuery) -> None:
    """Handle results pagination."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract page number with validation
        parts = callback.data.split("_")
        if len(parts) < 4 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid pagination data.")
            return

        page = int(parts[-1])
        if page < 0:
            await callback.answer("❌ Error: invalid page number.")
            return

        user = await get_or_create_user(callback.from_user.id)
        message = safe_message_from_callback(callback.message)

        if message:
            # Extract task_id from callback data or use a default approach
            # For now, we'll show all results since task filtering isn't fully implemented
            await show_task_results(message, user, 0, page, navigation_context=True)
            await callback.answer()
        else:
            await callback.answer("❌ Error: message not accessible.")

    except ValueError as e:
        logger.error(f"Error parsing results pagination page: {e}")
        await callback.answer("❌ Error: invalid page number.")
    except Exception as e:
        logger.error(f"Error in results pagination handler: {e}")
        await callback.answer("❌ Error loading page.")


@router.callback_query(F.data.startswith("results_pagination_item_"))
async def handle_result_selection(callback: CallbackQuery) -> None:
    """Handle result selection."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract result index with validation
        parts = callback.data.split("_")
        if len(parts) < 4 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid result data.")
            return

        result_idx = int(parts[-1])
        if result_idx < 0:
            await callback.answer("❌ Error: invalid result index.")
            return

        user = await get_or_create_user(callback.from_user.id)

        # Get all analyses for user to find the specific one
        all_analyses = []

        # Try old system first (ResearchTopic) - this is what agent currently uses
        try:
            from shared.db import list_recent_analyses_for_user

            old_analyses = await list_recent_analyses_for_user(user.id, limit=100)
            all_analyses.extend(old_analyses)
        except Exception as e:
            logger.warning(f"Error loading old system analyses: {e}")

        # If no results in old system, try new system (UserTask + Finding)
        if not all_analyses:
            try:
                user_tasks = await get_user_tasks(user.id)

                for task in user_tasks:
                    try:
                        # Import here to avoid circular imports
                        from shared.db import get_user_task_results

                        task_results = await get_user_task_results(task.id)
                        all_analyses.extend(task_results)
                    except Exception as e:
                        logger.warning(
                            f"Error loading task results for task {task.id}: {e}"
                        )
                        continue
            except Exception as e:
                logger.warning(f"Error loading user tasks: {e}")

        if result_idx >= len(all_analyses):
            await callback.answer("❌ Result not found.")
            return

        analysis, paper = all_analyses[result_idx]

        # Create detailed result display
        message = safe_message_from_callback(callback.message)
        if message:
            await show_individual_result(message, analysis, paper, result_idx)
            await callback.answer()
        else:
            await callback.answer("❌ Error: message not accessible.")

    except ValueError as e:
        logger.error(f"Error parsing result index: {e}")
        await callback.answer("❌ Error: invalid result index.")
    except Exception as e:
        logger.error(f"Error in result selection handler: {e}")
        await callback.answer("❌ Error loading result.")


@router.callback_query(F.data == "results_pagination_refresh")
async def handle_results_refresh(callback: CallbackQuery) -> None:
    """Handle results refresh."""
    if not callback.from_user:
        await callback.answer("❌ Error: could not determine user.")
        return

    user = await get_or_create_user(callback.from_user.id)
    message = safe_message_from_callback(callback.message)

    if message:
        await show_task_results(message, user, 0, 0, navigation_context=True)

    await callback.answer("✅ Results refreshed!")


# Result interaction handlers
@router.callback_query(F.data.startswith("show_result_"))
async def handle_show_individual_result_callback(callback: CallbackQuery) -> None:
    """Show individual result with AI summary and source links."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract result index with validation
        parts = callback.data.split("_")
        if len(parts) < 3 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid result data.")
            return

        result_idx = int(parts[-1])
        if result_idx < 0:
            await callback.answer("❌ Error: invalid result index.")
            return

        user = await get_or_create_user(callback.from_user.id)

        # Get all analyses for user to find the specific one
        all_analyses = []

        # Try old system first (ResearchTopic) - this is what agent currently uses
        try:
            from shared.db import list_recent_analyses_for_user

            old_analyses = await list_recent_analyses_for_user(user.id, limit=100)
            all_analyses.extend(old_analyses)
        except Exception as e:
            logger.warning(f"Error loading old system analyses: {e}")

        # If no results in old system, try new system (UserTask + Finding)
        if not all_analyses:
            try:
                user_tasks = await get_user_tasks(user.id)

                for task in user_tasks:
                    try:
                        # Import here to avoid circular imports
                        from shared.db import get_user_task_results

                        task_results = await get_user_task_results(task.id)
                        all_analyses.extend(task_results)
                    except Exception as e:
                        logger.warning(
                            f"Error loading task results for task {task.id}: {e}"
                        )
                        continue
            except Exception as e:
                logger.warning(f"Error loading user tasks: {e}")

        if result_idx >= len(all_analyses):
            await callback.answer("❌ Result not found.")
            return

        analysis, paper = all_analyses[result_idx]

        # Create detailed result display (new notification format)
        message = safe_message_from_callback(callback.message)
        if message:
            await show_individual_result(message, analysis, paper, result_idx)
            await callback.answer()
        else:
            await callback.answer("❌ Error: message not accessible.")

    except ValueError as e:
        logger.error(f"Error parsing result index: {e}")
        await callback.answer("❌ Error: invalid result index.")
    except Exception as e:
        logger.error(f"Error in show result handler: {e}")
        await callback.answer("❌ Error loading result.")


@router.callback_query(F.data.startswith("save_result_"))
async def handle_save_result(callback: CallbackQuery) -> None:
    """Handle save result button."""
    await callback.answer("💾 Result saved to your favorites! (Feature coming soon)")


@router.callback_query(F.data.startswith("more_sources_"))
async def handle_more_sources_callback(callback: CallbackQuery) -> None:
    """Handle more sources button."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract result index with validation
        parts = callback.data.split("_")
        if len(parts) < 3 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid result data.")
            return

        result_idx = int(parts[-1])
        if result_idx < 0:
            await callback.answer("❌ Error: invalid result index.")
            return

        user = await get_or_create_user(callback.from_user.id)

        # Get the specific result to show additional sources
        all_analyses = []

        # Try old system first (ResearchTopic) - this is what agent currently uses
        try:
            from shared.db import list_recent_analyses_for_user

            old_analyses = await list_recent_analyses_for_user(user.id, limit=100)
            all_analyses.extend(old_analyses)
        except Exception as e:
            logger.warning(f"Error loading old system analyses: {e}")

        # If no results in old system, try new system (UserTask + Finding)
        if not all_analyses:
            try:
                user_tasks = await get_user_tasks(user.id)

                for task in user_tasks:
                    try:
                        # Import here to avoid circular imports
                        from shared.db import get_user_task_results

                        task_results = await get_user_task_results(task.id)
                        all_analyses.extend(task_results)
                    except Exception as e:
                        logger.warning(
                            f"Error loading task results for task {task.id}: {e}"
                        )
                        continue
            except Exception as e:
                logger.warning(f"Error loading user tasks: {e}")

        if result_idx >= len(all_analyses):
            await callback.answer("❌ Result not found.")
            return

        analysis, paper = all_analyses[result_idx]

        # Show additional source options
        message = safe_message_from_callback(callback.message)
        if message:
            await show_additional_sources(message, paper, result_idx)
            await callback.answer()
        else:
            await callback.answer("❌ Error: message not accessible.")

    except ValueError as e:
        logger.error(f"Error parsing result index for sources: {e}")
        await callback.answer("❌ Error: invalid result index.")
    except Exception as e:
        logger.error(f"Error loading sources: {e}")
        await callback.answer("❌ Error loading sources.")


# Task management handlers
@router.callback_query(F.data.startswith("cancel_task_"))
async def handle_cancel_task(callback: CallbackQuery) -> None:
    """Handle task cancellation."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract task ID
        parts = callback.data.split("_")
        if len(parts) < 3 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid task data.")
            return

        task_id = int(parts[-1])
        logger.info(f"User {callback.from_user.id} attempting to cancel task {task_id}")

        user = await get_or_create_user(callback.from_user.id)
        logger.info(f"User {user.id} loaded for task cancellation")

        # Cancel the task using async version
        success = await cancel_user_task(user.id, task_id)
        logger.info(f"Task cancellation result for task {task_id}: {success}")

        if success:
            await callback.answer("✅ Task cancelled successfully!")

            # Simple response without complex UI updates to avoid event loop issues
            await callback.message.answer(
                f"✅ Task #{task_id} has been cancelled successfully!\n\n"
                "Use /status to see updated task list.",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            await callback.answer("❌ Could not cancel task.")

    except Exception as e:
        logger.error(f"Error cancelling task: {e}", exc_info=True)
        await callback.answer("❌ Error cancelling task.")


@router.callback_query(F.data.startswith("pause_task_"))
async def handle_pause_task(callback: CallbackQuery) -> None:
    """Handle task pausing."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract task ID
        parts = callback.data.split("_")
        if len(parts) < 3 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid task data.")
            return

        task_id = int(parts[-1])
        logger.info(f"User {callback.from_user.id} attempting to pause task {task_id}")

        user = await get_or_create_user(callback.from_user.id)
        logger.info(f"User {user.id} loaded for task pausing")

        # Pause the task using async version
        success = await pause_user_task(user.id, task_id)
        logger.info(f"Task pause result for task {task_id}: {success}")

        if success:
            await callback.answer("⏸️ Task paused successfully!")

            # Simple response without complex UI updates to avoid event loop issues
            await callback.message.answer(
                f"⏸️ Task #{task_id} has been paused successfully!\n\n"
                "Use /status to see updated task list.\n"
                "Use /resume_task {task_id} to resume the task.",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            await callback.answer("❌ Could not pause task.")

    except Exception as e:
        logger.error(f"Error pausing task: {e}", exc_info=True)
        await callback.answer("❌ Error pausing task.")


@router.callback_query(F.data.startswith("resume_task_"))
async def handle_resume_task(callback: CallbackQuery) -> None:
    """Handle task resumption."""
    if not callback.data or not callback.from_user:
        await callback.answer("❌ Error: invalid request.")
        return

    try:
        # Extract task ID
        parts = callback.data.split("_")
        if len(parts) < 3 or not parts[-1].isdigit():
            await callback.answer("❌ Error: invalid task data.")
            return

        task_id = int(parts[-1])
        logger.info(f"User {callback.from_user.id} attempting to resume task {task_id}")

        user = await get_or_create_user(callback.from_user.id)
        logger.info(f"User {user.id} loaded for task resumption")

        # Resume the task using async version
        success = await resume_user_task(user.id, task_id)
        logger.info(f"Task resume result for task {task_id}: {success}")

        if success:
            await callback.answer("▶️ Task resumed successfully!")

            # Simple response without complex UI updates to avoid event loop issues
            await callback.message.answer(
                f"▶️ Task #{task_id} has been resumed successfully!\n\n"
                "Use /status to see updated task list.",
                reply_markup=get_main_menu_keyboard(),
            )
        else:
            await callback.answer("❌ Could not resume task.")

    except Exception as e:
        logger.error(f"Error resuming task: {e}", exc_info=True)
        await callback.answer("❌ Error resuming task.")


# Click tracking for analytics
@router.callback_query(F.data.startswith("track_click_"))
async def handle_click_tracking(callback: CallbackQuery) -> None:
    """Track clicks on source buttons for analytics."""
    if not callback.data:
        return

    # Parse click data
    parts = callback.data.split("_")
    if len(parts) >= 4:
        source_type = parts[2]  # paper, arxiv, doi, pubmed, scholar
        result_idx = parts[3]

        # Log the click for analytics
        logger.info(
            f"User {callback.from_user.id if callback.from_user else 'unknown'} "
            f"clicked {source_type} link for result {result_idx}"
        )

    await callback.answer()
