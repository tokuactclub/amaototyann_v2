"""Discord メッセージ送信ユーティリティ."""

import dataclasses
import logging
from typing import Optional

import discord

logger = logging.getLogger(__name__)

WEBHOOK_NAME = "amaoto_task_feed"
AVATAR_URL = "https://github.com/tokuactclub/discord/blob/main/image.png?raw=true"
BOT_USERNAME = "あまおとちゃん"


@dataclasses.dataclass
class WebhookResponse:
    """Broadcast コマンドのレスポンスを格納するクラス."""
    webhook: discord.Webhook
    msg: discord.WebhookMessage


class DiscordSender:
    """Discord のメッセージ送信を行うクラス."""

    def __init__(
        self,
        interaction: Optional[discord.Interaction] = None,
        bot: Optional[discord.Client] = None,
        broadcast: bool = False,
    ) -> None:
        self.interaction = interaction
        self.bot = bot
        self.broadcast = broadcast
        self._webhook: Optional[discord.Webhook] = None

    async def send(
        self,
        content: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
        view: Optional[discord.ui.View] = None,
        ephemeral: bool = False,
        force_webhook: bool = False,
        target_webhooks: Optional[list[discord.Webhook]] = None,
        **kwargs: object,
    ) -> Optional[discord.WebhookMessage | list[WebhookResponse]]:
        """メッセージを送信する."""
        send_kwargs: dict = {"content": content, "embed": embed, "view": view, "ephemeral": ephemeral}
        send_kwargs.update(kwargs)
        send_kwargs = {k: v for k, v in send_kwargs.items() if v is not None}

        if force_webhook and self._webhook is None and not self.broadcast:
            await self._ensure_webhook()

        if self.broadcast:
            return await self._broadcast(**send_kwargs, webhooks=target_webhooks)
        elif force_webhook and self._webhook:
            return await self._webhook.send(**send_kwargs)
        elif self.interaction is not None:
            return await self._send_interaction(**send_kwargs)
        elif self._webhook:
            return await self._webhook.send(**send_kwargs)
        else:
            logger.error("No interaction or webhook available for sending")

    async def defer(self, *, ephemeral: bool = False) -> None:
        """インタラクションの応答を遅延させる."""
        if self.interaction:
            await self.interaction.response.defer(thinking=True, ephemeral=ephemeral)

    async def _ensure_webhook(self) -> None:
        """チャンネルの Webhook を取得または作成する."""
        if not self.interaction or not self.interaction.channel:
            return
        channel = self.interaction.channel
        if not isinstance(channel, discord.TextChannel):
            return
        webhooks = await channel.webhooks()
        self._webhook = discord.utils.get(webhooks, name=WEBHOOK_NAME)
        if self._webhook is None:
            self._webhook = await channel.create_webhook(name=WEBHOOK_NAME)

    async def _send_interaction(self, **kwargs: object) -> None:
        """インタラクションでメッセージを送信する."""
        if self.interaction is None:
            return
        if not self.interaction.response.is_done():
            await self.interaction.response.send_message(**kwargs)
        else:
            await self.interaction.followup.send(**kwargs)

    async def get_broadcast_webhooks(self) -> list[discord.Webhook]:
        """ブロードキャスト対象の Webhook リストを取得する."""
        if not self.bot:
            return []
        webhooks: list[discord.Webhook] = []
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                try:
                    channel_webhooks = await channel.webhooks()
                    wh = discord.utils.get(channel_webhooks, name=WEBHOOK_NAME)
                    if wh:
                        webhooks.append(wh)
                except Exception as e:
                    logger.exception(
                        "Failed to get webhook for %s/%s: %s",
                        guild.name, channel.name, e,
                    )
        return webhooks

    async def _broadcast(
        self,
        webhooks: Optional[list[discord.Webhook]] = None,
        **kwargs: object,
    ) -> list[WebhookResponse]:
        """全対象チャンネルにブロードキャストする."""
        if not self.bot:
            return []
        results: list[WebhookResponse] = []
        if webhooks is None:
            webhooks = await self.get_broadcast_webhooks()

        defaults = {"username": BOT_USERNAME, "avatar_url": AVATAR_URL, "wait": True}
        defaults.update(kwargs)

        for webhook in webhooks:
            try:
                msg = await webhook.send(**defaults)
                results.append(WebhookResponse(webhook=webhook, msg=msg))
            except Exception as e:
                logger.exception(
                    "Broadcast failed for %s/%s: %s",
                    webhook.guild.name if webhook.guild else "?",
                    webhook.channel.name if webhook.channel else "?",
                    e,
                )
        return results
