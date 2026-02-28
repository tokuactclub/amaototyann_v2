"""アプリケーションのライフサイクル管理."""

import asyncio
import logging
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI

from amaototyann.config import get_settings
from amaototyann.logging_config import configure_logging
from amaototyann.models.bot import BotInfo, GroupInfo
from amaototyann.sheets.client import SheetsClient
from amaototyann.store.memory import BotStore, GroupStore

logger = logging.getLogger(__name__)


async def _backup_loop(app: FastAPI) -> None:
    """定期的にストアデータを Google Sheets にバックアップするループ."""
    if app.state.sheets_client is None:
        return

    settings = get_settings()
    while True:
        try:
            if settings.is_debug:
                logger.debug("Skipping backup in debug mode")
            else:
                if app.state.bot_store.is_dirty:
                    data = await app.state.bot_store.dump_for_backup()
                    if await app.state.sheets_client.set_bot_info(data):
                        await app.state.bot_store.mark_clean()

                if app.state.group_store.is_dirty:
                    data = await app.state.group_store.dump_for_backup()
                    if await app.state.sheets_client.set_group_info(data):
                        await app.state.group_store.mark_clean()
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
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(health_url, timeout=timeout) as response:
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

    # 3. app.state 初期化
    app.state.bot_store = BotStore()
    app.state.group_store = GroupStore()
    app.state.sheets_client = None

    # 4. SheetsClient 初期化 & 初期データ取得
    if settings.google_service_account_json and settings.google_spreadsheet_id:
        app.state.sheets_client = await asyncio.get_running_loop().run_in_executor(
            None,
            SheetsClient,
            settings.google_service_account_json,
            settings.google_spreadsheet_id,
        )
        logger.info("SheetsClient initialized")
    else:
        logger.warning("Google Sheets credentials not configured")

    if app.state.sheets_client:
        bot_data = await app.state.sheets_client.get_bot_info()
        if bot_data:
            bots = [
                BotInfo(
                    id=int(row[0]),
                    bot_name=row[1],
                    channel_access_token=row[2],
                    channel_secret=row[3],
                    gpt_webhook_url=row[4] or None,
                    in_group=row[5].upper() == "TRUE",
                )
                for row in bot_data
            ]
            await app.state.bot_store.load(bots)
        else:
            logger.warning("No bot info loaded from Sheets")

        group_data = await app.state.sheets_client.get_group_info()
        if group_data:
            group = GroupInfo(id=group_data["id"], group_name=group_data["groupName"])
            await app.state.group_store.load(group)
        else:
            logger.warning("No group info loaded from Sheets")

    # 4. Discord client の起動 (オプション)
    tasks: list[asyncio.Task] = []
    if settings.discord_bot_token:
        from amaototyann.platforms.discord.bot import client as discord_client
        from amaototyann.platforms.discord.bot import setup_events

        setup_events(app)
        task = asyncio.create_task(discord_client.start(settings.discord_bot_token))
        tasks.append(task)
        logger.info("Discord client starting...")
    else:
        logger.warning("DISCORD_BOT_TOKEN not set. Discord bot will not start.")

    # 5. バックアップループの起動
    backup_task = asyncio.create_task(_backup_loop(app))
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

    logger.info("amaototyann v3 shutdown complete.")
