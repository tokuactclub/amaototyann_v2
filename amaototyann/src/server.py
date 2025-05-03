from flask import Flask, request, Response 
import os
import requests 
import time
import threading


from amaototyann.src.command import Commands
from amaototyann.src import logger, db_bot, db_group, integrate_flask_logger
from amaototyann.src.react_webhook import react_message_webhook, react_join_webhook, react_leave_webhook

GAS_URL = os.getenv('GAS_URL')


# サーバー停止を阻止し常時起動させるスクリプト
# 同時にデータベースのバックアップを行う

# threadsで実行するための処理
def boot_server():
    server_url = os.getenv("SERVER_URL")
    while True:
        try:
            url = os.path.join(server_url, "backupDatabase/")
            logger.info(f"===boot server===send backup request: {url}")
            requests.get(url)
        except Exception as e:
            logger.error(e)
        time.sleep(60 * 3)
        # time.sleep(20)

server_boot_script_running = os.getenv("SERVER_BOOT_SCRIPT_RUNNING")
if  not server_boot_script_running or server_boot_script_running == "False":
    # 別ワーカーで実行されていない場合のみ起動
    os.environ["SERVER_BOOT_SCRIPT_RUNNING"] = "True"
    thread = threading.Thread(target=boot_server)
    thread.start()



    
# Flaskのインスタンスを作成
app = Flask(__name__)
app.strict_slashes = False
integrate_flask_logger(app)

# databaseをスプレッドシートにバックアップするためのスクリプト
@app.route('/backupDatabase/', methods=['GET'])
def backup_database():
    res, code = db_group.backup_to_gas()
    res2, code2 = db_bot.backup_to_gas()
    message = f"group info: {res} - {code}    bot info: {res2} - {code2}"
    code = 200 if code == 200 and code2 == 200 else 500
    logger.info(f"{message}-{code}")
    return message, code
  
@app.route('/')
def hello_world():
    # app.logを返す
    with open("amaototyann/logs/app.log", "r") as f:
        log = f.read()
    return Response(log, mimetype='text/plain')



# lineWebhook用のエンドポイント
@app.route('/lineWebhook/<botId>/', methods=['POST'])
def lineWebhook(botId):
    logger.info("got LINE webhook, webhook type is on next line")
    botId = int(botId)
    # ユーザーからのメッセージを取得
    for i,event in enumerate(request.get_json()['events']):
        if event['type'] == 'message' and event["message"]["type"] == "text": # textメッセージイベント
            react_message_webhook(request, botId, i)

        elif event['type'] == 'join': # グループ参加イベント
            react_join_webhook(request, botId, i)

        elif event['type'] == 'leave': # グループ退出イベント
            react_leave_webhook(request, botId, i)
            
          
        else:
            logger.info("not needed to react to this webhook") 
    return "finish", 200

# プッシュメッセージ送信用のエンドポイント
@app.route('/pushMessage/', methods=['POST'])
def pushMessage():
    use_account = [account for account in db_bot.list_rows() if account["in_group"] == True]
    if len(use_account) == 0:
        return "error", 400
    use_account = use_account[0]
    channel_access_token = use_account["channel_access_token"]

    # プッシュメッセージを送信
    request_json:dict = request.get_json()
    cmd = request_json.get("cmd") # lineWebhookのコマンドと同じ形式 
    if cmd is None:
        return "error cmd isn't defined", 400
    # コマンド処理

    result = Commands(channel_access_token, request=request).process(cmd)
    if result:
        return "finish", 200
    else:
        return "error", 400

# 動作テスト用エンドポイント
@app.route("/test")
def test():
    use_account = [account for account in db_bot.list_rows() if account["in_group"] == True]
    if len(use_account) == 0:
        return "error", 400
    use_account = use_account[0]
    channel_access_token = use_account[1]

    # プッシュメッセージを送信
    cmd = "!reminder" # lineWebhookのコマンドと同じ形式 

    # コマンド処理

    result = Commands(channel_access_token).process(cmd)
    if result:
        return "finish", 200
    else:
        return "error", 400





if __name__ == '__main__':
    app.run(debug=True, port = 8000)
