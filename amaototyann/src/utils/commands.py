"""commandでのユーティリティを定義するモジュール"""
import dataclasses
from typing import NamedTuple, Callable, Any, Optional
import discord
from amaototyann.src import logger


class Command(NamedTuple):
    """各コマンドの情報を格納するクラス"""
    text: str
    description: str
    process: Callable[..., Any]


class CommandRegistry(type):
    """Commandクラスのメタクラス"""
    registry: list[Command] = []

    def __new__(mcs, name, bases, ns):
        """Commandが定義されたときにregistryに登録する処理"""
        cls = super().__new__(mcs, name, bases, dict(ns))
        # クラス定義時に見つかった Command だけで registry を初期化
        cls.registry = [v for v in ns.values() if isinstance(v, Command)]
        return cls


@dataclasses.dataclass
class WebhookResponse:
    """Broadcastコマンドのレスポンスを格納するクラス"""
    webhook: discord.Webhook
    msg: discord.WebhookMessage


BroadcastResponse = list[WebhookResponse]


class MessageSender():
    """discordのメッセージ送信を行うクラス"""

    def __init__(
        self,
        interaction: Optional[discord.Interaction] = None,
        webhook: Optional[discord.Webhook] = None,
        bot: Optional[discord.Client] = None,
        broadcast_webhook_msg: bool = False
    ):
        """_summary_

        Args:
            interaction (Optional[discord.Interaction], optional): discordのメッセージイベントで取得されるinteraction. Defaults to None.
            webhook (Optional[discord.Webhook], optional): discordのWebhookオブジェクト. Defaults to None.
            bot (Optional[discord.Client], optional): discord botのクライアントオブジェクト. Defaults to None.
            broadcast_webhook_msg (bool, optional): メッセージを全サーバーに送信する。`bot`が必要. Defaults to False.
        """
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
        **kwargs,  # Additional arguments for discord.Messageable.send
    ):
        """interaction or webhook 経由で送信
        Args:
            content (Optional[str], optional): メッセージ内容. Defaults to None.
            embed (Optional[discord.Embed], optional): 埋め込みメッセージ. Defaults to None.
            view (Optional[discord.ui.View], optional): メッセージのView. Defaults to None.
            ephemeral (bool, optional): ephemeralメッセージにするかどうか. Defaults to False.
            force_sendWithWebhook (bool, optional): webhook経由で送信するかどうか. Defaults to False.
            target_webhooks_on_broadcast (Optional[list[discord.Webhook]], optional): broadcast時の送信先Webhookリスト. Defaults to None.
        Raises:
            ValueError: interactionもwebhookも提供されなかった場合に発生
        Returns:
            discord.Message | discord.WebhookMessage | BroadcastResponse: 送信されたメッセージオブジェクト
        """
        assert self.interaction is not None or self.webhook is not None or self.broadcast_webhook_msg, \
            "Either interaction or webhook must be provided."

        kwargs.update({
            "content": content,
            "embed": embed,
            "view": view,
            "ephemeral": ephemeral
        })
        # Noneは許容されないため、Noneの値を除去
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # force_sendWithWebhookの場合、webhookを作成しておく
        # slashコマンドの場合のwebhook取得・作成処理
        if force_sendWithWebhook and self.webhook is None and not self.broadcast_webhook_msg:
            # interactionのみ提供されている場合、interactionのチャンネルからwebhookを取得or 作成
            assert self.interaction is not None, \
                "interaction must be provided when force_sendWithWebhook is True and webhook is None."
            channel = self.interaction.channel
            if channel is None or not isinstance(channel, discord.TextChannel):
                msg = "Error: Channel is None or not TextChannel"
                await self.send_message(msg)
                logger.error(msg)
                return

            webhooks = await channel.webhooks()
            webhook_name = "amaoto_task_feed"  # TODO: 定数化
            webhook = discord.utils.get(webhooks, name=webhook_name)  # 既存のWebhookを取得
            if webhook is None:  # なければ新規作成
                webhook = await channel.create_webhook(name=webhook_name)
            self.webhook = webhook

        _inter = self.interaction
        # broadcastの場合. 内部的にWebhook送信であるため、force_sendWithWebhookは無視される
        if self.broadcast_webhook_msg:
            return await self._broadcast_message(**kwargs, webhooks=target_webhooks_on_broadcast)
        elif force_sendWithWebhook:
            return await self.webhook.send(**kwargs)  # type:ignore
        # interaction がある場合--初回応答
        elif _inter is not None and _inter.response.is_done() is False:
            return await _inter.response.send_message(**kwargs)
        # interaction がある場合--2回目以降の応答
        elif _inter is not None:
            return await _inter.followup.send(**kwargs)
        # webhook 経由の場合
        elif self.webhook:
            return await self.webhook.send(**kwargs)
        else:
            raise ValueError("Either interaction or webhook must be provided.")

    async def _get_broadcast_targets_webhooks(self):
        """broadcastの送信先Webhookを取得する関数"""
        assert self.bot is not None, "bot must be provided to use broadcast_message"
        webhooks: list[discord.Webhook] = []
        for guild in self.bot.guilds:  # 全てのサーバーに送信
            for channel in guild.text_channels:  # 全てのテキストチャンネルに送信
                try:
                    channel_webhooks = await channel.webhooks()
                    webhook_name = "amaoto_task_feed"
                    webhook = discord.utils.get(channel_webhooks, name=webhook_name)  # 既存のWebhookを取得
                    if webhook:
                        webhooks.append(webhook)
                except Exception as e:  # pylint: disable=W0718
                    logger.exception(
                        "Failed to get webhook for guild %s channel %s: %s",
                        guild.name if guild else "Unknown",
                        channel.name if channel else "Unknown",
                        e
                    )
                    continue
        return webhooks

    async def _broadcast_message(
            self,
            webhooks: Optional[list[discord.Webhook]] = None,
            **kwargs,
    ):
        assert self.broadcast_webhook_msg, "broadcast_webhook_msg must be True to use broadcast_message"
        assert self.bot is not None, "bot must be provided to use broadcast_message"
        result: BroadcastResponse = []
        if webhooks is None:
            webhooks = await self._get_broadcast_targets_webhooks()
        for webhook in webhooks:
            try:
                default_kwargs = {
                    "username": "あまおとちゃん",
                    "avatar_url": "https://github.com/tokuactclub/discord/blob/main/image.png?raw=true",
                    "wait": True
                }
                default_kwargs.update(kwargs)
                msg = await webhook.send(
                    **default_kwargs
                )
                result.append(WebhookResponse(webhook=webhook, msg=msg))
            except Exception as e:  # pylint: disable=W0718
                logger.exception(
                    "Failed to send broadcast message to guild %s channel %s: %s",
                    webhook.guild.name if webhook.guild else "Unknown",
                    webhook.channel.name if webhook.channel else "Unknown",
                    e
                )
                continue
        return result

    async def defer_response(self, ephemeral: bool = False):
        """interactionの応答を保留する関数"""
        if self.interaction:
            await self.interaction.response.defer(thinking=True, ephemeral=ephemeral)
