"""アプリケーションのライフサイクル管理."""

import asyncio
import logging
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI

from amaototyann.config import get_settings
from amaototyann.gas.client import (
    backup_bot_info,
    backup_group_info,
    close_session,
    fetch_bot_info,
    fetch_group_info,
)
from amaototyann.logging_config import configure_logging
from amaototyann.store.memory import BotStore, GroupStore

logger = logging.getLogger(__name__)

# グローバルストアインスタンス
bot_store = BotStore()
group_store = GroupStore()


async def _backup_loop() -> None:
    """定期的に DB を GAS にバックアップするループ."""
    settings = get_settings()
    while True:
        try:
            if settings.is_debug:
                logger.debug("Skipping backup in debug mode")
            else:
                if bot_store.is_dirty:
                    data = await bot_store.dump_for_backup()
                    if await backup_bot_info(data):
                        await bot_store.mark_clean()

                if group_store.is_dirty:
                    data = await group_store.dump_for_backup()
                    if await backup_group_info(data):
                        await group_store.mark_clean()
        except Exception as e:
            logger.error("Backup error: %s", e)
        await asyncio.sleep(60 * 3)


async def _keep_alive_loop() -> None:
    """Ping the health endpoint to keep Render free tier from sleeping."""
    settings = get_settings()
    if not settings.server_url or settings.is_debug:
        logger.debug("Keep-alive loop disabled")
        return

    health_url = f"{settings.server_url}/health"
    timeout = aiohttp.ClientTimeout(total=10)
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                get_request = session.get(health_url, timeout=timeout)
                async with get_request as response:
                    if response.status == 200:
                        logger.debug("Keep-alive ping successful")
                    else:
                        logger.warning("Keep-alive ping returned status %s", response.status)
        except Exception as e:
            logger.error("Keep-alive ping error: %s", e)
        await asyncio.sleep(60 * 5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理."""
    # 1. ログ設定
    configure_logging()
    logger.info("Starting amaototyann v3...")

    # 2. 設定読み込み
    settings = get_settings()

    # 3. GAS から初期データ取得
    bots = await fetch_bot_info()
    if bots:
        await bot_store.load(bots)
    else:
        logger.warning("No bot info loaded from GAS")

    group = await fetch_group_info()
    if group:
        await group_store.load(group)
    else:
        logger.warning("No group info loaded from GAS")

    # 4. Discord client の起動 (オプション)
    tasks: list[asyncio.Task] = []
    if settings.discord_bot_token:
        from amaototyann.platforms.discord.bot import client as discord_client
        from amaototyann.platforms.discord.bot import setup_events

        setup_events()
        task = asyncio.create_task(discord_client.start(settings.discord_bot_token))
        tasks.append(task)
        logger.info("Discord client starting...")
    else:
        logger.warning("DISCORD_BOT_TOKEN not set. Discord bot will not start.")

    # 5. バックアップループの起動
    backup_task = asyncio.create_task(_backup_loop())
    tasks.append(backup_task)
    logger.info("Backup loop started.")

    # 6. Keep-alive ループの起動 (Render free tier でのスリープを防止)
    keep_alive_task = asyncio.create_task(_keep_alive_loop())
    tasks.append(keep_alive_task)
    logger.info("Keep-alive loop started.")

    yield

    # Shutdown
    if settings.discord_bot_token:
        from amaototyann.platforms.discord.bot import client as discord_client

        if not discord_client.is_closed():
            await discord_client.close()
            logger.info("Discord client closed.")

    for task in tasks:
        task.cancel()

    await close_session()
    logger.info("amaototyann v3 shutdown complete.")
