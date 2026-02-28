"""LINE Webhook イベントハンドラ."""

import json
import logging

from fastapi import Request

from amaototyann.config import get_settings
from amaototyann.store.memory import BotStore, GroupStore
from amaototyann.platforms.line.security import verify_line_signature
from amaototyann.platforms.line.commands import LineCommandHandler
from amaototyann.platforms.line.converter import convert_jp_command
from amaototyann import messages

logger = logging.getLogger(__name__)


async def handle_line_webhook(
    request: Request,
    bot_id: int,
    bot_store: BotStore,
    group_store: GroupStore,
) -> dict:
    """LINE Webhook を処理する."""
    bot = await bot_store.get(bot_id)

    # 署名検証 (デバッグモードではスキップ可能)
    settings = get_settings()
    if settings.is_debug:
        body = await request.body()
    else:
        body = await verify_line_signature(request, bot.channel_secret)

    body_json = json.loads(body)
    events = body_json.get("events", [])

    for event in events:
        event_type = event.get("type")
        if event_type == "message" and event.get("message", {}).get("type") == "text":
            await _handle_message(event, bot_id, bot_store, group_store)
        elif event_type == "join":
            await _handle_join(event, bot_id, bot_store, group_store)
        elif event_type == "leave":
            await _handle_leave(bot_id, bot_store)
        else:
            logger.info("Unhandled LINE event type: %s", event_type)

    return {"status": "finish"}


async def _handle_message(
    event: dict,
    bot_id: int,
    bot_store: BotStore,
    group_store: GroupStore,
) -> None:
    """テキストメッセージを処理する."""
    bot = await bot_store.get(bot_id)
    raw_text: str = event["message"]["text"]
    text = convert_jp_command(raw_text).replace("！", "!")

    if not text.startswith("!"):
        return

    logger.info("Processing LINE command: %s", text)
    reply_token = event.get("replyToken", "")
    group_id = event.get("source", {}).get("groupId")

    handler = LineCommandHandler(
        channel_access_token=bot.channel_access_token,
        reply_token=reply_token,
        bot_id=bot_id,
        bot_store=bot_store,
        group_store=group_store,
        source_group_id=group_id,
    )
    await handler.process(text)


async def _handle_join(
    event: dict,
    bot_id: int,
    bot_store: BotStore,
    group_store: GroupStore,
) -> None:
    """グループ参加イベントを処理する."""
    logger.info("LINE join event for bot %d", bot_id)
    bot = await bot_store.get(bot_id)
    group_id = event["source"]["groupId"]
    reply_token = event.get("replyToken", "")

    settings = get_settings()
    if not settings.is_debug:
        from linebot.v3.messaging import AsyncApiClient, AsyncMessagingApi, Configuration
        from linebot.v3.messaging.models import ReplyMessageRequest, TextMessage

        config = Configuration(access_token=bot.channel_access_token)
        async with AsyncApiClient(config) as api_client:
            api = AsyncMessagingApi(api_client)
            count_resp = await api.get_group_members_count(group_id)
            quota_resp = await api.get_message_quota()
            remaining = quota_resp.value // count_resp
            await api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=messages.JOIN_LINE.format(bot.bot_name, remaining))],
                )
            )
    else:
        logger.info("[DEBUG] JOIN: %s", messages.JOIN_LINE.format(bot.bot_name, 200))

    target_group_id = await group_store.get_group_id()
    if group_id == target_group_id:
        await bot_store.update(bot_id, in_group=True)


async def _handle_leave(bot_id: int, bot_store: BotStore) -> None:
    """グループ退出イベントを処理する."""
    logger.info("LINE leave event for bot %d", bot_id)
    await bot_store.update(bot_id, in_group=False)
