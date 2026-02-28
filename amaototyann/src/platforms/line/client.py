"""LINE Bot コマンド処理モジュール."""
from typing import Optional
from linebot import LineBotApi
from linebot.models import TextSendMessage

from amaototyann.src import IS_DEBUG_MODE, logger, db_bot, db_group, messages
from amaototyann.src.core.commands import get_practice_events, get_reminder_events, finish_event
from amaototyann.src.platforms.line.bubble_msg import taskBubbleMsg


class LineCommands:
    """LINE Bot のコマンドを処理するクラス."""

    def __init__(self, channel_access_token: str, reply_token: Optional[str] = None,
                 target_group_id: Optional[str] = None, bot_id: Optional[int] = None):
        self.line_bot_api = LineBotApi(channel_access_token)
        self.reply_token = reply_token
        self.target_group_id = target_group_id
        self.bot_id = bot_id
        self.is_webhook_request = reply_token is not None

    async def process(self, cmd: str) -> bool:
        """コマンドを処理する."""
        commands = cmd.split()
        cmd_name = commands[0].lstrip("!")
        args = commands[1:] if len(commands) > 1 else []

        if cmd_name == "help":
            self._send_text_message(messages.HELP)
        elif cmd_name == "changeGroup":
            self._change_group()
        elif cmd_name == "reminder":
            await self._reminder(*args)
        elif cmd_name == "practice":
            await self._practice()
        elif cmd_name == "place":
            self._send_text_message(messages.PLACE)
        elif cmd_name == "handover":
            self._send_text_message(messages.HANDOVER)
        elif cmd_name == "hello":
            self._send_text_message("Hello, World!")
        elif cmd_name == "finish":
            await self._finish_event(args[0] if args else "")
        elif cmd_name == "youtube":
            self._send_text_message(messages.YOUTUBE)
        elif cmd_name == "instagram":
            self._send_text_message(messages.INSTAGRAM)
        elif cmd_name == "twitter":
            self._send_text_message(messages.TWITTER)
        elif cmd_name == "homepage":
            self._send_text_message(messages.HOMEPAGE)
        else:
            self._send_text_message(messages.CMD_ERROR)
            logger.error("command not found: %s", cmd_name)
            return False
        return True

    async def _practice(self):
        result = await get_practice_events()
        if result.error:
            logger.error("practice error: %s", result.error)
            return
        if result.text:
            self._send_text_message(result.text)
        elif result.is_empty and self.is_webhook_request:
            self._send_text_message(messages.NO_PRACTICE)

    async def _reminder(self, day_left: Optional[str] = None):
        result = await get_reminder_events(day_left)
        if result.error:
            logger.error("reminder error: %s", result.error)
            return
        if result.is_empty and self.is_webhook_request:
            self._send_text_message(messages.NONE_REMIND_TASK)
            return
        if result.events:
            msg_task = taskBubbleMsg()
            for event in result.events:
                msg_task.addReminder(
                    job=event["job"], person=event["person"],
                    deadline=event["date"], last_days=event["last_days"],
                    task=event["task"], memo=event["memo"], id=event["id"],
                )
            self._send_bubble_message(msg_task.getMessages())

    async def _finish_event(self, event_id: str):
        result = await finish_event(event_id)
        if result.text:
            self._send_text_message(result.text)
        elif result.error:
            self._send_text_message(result.error)

    def _change_group(self, group_id: Optional[str] = None, webhook_body: Optional[dict] = None):
        """リマインド対象グループを変更する."""
        if webhook_body:
            group_id = webhook_body['events'][0]['source']['groupId']
        if not group_id:
            return

        if not IS_DEBUG_MODE:
            group_name = self.line_bot_api.get_group_summary(group_id).group_name
        else:
            group_name = "test_group_name"

        if group_name is None:
            self._send_text_message(messages.CHANGE_GROUP_ERROR)
            return

        db_group.set_group_info(group_id, group_name)

        for row in db_bot.list_rows():
            if row["id"] == self.bot_id:
                db_bot.update_value(row["id"], "in_group", True)
            else:
                db_bot.update_value(row["id"], "in_group", False)

        self._send_text_message(messages.CHANGE_GROUP)

    def _send_text_message(self, text: str):
        if IS_DEBUG_MODE:
            logger.info("[DEBUG MODE] Message: %s", text)
        elif self.is_webhook_request:
            self.line_bot_api.reply_message(self.reply_token, TextSendMessage(text=text))
        else:
            self.line_bot_api.push_message(self.target_group_id, TextSendMessage(text=text))

    def _send_bubble_message(self, bubble):
        if IS_DEBUG_MODE:
            logger.info("[DEBUG MODE] Bubble Message: %s", bubble)
        elif self.is_webhook_request:
            self.line_bot_api.reply_message(self.reply_token, bubble)
        else:
            self.line_bot_api.push_message(self.target_group_id, bubble)
