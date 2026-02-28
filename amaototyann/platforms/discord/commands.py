"""Discord Bot コマンド定義."""

import logging

import discord
from discord import app_commands

from amaototyann import messages
from amaototyann.core.commands import finish_event, get_practice_events, get_reminder_events
from amaototyann.platforms.discord.message_sender import DiscordSender, WebhookResponse
from amaototyann.platforms.discord.ui import ProgressButton, ProgressStatus

logger = logging.getLogger(__name__)

_registered = False


def register_commands(tree: app_commands.CommandTree) -> None:
    """スラッシュコマンドを CommandTree に登録する."""
    global _registered
    if _registered:
        return
    _registered = True

    @tree.command(name="help", description="ヘルプコマンド")
    async def help_cmd(interaction: discord.Interaction) -> None:
        text = "利用可能なコマンド一覧だよ！\n"
        text += "`/help` : ヘルプコマンド\n"
        text += "`/reminder` : リマインダーを送信するコマンド\n"
        text += "`/practice` : 練習があるか送信するコマンド\n"
        text += "`/finish` : リマインダー通知を終了するコマンド\n"
        text += "`/place` : 場所を送信するコマンド（未実装）\n"
        text += "`/handover` : 引き継ぎ資料のURLを送信するコマンド\n"
        text += "`/youtube` : YouTubeのURLを送信するコマンド\n"
        text += "`/instagram` : InstagramのURLを送信するコマンド\n"
        text += "`/twitter` : TwitterのURLを送信するコマンド\n"
        text += "`/homepage` : ホームページのURLを送信するコマンド\n"
        sender = DiscordSender(interaction=interaction)
        await sender.send(text)

    @tree.command(name="reminder", description="リマインダーを送信するコマンド")
    async def reminder_cmd(interaction: discord.Interaction) -> None:
        sender = DiscordSender(interaction=interaction)
        await _reminder(sender)

    @tree.command(name="practice", description="練習があるか送信するコマンド")
    async def practice_cmd(interaction: discord.Interaction) -> None:
        sender = DiscordSender(interaction=interaction)
        await _practice(sender)

    @tree.command(name="finish", description="リマインダー通知を終了するコマンド")
    @app_commands.describe(event_id="終了するイベントのID")
    async def finish_cmd(interaction: discord.Interaction, event_id: str) -> None:
        sender = DiscordSender(interaction=interaction)
        await _finish_event(sender, event_id)

    @tree.command(name="place", description="場所を送信するコマンド（未実装）")
    async def place_cmd(interaction: discord.Interaction) -> None:
        sender = DiscordSender(interaction=interaction)
        await sender.send(messages.PLACE)

    @tree.command(name="handover", description="引き継ぎ資料のURLを送信するコマンド")
    async def handover_cmd(interaction: discord.Interaction) -> None:
        sender = DiscordSender(interaction=interaction)
        await sender.send(messages.HANDOVER)

    @tree.command(name="hello", description="say hello to the world!")
    async def hello_cmd(interaction: discord.Interaction) -> None:
        sender = DiscordSender(interaction=interaction)
        await sender.send("Hello, World!")

    @tree.command(name="youtube", description="YouTubeのURLを送信するコマンド")
    async def youtube_cmd(interaction: discord.Interaction) -> None:
        sender = DiscordSender(interaction=interaction)
        await sender.send(messages.YOUTUBE)

    @tree.command(name="instagram", description="InstagramのURLを送信するコマンド")
    async def instagram_cmd(interaction: discord.Interaction) -> None:
        sender = DiscordSender(interaction=interaction)
        await sender.send(messages.INSTAGRAM)

    @tree.command(name="twitter", description="TwitterのURLを送信するコマンド")
    async def twitter_cmd(interaction: discord.Interaction) -> None:
        sender = DiscordSender(interaction=interaction)
        await sender.send(messages.TWITTER)

    @tree.command(name="homepage", description="ホームページのURLを送信するコマンド")
    async def homepage_cmd(interaction: discord.Interaction) -> None:
        sender = DiscordSender(interaction=interaction)
        await sender.send(messages.HOMEPAGE)


async def _practice(sender: DiscordSender, *, is_broadcast: bool = False) -> None:
    """練習予定を送信する."""
    try:
        await sender.defer()
        result = await get_practice_events()
        if result.error:
            logger.error("practice error: %s", result.error)
            return
        if result.text:
            await sender.send(result.text)
        elif result.is_empty and not is_broadcast:
            await sender.send(messages.NO_PRACTICE)
    except Exception:
        logger.exception("Discord practice error")


async def _reminder(
    sender: DiscordSender, *, day_left: str | None = None, is_broadcast: bool = False
) -> None:
    """リマインダーを送信する."""
    try:
        await sender.defer(ephemeral=True)
        result = await get_reminder_events(day_left)

        if result.error:
            await sender.send(result.error)
            return
        if result.is_empty and is_broadcast:
            return
        if result.is_empty:
            await sender.send(messages.NONE_REMIND_TASK)
            return

        await sender.send("リマインダーだよ！")
        target_webhooks = await sender.get_broadcast_webhooks() if sender.broadcast else None
        if result.events:
            for event in result.events:
                await _send_remind_msg(sender, event, target_webhooks)
    except Exception:
        logger.exception("Discord reminder error")


async def _send_remind_msg(
    sender: DiscordSender,
    event: dict,
    target_webhooks: list[discord.Webhook] | None,
) -> None:
    """個別リマインダーメッセージを送信する."""
    embed = discord.Embed(colour=0x00B0F4)
    embed.add_field(
        name=f"{event['job']} - 締め切りまで残り**{event['last_days']}**日",
        value=f"{event['task']}<@{event['person']}>\n{event['memo']}",
        inline=False,
    )
    embed.add_field(name=ProgressStatus.WAITING, value="", inline=False)

    res = await sender.send(
        embed=embed,
        force_webhook=True,
        target_webhooks=target_webhooks,
        wait=True,
        username="あまおとちゃん",
        avatar_url="https://github.com/tokuactclub/discord/blob/main/image.png?raw=true",
    )

    if isinstance(res, discord.WebhookMessage):
        responses = [WebhookResponse(webhook=sender._webhook, msg=res)]
    elif isinstance(res, list) and all(isinstance(r, WebhookResponse) for r in res):
        responses = res
    else:
        logger.error("Unexpected response type: %s", type(res))
        return

    for response in responses:
        webhook = response.webhook
        msg = response.msg
        target_role = (
            discord.utils.get(webhook.guild.roles, name=event["job"]) if webhook.guild else None
        )
        view = ProgressButton(
            allow_role=target_role,
            webhook=webhook,
            message_id=msg.id,
            on_done=lambda interaction, button, eid=event["id"]: _finish_event(
                DiscordSender(interaction=interaction),
                eid,
            ),
        )
        await webhook.edit_message(msg.id, embed=embed, view=view)


async def _finish_event(sender: DiscordSender, event_id: str) -> None:
    """リマインダー通知を終了する."""
    try:
        result = await finish_event(event_id)
        if result.text:
            await sender.send(result.text)
        elif result.error:
            await sender.send(result.error)
    except Exception:
        logger.exception("Discord finish error")


async def broadcast_practice(bot: discord.Client) -> None:
    """ブロードキャストで練習通知を送信する."""
    sender = DiscordSender(bot=bot, broadcast=True)
    await _practice(sender, is_broadcast=True)


async def broadcast_reminder(bot: discord.Client) -> None:
    """ブロードキャストでリマインダーを送信する."""
    sender = DiscordSender(bot=bot, broadcast=True)
    await _reminder(sender, is_broadcast=True)
