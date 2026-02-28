"""Discord Bot コマンド定義."""
from typing import Optional

import discord

from amaototyann.src import logger, messages
from amaototyann.src.core.commands import get_practice_events, get_reminder_events, finish_event
from amaototyann.src.platforms.discord.ui import ProgressButton, ProgressStatus
from amaototyann.src.platforms.discord.message_sender import (
    Command, CommandRegistry, WebhookResponse, MessageSender,
)


class DiscordCommands(MessageSender, metaclass=CommandRegistry):
    """Discord Bot のコマンド処理クラス."""

    def __init__(
        self,
        interaction: Optional[discord.Interaction] = None,
        webhook: Optional[discord.Webhook] = None,
        bot: Optional[discord.Client] = None,
        broadcast_webhook_msg: bool = False,
    ):
        super().__init__(
            interaction=interaction, webhook=webhook,
            bot=bot, broadcast_webhook_msg=broadcast_webhook_msg,
        )

    HELP = Command(text="help", description="ヘルプコマンド", process=lambda self: self._help())
    REMINDER = Command(text="reminder", description="リマインダーを送信するコマンド", process=lambda self: self.reminder())
    PRACTICE = Command(text="practice", description="練習があるか送信するコマンド。事前にGASで練習予定を登録しておく必要がある。", process=lambda self: self.practice())
    PLACE = Command(text="place", description="場所を送信するコマンド（未実装）", process=lambda self: self.send_message(messages.PLACE))
    HANDOVER = Command(text="handover", description="引き継ぎ資料のURLを送信するコマンド", process=lambda self: self.send_message(messages.HANDOVER))
    HELLO = Command(text="hello", description="say hello to the world!", process=lambda self: self.send_message("Hello, World!"))
    FINISH = Command(text="finish", description="リマインダー通知を終了するコマンド", process=lambda self, e_id: self._finish_event(e_id))
    YOUTUBE = Command(text="youtube", description="YouTubeのURLを送信するコマンド", process=lambda self: self.send_message(messages.YOUTUBE))
    INSTAGRAM = Command(text="instagram", description="InstagramのURLを送信するコマンド", process=lambda self: self.send_message(messages.INSTAGRAM))
    TWITTER = Command(text="twitter", description="TwitterのURLを送信するコマンド", process=lambda self: self.send_message(messages.TWITTER))
    HOMEPAGE = Command(text="homepage", description="ホームページのURLを送信するコマンド", process=lambda self: self.send_message(messages.HOMEPAGE))

    async def send_single_remind_msg(self, event: dict, target_webhooks: Optional[list[discord.Webhook]]):
        embed = discord.Embed(colour=0x00b0f4)
        embed.add_field(
            name=f"{event['job']} - 締め切りまで残り**{event['last_days']}**日",
            value=f"{event['task']}<@{event['person']}>\n{event['memo']}",
            inline=False,
        )
        embed.add_field(name=ProgressStatus.WAITING, value="", inline=False)

        res = await self.send_message(
            embed=embed, force_sendWithWebhook=True,
            target_webhooks_on_broadcast=target_webhooks, wait=True,
            username="あまおとちゃん",
            avatar_url="https://github.com/tokuactclub/discord/blob/main/image.png?raw=true",
        )
        if isinstance(res, discord.WebhookMessage):
            responses = [WebhookResponse(webhook=self.webhook, msg=res)]
        elif isinstance(res, list) and all(isinstance(r, WebhookResponse) for r in res):
            responses = res
        else:
            logger.error("Unexpected response type: %s", type(res))
            return

        for response in responses:
            webhook = response.webhook
            msg = response.msg
            target_role = discord.utils.get(webhook.guild.roles, name=event["job"]) if webhook.guild else None
            view = ProgressButton(
                allow_role=target_role, webhook=webhook, message_id=msg.id,
                on_done=lambda interaction, button: self._finish_event(event["id"]),
            )
            await webhook.edit_message(msg.id, embed=embed, view=view)

    async def reminder(self, day_left: Optional[str] = None):
        try:
            await self.defer_response(ephemeral=True)
            result = await get_reminder_events(day_left)

            if result.error:
                await self.send_message(result.error)
                return
            if result.is_empty and self.broadcast_webhook_msg:
                return
            if result.is_empty:
                await self.send_message(messages.NONE_REMIND_TASK)
                return

            await self.send_message("リマインダーだよ！")
            target_webhooks = await self._get_broadcast_targets_webhooks() if self.broadcast_webhook_msg else None
            for event in result.events:
                await self.send_single_remind_msg(event, target_webhooks)
        except Exception as e:
            logger.exception(e)

    async def _finish_event(self, event_id: str):
        try:
            result = await finish_event(event_id)
            if result.text:
                await self.send_message(result.text)
            elif result.error:
                await self.send_message(result.error)
        except Exception as e:
            logger.exception(e)

    async def practice(self):
        try:
            await self.defer_response()
            result = await get_practice_events()

            if result.error:
                logger.error("practice error: %s", result.error)
                return
            if result.text:
                await self.send_message(result.text)
            elif result.is_empty and not self.broadcast_webhook_msg:
                await self.send_message(messages.NO_PRACTICE)
        except Exception as e:
            logger.exception(e)

    async def _help(self):
        text = "利用可能なコマンド一覧だよ！\n"
        for cmd in DiscordCommands.registry:
            text += f"`/{cmd.text}` : {cmd.description}\n"
        await self.send_message(text)
