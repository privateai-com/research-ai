#!/usr/bin/env python3
"""
Script to start only the Telegram bot
"""

import asyncio
from bot.main import main
from shared.db import init_db


async def startup():
    """Initialize database and start the bot."""
    await init_db()
    await main()


if __name__ == "__main__":
    asyncio.run(startup())
