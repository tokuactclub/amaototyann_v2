"""管理用ルーター."""

import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from amaototyann.config import get_settings
from amaototyann.server.lifespan import bot_store, group_store, sheets_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """ヘルスチェックエンドポイント."""
    discord_status = "not configured"
    settings = get_settings()
    if settings.discord_bot_token:
        try:
            from amaototyann.platforms.discord.bot import client as discord_client

            discord_status = "connected" if discord_client.is_ready() else "disconnected"
        except Exception:
            discord_status = "error"
    return {
        "status": "ok",
        "version": "3.0.0",
        "discord": discord_status,
    }


@router.get("/test")
async def test():
    """テストエンドポイント."""
    return PlainTextResponse("test success", status_code=200)


@router.get("/backupDatabase")
async def backup_database():
    """データベースを Google Sheets にバックアップするエンドポイント."""
    settings = get_settings()
    if settings.is_debug:
        return PlainTextResponse("Backup skipped in debug mode")

    if sheets_client is None:
        return PlainTextResponse("Sheets client not configured", status_code=503)

    results = []

    bot_data = await bot_store.dump_for_backup()
    bot_ok = await sheets_client.set_bot_info(bot_data)
    if bot_ok:
        await bot_store.mark_clean()
    results.append(f"bot={'success' if bot_ok else 'error'}")

    group_data = await group_store.dump_for_backup()
    group_ok = await sheets_client.set_group_info(group_data)
    if group_ok:
        await group_store.mark_clean()
    results.append(f"group={'success' if group_ok else 'error'}")

    message = " | ".join(results)
    code = 200 if bot_ok and group_ok else 500
    return PlainTextResponse(message, status_code=code)


@router.get("/")
async def root():
    """app.log を返すエンドポイント."""
    log_path = Path(__file__).parent.parent.parent / "logs" / "app.log"
    if log_path.exists():
        return PlainTextResponse(log_path.read_text(encoding="utf-8"))
    return PlainTextResponse("No logs available")
