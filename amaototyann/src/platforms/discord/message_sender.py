"""Discord メッセージ送信ユーティリティ."""
import dataclasses
from typing import NamedTuple, Callable, Any, Optional

import discord

from amaototyann.src import logger


class Command(NamedTuple):
    """各コマンドの情報を格納するクラス."""
    text: str
    description: str
    process: Callable[..., Any]


class CommandRegistry(type):
    """Command クラスのメタクラス."""
    registry: list[Command] = []

    def __new__(mcs, name, bases, ns):
        cls = super().__new__(mcs, name, bases, dict(ns))
        cls.registry = [v for v in ns.values() if isinstance(v, Command)]
        return cls


@dataclasses.dataclass
class WebhookResponse:
    """Broadcast コマンドのレスポンスを格納するクラス."""
    webhook: discord.Webhook
    msg: discord.WebhookMessage


BroadcastResponse = list[WebhookResponse]


class MessageSender:
    """Discord のメッセージ送信を行うクラス."""

    def __init__(
        self,
        interaction: Optional[discord.Interaction] = None,
        webhook: Optional[discord.Webhook] = None,
        bot: Optional[discord.Client] = None,
        broadcast_webhook_msg: bool = False,
    ):
        self.interaction = interaction
        self.webhook = webhook
        self.bot = bot
        self.broadcast_webhook_msg = broadcast_webhook_msg

    async def send_message(
        self,
        content: Optional[str] = None,
        embed: Optional[discord.Embed] = None,
        view: Optional[discord.ui.View] = None,
        ephemeral: bool = False,
        force_sendWithWebhook: bool = False,
        target_webhooks_on_broadcast: Optional[list[discord.Webhook]] = None,
        **kwargs,
    ):
        assert self.interaction is not None or self.webhook is not None or self.broadcast_webhook_msg, \
            "Either interaction or webhook must be provided."

        kwargs.update({"content": content, "embed": embed, "view": view, "ephemeral": ephemeral})
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        if force_sendWithWebhook and self.webhook is None and not self.broadcast_webhook_msg:
            assert self.interaction is not None
            channel = self.interaction.channel
            if channel is None or not isinstance(channel, discord.TextChannel):
                msg = "Error: Channel is None or not TextChannel"
                await self.send_message(msg)
                logger.error(msg)
                return
            webhooks = await channel.webhooks()
            webhook_name = "amaoto_task_feed"
            webhook = discord.utils.get(webhooks, name=webhook_name)
            if webhook is None:
                webhook = await channel.create_webhook(name=webhook_name)
            self.webhook = webhook

        _inter = self.interaction
        if self.broadcast_webhook_msg:
            return await self._broadcast_message(**kwargs, webhooks=target_webhooks_on_broadcast)
        elif force_sendWithWebhook:
            return await self.webhook.send(**kwargs)
        elif _inter is not None and _inter.response.is_done() is False:
            return await _inter.response.send_message(**kwargs)
        elif _inter is not None:
            return await _inter.followup.send(**kwargs)
        elif self.webhook:
            return await self.webhook.send(**kwargs)
        else:
            raise ValueError("Either interaction or webhook must be provided.")

    async def _get_broadcast_targets_webhooks(self):
        assert self.bot is not None
        webhooks: list[discord.Webhook] = []
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                try:
                    channel_webhooks = await channel.webhooks()
                    webhook = discord.utils.get(channel_webhooks, name="amaoto_task_feed")
                    if webhook:
                        webhooks.append(webhook)
                except Exception as e:
                    logger.exception(
                        "Failed to get webhook for guild %s channel %s: %s",
                        guild.name if guild else "Unknown",
                        channel.name if channel else "Unknown", e,
                    )
        return webhooks

    async def _broadcast_message(self, webhooks: Optional[list[discord.Webhook]] = None, **kwargs):
        assert self.broadcast_webhook_msg and self.bot is not None
        result: BroadcastResponse = []
        if webhooks is None:
            webhooks = await self._get_broadcast_targets_webhooks()
        for webhook in webhooks:
            try:
                default_kwargs = {
                    "username": "あまおとちゃん",
                    "avatar_url": "https://github.com/tokuactclub/discord/blob/main/image.png?raw=true",
                    "wait": True,
                }
                default_kwargs.update(kwargs)
                msg = await webhook.send(**default_kwargs)
                result.append(WebhookResponse(webhook=webhook, msg=msg))
            except Exception as e:
                logger.exception(
                    "Failed to send broadcast message to guild %s channel %s: %s",
                    webhook.guild.name if webhook.guild else "Unknown",
                    webhook.channel.name if webhook.channel else "Unknown", e,
                )
        return result

    async def defer_response(self, ephemeral: bool = False):
        if self.interaction:
            await self.interaction.response.defer(thinking=True, ephemeral=ephemeral)
