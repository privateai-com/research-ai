from aiogram import Router
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.filters import Command
from textwrap import dedent

from bot.handlers.utils.messages import send_or_edit_message

router = Router(name="settings")


async def show_simple_commands_help(message: Message) -> None:
    """Show simple commands help instead of complex settings.

    :param message: Telegram message to respond to
    """
    help_text = dedent("""
    ⚙️ <b>Simple Commands</b>
    
    <b>📢 Notifications:</b>
    /notifications_on - Get notified about important findings
    /notifications_off - Turn off notifications
    
    <b>👥 Group Chat:</b>
    /group_on - Share results in this group (use in group)
    /group_off - Back to personal notifications
    
    <b>📊 Account:</b>
    /account - View your plan and limits
    
    That's it! Simple and fast.
    """)

    await message.answer(help_text, parse_mode=ParseMode.HTML)


@router.message(Command("account"))
async def command_account(message: Message) -> None:
    """Show account information."""
    if not message.from_user:
        error_text = "❌ Error: could not determine user."
        await send_or_edit_message(message, error_text, auto_edit_recent=True)
        return

    # Import here to avoid circular imports
    from shared.db import get_or_create_user, get_user_tasks
    from bot.ui import get_plan_display_name

    try:
        user = await get_or_create_user(message.from_user.id)
        user_tasks = await get_user_tasks(user.id)

        # Count tasks by status
        active_tasks = len(
            [t for t in user_tasks if str(t.status) in ["queued", "processing"]]
        )
        completed_tasks = len([t for t in user_tasks if str(t.status) == "completed"])

        account_text = dedent(f"""
        📊 <b>Your Account</b>

        <b>Plan:</b> {get_plan_display_name(user.plan)}
        <b>Daily tasks:</b> {user.daily_tasks_created}/{user.daily_task_limit}
        <b>Active tasks:</b> {active_tasks}/{user.concurrent_task_limit}
        <b>Completed:</b> {completed_tasks}
        """)

        await send_or_edit_message(message, account_text, auto_edit_recent=True)

    except Exception:
        error_text = "❌ Error loading account information"
        await send_or_edit_message(message, error_text, auto_edit_recent=True)
