"""
General settings handlers.

This module provides handlers for general user settings and preferences
including notifications, research preferences, and account management.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from textwrap import dedent

from shared.logging import get_logger
from bot.handlers.utils.messages import send_or_edit_message

router = Router(name="settings_general")
logger = get_logger(__name__)


@router.message(Command("settings"))
async def command_settings(message: Message) -> None:
    """Show main settings menu.

    :param message: Telegram message
    """
    if not message.from_user:
        await message.answer("❌ Error: could not determine user.")
        return

    try:
        settings_text = dedent("""
        ⚙️ <b>Settings</b>
        
        Configure your research assistant preferences:
        
        <b>📢 Notifications:</b>
        Control when and how you receive updates
        
        <b>🎯 Research Preferences:</b>
        Customize search and analysis behavior
        
        <b>🧘‍♂️ Zen Tasks:</b>
        Configure continuous research tasks
        
        <b>👤 Account:</b>
        Manage profile and privacy settings
        
        <b>📊 Data & Export:</b>
        Control data usage and export options
        """)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📢 Notifications", callback_data="settings_notifications"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🎯 Research Preferences",
                        callback_data="settings_research",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🧘‍♂️ Zen Tasks", callback_data="settings_zen"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👤 Account", callback_data="settings_account"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Data & Export", callback_data="settings_data"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Reset All", callback_data="settings_reset"
                    )
                ],
            ]
        )

        await send_or_edit_message(
            message,
            settings_text,
            keyboard,
        )

    except Exception as e:
        logger.error(f"Error showing settings: {e}")
        await message.answer("❌ Error showing settings.")


@router.callback_query(lambda c: c.data == "settings_notifications")
async def callback_settings_notifications(callback: CallbackQuery) -> None:
    """Handle notifications settings.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        # TODO: Get current notification settings from database
        notifications_text = dedent("""
        📢 <b>Notification Settings</b>
        
        <b>🔔 Current Settings:</b>
        • Important findings: ✅ Enabled (75%+ relevance)
        • New results: ✅ Enabled
        • Task completion: ✅ Enabled
        • System updates: ✅ Enabled
        
        <b>📱 Delivery Method:</b>
        • Personal chat: ✅ Active
        • Group chat: ❌ Not configured
        
        <b>⏰ Timing:</b>
        • Instant notifications: ✅ Enabled
        • Daily summaries: ❌ Disabled
        • Weekly reports: ❌ Disabled
        
        <b>🎯 Thresholds:</b>
        • Relevance threshold: 75%
        • Quality threshold: High
        • Importance level: Medium
        """)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔕 Toggle All", callback_data="notifications_toggle_all"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🎯 Set Threshold", callback_data="notifications_threshold"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👥 Group Chat", callback_data="notifications_group"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⏰ Schedule", callback_data="notifications_schedule"
                    )
                ],
                [InlineKeyboardButton(text="◀️ Back", callback_data="settings_back")],
            ]
        )

        await send_or_edit_message(
            callback.message, notifications_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing notification settings: {e}")
        await callback.answer("❌ Error showing notification settings.")


@router.callback_query(lambda c: c.data == "settings_research")
async def callback_settings_research(callback: CallbackQuery) -> None:
    """Handle research preferences settings.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        # Get current research preferences from database
        from shared.db import get_user_settings

        user_settings = None
        try:
            user_settings = await get_user_settings(callback.from_user.id)
        except Exception as e:
            logger.warning(f"Could not get user settings: {e}")

        # Use settings from database or defaults
        relevance_threshold = (
            getattr(user_settings, "instant_notification_threshold", 75.0)
            if user_settings
            else 75.0
        )

        research_text = dedent(f"""
        🎯 <b>Research Preferences</b>
        
        <b>🔍 Search Behavior:</b>
        • Default sources: All (arXiv, PubMed, Google Scholar)
        • Search depth: Medium (10-20 papers)
        • Relevance threshold: {relevance_threshold:.0f}%
        • Language: English only
        
        <b>📊 Analysis Style:</b>
        • Summary length: Medium
        • Technical detail: Balanced
        • Include methodology: ✅ Yes
        • Include limitations: ✅ Yes
        
        <b>🎨 Result Format:</b>
        • Sort by: Relevance
        • Group by: Topic
        • Show abstracts: ✅ Yes
        • Show citations: ✅ Yes
        
        <b>⚡ Performance:</b>
        • Concurrent searches: 3
        • Timeout: 30 seconds
        • Retry failed: ✅ Yes
        • Cache results: ✅ Yes
        """)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔍 Search Settings", callback_data="research_search"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Analysis Style", callback_data="research_analysis"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🎨 Format Options", callback_data="research_format"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⚡ Performance", callback_data="research_performance"
                    )
                ],
                [InlineKeyboardButton(text="◀️ Back", callback_data="settings_back")],
            ]
        )

        await send_or_edit_message(
            callback.message, research_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing research settings: {e}")
        await callback.answer("❌ Error showing research settings.")


@router.callback_query(lambda c: c.data == "settings_account")
async def callback_settings_account(callback: CallbackQuery) -> None:
    """Handle account settings.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        # TODO: Get current account info from database
        from shared.db import get_or_create_user

        user = await get_or_create_user(callback.from_user.id)

        account_text = dedent(f"""
        👤 <b>Account Settings</b>
        
        <b>📋 Profile:</b>
        • User ID: {user.id}
        • Username: @{callback.from_user.username or "Not set"}
        • Member since: {user.created_at.strftime("%B %Y") if hasattr(user, "created_at") and user.created_at else "Unknown"}
        • Last active: {user.updated_at.strftime("%Y-%m-%d %H:%M") if hasattr(user, "updated_at") and user.updated_at else "Recently"}
        
        <b>🔒 Privacy Settings:</b>
        • Data sharing: ❌ Disabled
        • Analytics: ✅ Anonymous only
        • Export available: ✅ Enabled
        • Account deletion: Available
        
        <b>🌐 Preferences:</b>
        • Language: English
        • Timezone: UTC+0 (System default)
        • Date format: DD.MM.YYYY
        • Theme: Default
        """)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📝 Edit Profile", callback_data="account_profile"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📈 Upgrade Plan", callback_data="account_upgrade"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔒 Privacy", callback_data="account_privacy"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📤 Export Data", callback_data="account_export"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🗑️ Delete Account", callback_data="account_delete"
                    )
                ],
                [InlineKeyboardButton(text="◀️ Back", callback_data="settings_back")],
            ]
        )

        await send_or_edit_message(
            callback.message, account_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error showing account settings: {e}")
        await callback.answer("❌ Error showing account settings.")


@router.callback_query(lambda c: c.data == "settings_back")
async def callback_settings_back(callback: CallbackQuery) -> None:
    """Return to main settings menu.

    :param callback: Callback query
    """
    if not callback.message:
        await callback.answer("❌ Error: message not accessible.")
        return

    try:
        settings_text = dedent("""
        ⚙️ <b>Settings</b>
        
        Configure your research assistant preferences:
        
        <b>📢 Notifications:</b>
        Control when and how you receive updates
        
        <b>🎯 Research Preferences:</b>
        Customize search and analysis behavior
        
        <b>🧘‍♂️ Zen Tasks:</b>
        Configure continuous research tasks
        
        <b>👤 Account:</b>
        Manage profile and privacy settings
        
        <b>📊 Data & Export:</b>
        Control data usage and export options
        """)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📢 Notifications", callback_data="settings_notifications"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🎯 Research Preferences",
                        callback_data="settings_research",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🧘‍♂️ Zen Tasks", callback_data="settings_zen"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👤 Account", callback_data="settings_account"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📊 Data & Export", callback_data="settings_data"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Reset All", callback_data="settings_reset"
                    )
                ],
            ]
        )

        await send_or_edit_message(
            callback.message, settings_text, keyboard, edit_mode=True
        )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error returning to settings: {e}")
        await callback.answer("❌ Error returning to settings.")


# TODO: Implement remaining settings handlers:
# - settings_zen - Zen tasks configuration
# - settings_data - Data management and export
# - settings_reset - Reset to defaults
# - account_profile - Profile editing
# - account_upgrade - Plan upgrade flow
# - account_privacy - Privacy settings
# - account_export - Data export
# - account_delete - Account deletion
# - research_* - Detailed research preferences
# - notifications_* - Detailed notification settings
