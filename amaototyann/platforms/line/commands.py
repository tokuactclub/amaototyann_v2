"""LINE Bot コマンド処理."""

import logging

from amaototyann.config import get_settings
from amaototyann.core.commands import get_practice_events, get_reminder_events, finish_event
from amaototyann.store.memory import BotStore, GroupStore
from amaototyann.platforms.line.flex_messages import ReminderFlexBuilder
from amaototyann import messages

logger = logging.getLogger(__name__)


class LineCommandHandler:
    """LINE Bot のコマンドを処理するクラス."""

    def __init__(
        self,
        *,
        channel_access_token: str,
        reply_token: str | None = None,
        target_group_id: str | None = None,
        bot_id: int | None = None,
        bot_store: BotStore | None = None,
        group_store: GroupStore | None = None,
        source_group_id: str | None = None,
    ) -> None:
        self._token = channel_access_token
        self._reply_token = reply_token
        self._target_group_id = target_group_id
        self._bot_id = bot_id
        self._bot_store = bot_store
        self._group_store = group_store
        self._source_group_id = source_group_id
        self._is_webhook = reply_token is not None

    async def process(self, cmd: str) -> bool:
        """コマンドを処理する."""
        parts = cmd.split()
        cmd_name = parts[0].lstrip("!")
        args = parts[1:] if len(parts) > 1 else []

        handlers: dict[str, object] = {
            "help": lambda: self._send_text(messages.HELP),
            "changeGroup": lambda: self._change_group(),
            "reminder": lambda: self._reminder(*args),
            "practice": lambda: self._practice(),
            "place": lambda: self._send_text(messages.PLACE),
            "handover": lambda: self._send_text(messages.HANDOVER),
            "hello": lambda: self._send_text("Hello, World!"),
            "finish": lambda: self._finish_event(args[0] if args else ""),
            "youtube": lambda: self._send_text(messages.YOUTUBE),
            "instagram": lambda: self._send_text(messages.INSTAGRAM),
            "twitter": lambda: self._send_text(messages.TWITTER),
            "homepage": lambda: self._send_text(messages.HOMEPAGE),
        }

        handler = handlers.get(cmd_name)
        if handler is None:
            await self._send_text(messages.CMD_ERROR)
            logger.error("LINE command not found: %s", cmd_name)
            return False

        await handler()
        return True

    async def _practice(self) -> None:
        result = await get_practice_events()
        if result.error:
            logger.error("practice error: %s", result.error)
            return
        if result.text:
            await self._send_text(result.text)
        elif result.is_empty and self._is_webhook:
            await self._send_text(messages.NO_PRACTICE)

    async def _reminder(self, day_left: str | None = None) -> None:
        result = await get_reminder_events(day_left)
        if result.error:
            logger.error("reminder error: %s", result.error)
            return
        if result.is_empty and self._is_webhook:
            await self._send_text(messages.NONE_REMIND_TASK)
            return
        if result.events:
            builder = ReminderFlexBuilder()
            for event in result.events:
                builder.add_reminder(
                    job=event["job"],
                    person=event["person"],
                    deadline=event["date"],
                    last_days=event["last_days"],
                    task=event["task"],
                    memo=event["memo"],
                    event_id=event["id"],
                )
            await self._send_flex(builder.build())

    async def _finish_event(self, event_id: str) -> None:
        result = await finish_event(event_id)
        if result.text:
            await self._send_text(result.text)
        elif result.error:
            await self._send_text(result.error)

    async def _change_group(self) -> None:
        """リマインド対象グループを変更する (バグ修正: source_group_id を使用)."""
        group_id = self._source_group_id
        if not group_id:
            logger.warning("changeGroup called without source group_id")
            return

        settings = get_settings()
        if not settings.is_debug:
            from linebot.v3.messaging import AsyncApiClient, AsyncMessagingApi, Configuration

            config = Configuration(access_token=self._token)
            async with AsyncApiClient(config) as api_client:
                api = AsyncMessagingApi(api_client)
                summary = await api.get_group_summary(group_id)
                group_name = summary.group_name
        else:
            group_name = "test_group_name"

        if group_name is None:
            await self._send_text(messages.CHANGE_GROUP_ERROR)
            return

        if self._group_store:
            await self._group_store.set_group_info(group_id, group_name)

        if self._bot_store and self._bot_id is not None:
            bots = await self._bot_store.list_all()
            for bot in bots:
                new_in_group = bot.id == self._bot_id
                await self._bot_store.update(bot.id, in_group=new_in_group)

        await self._send_text(messages.CHANGE_GROUP)

    async def _send_text(self, text: str) -> None:
        """テキストメッセージを送信する."""
        settings = get_settings()
        if settings.is_debug:
            logger.info("[DEBUG] LINE message: %s", text)
            return

        from linebot.v3.messaging import AsyncApiClient, AsyncMessagingApi, Configuration
        from linebot.v3.messaging.models import (
            ReplyMessageRequest,
            PushMessageRequest,
            TextMessage,
        )

        config = Configuration(access_token=self._token)
        async with AsyncApiClient(config) as api_client:
            api = AsyncMessagingApi(api_client)
            if self._is_webhook and self._reply_token:
                await api.reply_message(
                    ReplyMessageRequest(
                        reply_token=self._reply_token,
                        messages=[TextMessage(text=text)],
                    )
                )
            elif self._target_group_id:
                await api.push_message(
                    PushMessageRequest(
                        to=self._target_group_id,
                        messages=[TextMessage(text=text)],
                    )
                )

    async def _send_flex(self, flex_messages: list) -> None:
        """Flex Message を送信する."""
        settings = get_settings()
        if settings.is_debug:
            logger.info("[DEBUG] LINE flex message: %d messages", len(flex_messages))
            return

        from linebot.v3.messaging import AsyncApiClient, AsyncMessagingApi, Configuration
        from linebot.v3.messaging.models import (
            ReplyMessageRequest,
            PushMessageRequest,
        )

        config = Configuration(access_token=self._token)
        async with AsyncApiClient(config) as api_client:
            api = AsyncMessagingApi(api_client)
            if self._is_webhook and self._reply_token:
                await api.reply_message(
                    ReplyMessageRequest(
                        reply_token=self._reply_token,
                        messages=flex_messages,
                    )
                )
            elif self._target_group_id:
                await api.push_message(
                    PushMessageRequest(
                        to=self._target_group_id,
                        messages=flex_messages,
                    )
                )
