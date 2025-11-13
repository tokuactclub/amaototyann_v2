"""LINE BotのWebhookを受け取るFlaskサーバー."""
import os
from typing import Callable, Any
import threading
import time
import requests
from flask import Flask, request
from amaototyann.src.database import db_bot, db_group
from amaototyann.src import integrate_flask_logger, logger
from amaototyann.src.command import Commands

GAS_URL = os.getenv('GAS_URL')


#
def boot_server():
    """サーバーを常時起動させ、定期的にデータベースのバックアップを行う. threadsで実行する
    """
    server_url = os.getenv("SERVER_URL")
    if server_url is None:
        logger.error("SERVER_URL is not set")
        return
    while True:
        try:
            url = os.path.join(server_url, "backupDatabase/")
            logger.info("===boot server===send backup request: %s", url)
            requests.get(url, timeout=60)
        except Exception as e:
            logger.error("Error sending backup request: %s", e)
        time.sleep(60 * 3)


server_boot_script_running = os.getenv("SERVER_BOOT_SCRIPT_RUNNING")
if not server_boot_script_running or server_boot_script_running == "False":
    # 別ワーカーで実行されていない場合のみ起動
    os.environ["SERVER_BOOT_SCRIPT_RUNNING"] = "True"
    thread = threading.Thread(target=boot_server)
    thread.start()

# Flaskのインスタンスを作成
app = Flask(__name__)
app.strict_slashes = False  # type: ignore
integrate_flask_logger(app)


@app.route('/backupDatabase/', methods=['GET'])
def backup_database():
    """データベースをスプレッドシートにバックアップするエンドポイント
    """
    res, code = db_group.backup_to_gas()
    res2, code2 = db_bot.backup_to_gas()
    message = f"group info: {res} - {code}    bot info: {res2} - {code2}"
    code = 200 if code == 200 and code2 == 200 else 500
    logger.info("%s-%d", message, code)
    return message, code


@app.route('/pushMessage/', methods=['POST'])
def webhookMsg():
    """
    互換性の観点からエンドポイント名がpushMessageとなっているが、
    実際にはDiscordWebhookを利用してメッセージを送信するエンドポイント.
    """

    # コマンドを取得
    request_json: dict = request.get_json()
    cmd = request_json.get("cmd")  # lineWebhookのコマンドと同じ形式
    if cmd is None:
        logger.error("No cmd in request")
        return "error", 400
    cmd = cmd.lstrip("!")

    cmd = [c for c in Commands.registry if c.text == cmd]
    if len(cmd) == 0:
        logger.error("Command not found: %s", cmd)
        return "error", 400

    result = cmd[0].process("INTERACTIONS")
    if result:
        return "finish", 200
    else:
        return "error", 400
