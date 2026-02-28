"""LINE Webhook イベントハンドラ."""
import time
from typing import Optional

from linebot import LineBotApi
from linebot.models import TextSendMessage

from amaototyann.src import IS_DEBUG_MODE, logger, db_bot, db_group
from amaototyann.src import messages
from amaototyann.src.platforms.line.client import LineCommands
from amaototyann.src.platforms.line.converter import convert_jp_command


async def react_message_webhook(request_json: dict, bot_id: int, event_index: int):
    """テキストメッセージ Webhook を処理する."""
    logger.info("got react message webhook")
    bot = db_bot.get_row(bot_id)
    channel_access_token = bot["channel_access_token"]

    message: str = request_json['events'][event_index]['message']['text']
    message = convert_jp_command(message)

    # 全角の！を半角に変換
    message = message.replace("！", "!")

    if not message.startswith("!"):
        return

    logger.info("start command process")
    reply_token = request_json['events'][event_index]['replyToken']
    cmd = LineCommands(
        channel_access_token=channel_access_token,
        reply_token=reply_token,
        bot_id=bot_id,
    )
    await cmd.process(message)


async def react_join_webhook(request_json: dict, bot_id: int, event_index: int):
    """グループ参加 Webhook を処理する."""
    logger.info("got join webhook")
    bot = db_bot.get_row(bot_id)
    channel_access_token = bot["channel_access_token"]
    bot_name = bot["bot_name"]

    event = request_json['events'][event_index]
    group_id = event['source']['groupId']

    if IS_DEBUG_MODE:
        remaining_message_count = 200
        logger.info(messages.JOIN_LINE.format(bot_name, remaining_message_count))
    else:
        line_bot_api = LineBotApi(channel_access_token)
        group_member_count = line_bot_api.get_group_members_count(group_id)
        remaining_message_count = line_bot_api.get_message_quota().value
        remaining_message_count = remaining_message_count // group_member_count
        line_bot_api.reply_message(
            event['replyToken'],
            TextSendMessage(text=messages.JOIN_LINE.format(bot_name, remaining_message_count))
        )

    target_group_id = db_group.group_id()
    if group_id == target_group_id:
        db_bot.update_value(bot_id, "in_group", True)


async def react_leave_webhook(request_json: dict, bot_id: int, event_index: int):
    """グループ退出 Webhook を処理する."""
    logger.info("got left webhook")
    db_bot.update_value(bot_id, "in_group", False)
