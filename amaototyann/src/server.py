"""LINE BotのWebhookを受け取るFlaskサーバー."""
import os
from typing import Callable, Any
import discord
from discord import app_commands

from amaototyann.src.command import Commands as cmds
from amaototyann.src import messages, logger

GAS_URL = os.getenv('GAS_URL')

DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if DISCORD_TOKEN is None:
    logger.error("DISCORD_BOT_TOKEN is not set")
    exit(1)


# def boot_server():
#     """サーバーを常時起動させ、定期的にデータベースのバックアップを行う. threadsで実行する
#     """
#     server_url = os.getenv("SERVER_URL")
#     if server_url is None:
#         logger.error("SERVER_URL is not set")
#         return
#     while True:
#         try:
#             url = os.path.join(server_url, "backupDatabase/")
#             logger.info("===boot server===send backup request: %s", url)
#             requests.get(url, timeout=60)
#         except Exception as e:
#             logger.error("Error sending backup request: %s", e)
#         time.sleep(60 * 3)


# server_boot_script_running = os.getenv("SERVER_BOOT_SCRIPT_RUNNING")
# if not server_boot_script_running or server_boot_script_running == "False":
#     # 別ワーカーで実行されていない場合のみ起動
#     os.environ["SERVER_BOOT_SCRIPT_RUNNING"] = "True"
#     thread = threading.Thread(target=boot_server)
#     thread.start()


# Discord Botの起動
intents = discord.Intents.default()  # デフォルトのインテントを使用
intents.message_content = True  # メッセージ内容の受信を有効化
intents.messages = True  # メッセージの受信を有効化

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# integrate_flask_logger(app)


# @app.route('/backupDatabase/', methods=['GET'])
# def backup_database():
#     """データベースをスプレッドシートにバックアップするエンドポイント
#     """
#     res, code = db_group.backup_to_gas()
#     res2, code2 = db_bot.backup_to_gas()
#     message = f"group info: {res} - {code}    bot info: {res2} - {code2}"
#     code = 200 if code == 200 and code2 == 200 else 500
#     logger.info("%s-%d", message, code)
#     return message, code


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
            await process(interaction)
        return _cmd
    for cmd in cmds.registry:
        tree.add_command(
            app_commands.Command(
                name=cmd.text,
                description=cmd.description,
                callback=make_cmd(cmd.process)
            )
        )

    # スラッシュコマンドを同期
    # コマンドの種類が増えた場合などに必要
    # 単にコマンドの挙動を変えただけの場合は不要
    # レート制限があるため、頻繁に実行しないこと
    # await tree.sync()


client.run(DISCORD_TOKEN)
