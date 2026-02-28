"""Discord Bot クライアント."""
import os
from datetime import time, timezone, timedelta
from typing import Callable, Any

import discord
from discord.ext import tasks

from amaototyann.src import logger, messages
from amaototyann.src.platforms.discord.commands import DiscordCommands

# JST timezone
JST = timezone(timedelta(hours=9))

# Discord Bot の設定
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)


@client.event
async def on_guild_join(guild):
    """Bot がサーバーに参加したときに実行される処理."""
    logger.info("Joined guild: %s (id: %s)", guild.name, guild.id)
    general = discord.utils.find(lambda x: x.name == 'general', guild.text_channels)
    if general and general.permissions_for(guild.me).send_messages:
        await general.send(messages.JOIN_DISCORD)


@client.event
async def on_message(message):
    """メッセージ受信時に実行される処理."""
    if message.author.bot:
        return


@client.event
async def on_ready():
    """ボットの起動時に実行される処理."""
    logger.info("Discord Bot is ready. Logged in as %s", client.user)
    await client.change_presence(activity=discord.Game("あまおとちゃん"))

    def make_cmd(process: Callable[..., Any]) -> Callable[..., Any]:
        async def _cmd(interaction: discord.Interaction):
            cmd = DiscordCommands(interaction=interaction)
            await process(cmd)
        return _cmd

    for cmd in DiscordCommands.registry:
        tree.add_command(
            discord.app_commands.Command(
                name=cmd.text, description=cmd.description,
                callback=make_cmd(cmd.process),
            )
        )

    # スケジューラを起動
    if not practice_task.is_running():
        practice_task.start()
    if not reminder_task.is_running():
        reminder_task.start()

    logger.info("Discord slash commands registered and schedulers started.")


# === discord.ext.tasks スケジューラ ===
@tasks.loop(time=time(hour=8, minute=0, tzinfo=JST))
async def practice_task():
    """JST 08:00 に練習通知を送信."""
    logger.info("Running scheduled practice task")
    await DiscordCommands(bot=client, broadcast_webhook_msg=True).practice()


@tasks.loop(time=time(hour=20, minute=0, tzinfo=JST))
async def reminder_task():
    """JST 20:00 にリマインダーを送信."""
    logger.info("Running scheduled reminder task")
    await DiscordCommands(bot=client, broadcast_webhook_msg=True).reminder()


@practice_task.before_loop
async def before_practice():
    await client.wait_until_ready()


@reminder_task.before_loop
async def before_reminder():
    await client.wait_until_ready()
