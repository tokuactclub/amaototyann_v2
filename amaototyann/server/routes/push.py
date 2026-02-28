"""Push Message ルーター."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from amaototyann.config import get_settings
from amaototyann.platforms.line.commands import LineCommandHandler
from amaototyann.server.lifespan import bot_store, group_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/pushMessage")
async def push_message(request: Request):
    """外部からコマンドを実行するエンドポイント (LINE / Discord 両対応)."""
    request_json = await request.json()
    cmd = request_json.get("cmd")
    if cmd is None:
        logger.error("No cmd in request")
        return PlainTextResponse("error", status_code=400)

    platform = request_json.get("platform", "line")

    if platform == "discord":
        return await _handle_discord_push(cmd)
    else:
        return await _handle_line_push(cmd)


async def _handle_discord_push(cmd: str) -> PlainTextResponse:
    """Discord push message を処理する."""
    try:
        settings = get_settings()
        if not settings.discord_bot_token:
            return PlainTextResponse("Discord not configured", status_code=400)

        from amaototyann.platforms.discord.bot import client as discord_client
        from amaototyann.platforms.discord.commands import broadcast_practice, broadcast_reminder

        cmd_name = cmd.lstrip("!")
        if cmd_name == "practice":
            await broadcast_practice(discord_client)
        elif cmd_name == "reminder":
            await broadcast_reminder(discord_client)
        else:
            logger.error("Unknown Discord push command: %s", cmd_name)
            return PlainTextResponse("error", status_code=400)

        return PlainTextResponse("finish")
    except Exception:
        logger.exception("Discord push error")
        return PlainTextResponse("error", status_code=500)


async def _handle_line_push(cmd: str) -> PlainTextResponse:
    """LINE push message を処理する."""
    try:
        bots = await bot_store.list_all()
        active_bots = [b for b in bots if b.in_group]
        if not active_bots:
            return PlainTextResponse("error: no active bot", status_code=400)

        bot = active_bots[0]
        target_group_id = await group_store.get_group_id()

        handler = LineCommandHandler(
            channel_access_token=bot.channel_access_token,
            target_group_id=target_group_id,
        )
        result = await handler.process(cmd)
        if result:
            return PlainTextResponse("finish")
        return PlainTextResponse("error", status_code=400)
    except Exception:
        logger.exception("LINE push error")
        return PlainTextResponse("error", status_code=500)
