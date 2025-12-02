"""LINE BotのWebhookを受け取るFlaskサーバー."""
import os
from typing import Callable, Any
from datetime import datetime, timezone, timedelta
import threading
import time
import asyncio
import schedule
import discord

from amaototyann.src.commands._command import Commands
from amaototyann.src import messages, logger

GAS_URL = os.getenv('GAS_URL')

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if DISCORD_TOKEN is None:
    logger.error("DISCORD_BOT_TOKEN is not set")
    exit(1)

# Discord Botの起動
intents = discord.Intents.default()  # デフォルトのインテントを使用
intents.message_content = True  # メッセージ内容の受信を有効化
intents.messages = True  # メッセージの受信を有効化

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)


@client.event
async def on_guild_join(guild):
    """botがサーバーに参加したときに実行される処理."""
    logger.info("Joined guild: %s (id: %s)", guild.name, guild.id)
    # 挨拶メッセージを送信
    general = discord.utils.find(lambda x: x.name == 'general', guild.text_channels)
    if general and general.permissions_for(guild.me).send_messages:
        await general.send(messages.JOIN)


@client.event
async def on_message(message):
    """メッセージ受信時に実行される処理."""
    # メッセージ送信者がボットの場合は無視する
    if message.author.bot:
        return
    # logger.info("Received message: %s from %s", message.content, message.author)


@client.event
async def on_ready():
    """ボットの起動時に実行される処理."""
    logger.info("Bot is ready. Logged in as %s", client.user)
    # アクティビティを設定
    new_activity = "テスト"
    await client.change_presence(activity=discord.Game(new_activity))

    # スラッシュコマンドの登録
    # command.pyで定義しているコマンドを自動で登録する

    def make_cmd(process: Callable[..., Any]) -> Callable[..., Any]:
        """スコーププ内関数でコマンド処理を生成する関数."""
        async def _cmd(interaction: discord.Interaction):
            cmd = Commands(interaction=interaction)
            await process(cmd)
        return _cmd
    for cmd in Commands.registry:
        tree.add_command(
            discord.app_commands.Command(
                name=cmd.text,
                description=cmd.description,
                callback=make_cmd(cmd.process)
            )
        )
    # スケジュールを起動
    start_scheduler_from_bot_loop()

    # スラッシュコマンドを同期
    # コマンドの種類が増えた場合などに必要
    # 単にコマンドの挙動を変えただけの場合は不要
    # レート制限があるため、頻繁に実行しないこと
    # await tree.sync()


async def practice_command():
    await Commands(bot=client, broadcast_webhook_msg=True).practice()


async def reminder_command():
    await Commands(bot=client, broadcast_webhook_msg=True).reminder()


def schedule_task(loop: asyncio.AbstractEventLoop):
    """スケジュール設定."""
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    logger.info("Scheduler started at %s", now)

    # コメント: 既存のイベントループ上でコマンドを実行するラッパー
    def run_practice():
        asyncio.run_coroutine_threadsafe(practice_command(), loop)

    def run_reminder():
        asyncio.run_coroutine_threadsafe(reminder_command(), loop)

    # JST 8時のタスクをスケジュール
    schedule.every().day.at("08:00").do(run_practice)

    # JST 20時のタスクをスケジュール
    schedule.every().day.at("20:00").do(run_reminder)

    while True:
        schedule.run_pending()
        time.sleep(1)


# コメント: 実際には「bot が起動し、イベントループが動いているスレッド」で loop を取る
# 例: on_ready などから呼ぶ
def start_scheduler_from_bot_loop():
    loop = asyncio.get_running_loop()  # bot.run(...) の中ならこれで取得できる
    scheduler_thread = threading.Thread(
        target=schedule_task,
        args=(loop,),
        daemon=True,
    )
    scheduler_thread.start()


client.run(DISCORD_TOKEN)
