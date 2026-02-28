"""Discord Bot クライアント."""

import logging
from datetime import time, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import tasks
from fastapi import FastAPI

from amaototyann import messages

logger = logging.getLogger(__name__)

# JST timezone
JST = timezone(timedelta(hours=9))

# Discord Bot の設定
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

_app: FastAPI | None = None


def setup_events(app: FastAPI) -> None:
    """Discord イベントハンドラを登録する."""
    global _app
    _app = app

    @client.event
    async def on_guild_join(guild: discord.Guild) -> None:
        logger.info("Joined guild: %s (id: %s)", guild.name, guild.id)
        general = discord.utils.find(lambda x: x.name == "general", guild.text_channels)
        if general and general.permissions_for(guild.me).send_messages:
            await general.send(messages.JOIN_DISCORD)

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return

    @client.event
    async def on_ready() -> None:
        logger.info("Discord Bot is ready. Logged in as %s", client.user)
        await client.change_presence(activity=discord.Game("あまおとちゃん"))

        # コマンドを同期
        from amaototyann.platforms.discord.commands import register_commands

        register_commands(tree, _app.state.sheets_client if _app else None)
        await tree.sync()

        # スケジューラを起動
        if not practice_task.is_running():
            practice_task.start()
        if not reminder_task.is_running():
            reminder_task.start()

        logger.info("Discord slash commands registered and schedulers started.")


# === discord.ext.tasks スケジューラ ===


@tasks.loop(time=time(hour=8, minute=0, tzinfo=JST))
async def practice_task() -> None:
    """JST 08:00 に練習通知を送信."""
    logger.info("Running scheduled practice task")
    from amaototyann.platforms.discord.commands import broadcast_practice

    sheets_client = _app.state.sheets_client if _app else None
    await broadcast_practice(client, sheets_client)


@tasks.loop(time=time(hour=20, minute=0, tzinfo=JST))
async def reminder_task() -> None:
    """JST 20:00 にリマインダーを送信."""
    logger.info("Running scheduled reminder task")
    from amaototyann.platforms.discord.commands import broadcast_reminder

    sheets_client = _app.state.sheets_client if _app else None
    await broadcast_reminder(client, sheets_client)


@practice_task.before_loop
async def before_practice() -> None:
    await client.wait_until_ready()


@reminder_task.before_loop
async def before_reminder() -> None:
    await client.wait_until_ready()
