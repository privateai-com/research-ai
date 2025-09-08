"""
Administrative user management handlers.

This module provides user management functionality for administrators
including user bans, role management, plan upgrades, and user monitoring.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from textwrap import dedent

from shared.db import get_all_users
from shared.logging import get_logger
from bot.handlers.utils.messages import send_or_edit_message
from bot.handlers.utils.admin import admin_required

router = Router(name="admin_users")
logger = get_logger(__name__)

# TODO: Implement user ban/unban system
# TODO: Implement user role management
# TODO: Implement user search functionality


@router.message(Command("admin_users"))
@admin_required
async def command_admin_users(message: Message) -> None:
    """Show user management overview for admins.

    :param message: Telegram message object
    """

    try:
        all_users = await get_all_users()

        # Calculate user statistics
        active_users = sum(1 for user in all_users if getattr(user, "is_active", True))
        banned_users = sum(1 for user in all_users if getattr(user, "is_banned", False))

        users_text = dedent(f"""
        👥 <b>User Management</b>
        
        <b>📊 Overview:</b>
        • Total users: {len(all_users)}
        • Active users: {active_users}
        • Banned users: {banned_users}
        • Registration rate: {len(all_users)} total registrations
        
        <b>Management Commands:</b>
        • <code>/admin_user [user_id]</code> - View user details (planned)
        • <code>/admin_ban [user_id]</code> - Ban user (planned)
        • <code>/admin_unban [user_id]</code> - Unban user (planned)
        • <code>/admin_user_stats</code> - Detailed user statistics
        
        <b>Quick Stats:</b>
        • New users this week: Data not available
        • Most active user: Data not available
        • Users with tasks: Data not available
        
        <i>Additional user management features are being implemented</i>
        """)

        await send_or_edit_message(message, users_text)

    except Exception as e:
        logger.error(f"Error showing users overview: {e}")
        await message.answer("❌ Error showing users overview.")


@router.message(Command("admin_user_details"))
@admin_required
async def command_admin_user_details(message: Message) -> None:
    """Show detailed information about all users for admins.

    :param message: Telegram message object
    """
    try:
        all_users = await get_all_users()

        if not all_users:
            await send_or_edit_message(message, "📊 No users found in the system.")
            return

        # Show first 10 users for demo (can be expanded)
        users_list = all_users[:10]

        details_text = "👥 <b>User Details (First 10)</b>\n\n"

        for i, user in enumerate(users_list, 1):
            user_status = (
                "🟢 Active" if getattr(user, "is_active", True) else "🔴 Inactive"
            )
            ban_status = " (🚫 Banned)" if getattr(user, "is_banned", False) else ""

            details_text += dedent(f"""
            <b>{i}. User {user.id}</b>
            • Status: {user_status}{ban_status}
            • Registration: {getattr(user, "created_at", "Unknown")}
            • Last activity: {getattr(user, "updated_at", "Unknown")}
            \n
            """)

        if len(all_users) > 10:
            details_text += f"\n<i>... and {len(all_users) - 10} more users</i>"

        await send_or_edit_message(message, details_text)

    except Exception as e:
        logger.error(f"Error showing user details: {e}")
        await message.answer("❌ Error showing user details.")


# TODO: Implement remaining admin user commands
# - /admin_user [user_id] - Specific user details with argument parsing
# - /admin_ban [user_id] - Ban user (requires ban system implementation)
# - /admin_unban [user_id] - Unban user (requires ban system implementation)
# - /admin_plan [user_id] [plan] - Change plan (requires plan system implementation)
# - /admin_search [query] - Search users (requires search implementation)
