"""Telegram bot dispatcher and bootstrap.

Initializes routers, background tasks, and starts long-polling using aiogram.
Reads environment with ``dotenv`` and ensures database is initialized.
"""

import asyncio
import os
import sys
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared.db import init_db, list_completed_tasks_since
from shared.logging import get_logger
from bot.handlers import (
    get_general_router,
    get_settings_router,
    get_notifications_router,
    get_tasks_router,
    get_help_router,
    get_admin_analytics_router,
    get_admin_metrics_router,
    get_admin_settings_router,
    get_admin_users_router,
)
# Lazy imports will be done inside functions

logger = get_logger(__name__)


def create_env_template_if_missing():
    """Create a template .env file if it doesn't exist."""
    env_path = ".env"
    if os.path.exists(env_path):
        return

    template_content = """# Bot Configuration
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# LLM Configuration (at least one required for AI analysis)
OPENAI_API_KEY=your-openai-api-key
# OPENROUTER_API_KEY=your-openrouter-key

# Database Configuration
DATABASE_URL=sqlite:///./database.db

# Agent Configuration
AGENT_POLL_SECONDS=30
AGENT_DRY_RUN=false
AGENT_ID=main_agent

# Pipeline Configuration
PIPELINE_USE_AGENTS_STRATEGY=1
PIPELINE_USE_AGENTS_ANALYZE=0
"""

    try:
        with open(env_path, "w") as f:
            f.write(template_content)
        logger.info("Created template .env file. Please fill in your values.")
    except Exception as e:
        logger.warning(f"Could not create template .env file: {e}")


create_env_template_if_missing()
load_dotenv()


def check_required_env_vars():
    """Check for required environment variables and provide helpful error messages."""
    required_vars = ["TELEGRAM_BOT_TOKEN"]
    optional_vars = ["OPENAI_API_KEY", "OPENROUTER_API_KEY", "DATABASE_URL"]

    missing_required = []
    missing_optional = []

    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)

    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)

    if missing_required:
        error_msg = f"❌ Missing required environment variables: {', '.join(missing_required)}\n"
        error_msg += "Please create a .env file in the project root with the following variables:\n"
        error_msg += "\n".join(
            [f"  {var}=your_{var.lower()}_here" for var in missing_required]
        )
        if missing_optional:
            error_msg += (
                f"\n\n⚠️  Optional variables also missing: {', '.join(missing_optional)}"
            )
        raise ValueError(error_msg)

    if missing_optional:
        logger.warning(
            f"Optional environment variables missing: {', '.join(missing_optional)}"
        )
        logger.info("Bot will work with limited functionality (no AI analysis)")


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
check_required_env_vars()

# BOT_TOKEN is guaranteed to be not None after check_required_env_vars()
assert BOT_TOKEN is not None
bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()
dp.include_router(get_settings_router())
dp.include_router(get_notifications_router())
dp.include_router(get_tasks_router())
dp.include_router(get_help_router())
dp.include_router(get_general_router())

# Admin routers
dp.include_router(get_admin_analytics_router())
dp.include_router(get_admin_metrics_router())
dp.include_router(get_admin_settings_router())
dp.include_router(get_admin_users_router())

# TODO: Add zen routers when zen mode is fully implemented
# dp.include_router(get_zen_create_router())
# dp.include_router(get_zen_manage_router())
# dp.include_router(get_zen_view_router())

# TODO: Add advanced tasks routers when features are implemented
# dp.include_router(get_tasks_create_router())
# dp.include_router(get_tasks_manage_router())
# dp.include_router(get_tasks_view_router())


async def main() -> None:
    """Start the bot dispatcher and background workers.

    - Ensures database is initialized.
    - Launches background tasks for analyses and completed task delivery.
    - Starts long polling.

    :returns: ``None``.
    """
    logger.info("Starting Telegram bot...")

    try:
        await init_db()
        logger.info("Database initialized for bot")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Start background task to check for new analyses
    logger.info("Starting background analysis checker...")
    from bot.handlers.notifications import check_new_analyses

    asyncio.create_task(check_new_analyses(bot))
    logger.info("Background analysis checker started")

    logger.info("Telegram bot ready to work")

    # Start background task to process completed tasks (DB polling)
    async def check_completed_tasks():
        last_checked_id = 0
        while True:
            try:
                tasks = await list_completed_tasks_since(last_checked_id)
                for task in tasks:
                    from bot.handlers.notifications import process_completed_task

                    await process_completed_task(bot, task)
                    last_checked_id = max(last_checked_id, task.id)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error in completed tasks checker: {e}")
                await asyncio.sleep(5)

    asyncio.create_task(check_completed_tasks())

    # Start the bot
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
