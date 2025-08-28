#!/usr/bin/env python3
"""
Script to start only the AI agent
"""

import asyncio
from agent.manager import main
from shared.db import init_db


async def startup():
    """Initialize database and start the agent."""
    await init_db()
    await main()


if __name__ == "__main__":
    asyncio.run(startup())
