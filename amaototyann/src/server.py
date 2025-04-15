from flask import Flask, request, Response # type: ignore
import os
import requests # type: ignore
import time
import threading

from linebot import LineBotApi # type: ignore
from linebot.models import TextSendMessage # type: ignore

from amaototyann.src.command import Commands, CommandsScripts
from amaototyann.src.system import transcribeWebhook
from amaototyann.src import messages, logger
from amaototyann.src import db_bot, group_info_manager


GAS_URL = os.getenv('GAS_URL')


# gasから取得する
BOT_INFOS = db_bot


# サーバー停止を阻止し常時起動させるスクリプト
# 同時にデータベースのバックアップを行う

# threadsで実行するための処理
def boot_server():
    server_url = os.getenv("SERVER_URL")
    while True:
        try:
            url = os.path.join(server_url, "backupDatabase/")
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

# databaseをスプレッドシートにバックアップするためのスクリプト
@app.route('/backupDatabase/', methods=['GET'])
def backup_database():
    res, code = group_info_manager.backup_to_gas()
    res2, code2 = db_bot.backup_to_gas()
    return ("success", 200) if code == 200 and code2 == 200 else ("error", 500)
  
@app.route('/')
def hello_world():
    # app.logを返す
    with open("amaototyann/logs/app.log", "r") as f:
        log = f.read()
    return Response(log, mimetype='text/plain')

def react_message_webhook(request, botId, event_index):
    logger.info("got react message webhook")
    # リクエストボディーをJSONに変換
    request_json = request.get_json()
    bot_info = BOT_INFOS.get_row(botId)
    channel_access_token = bot_info["channel_access_token"]
    gpt_url = bot_info["gpt_webhook_url"]
    
    message:str = request_json['events'][event_index]['message']['text']

    # 引継ぎ資料がメッセージに含まれる場合コマンドに変換
    if message.startswith("引き継ぎ資料") or message.startswith("引継ぎ資料"):
        message = CommandsScripts.HANDOVER

    debug = request_json.get("debug", False) 
        
    # チャットボット機能の際は転送
    if message.startswith("あまおとちゃん") and not debug:
        for _ in range(3):
            response = transcribeWebhook(request,gpt_url)
            if response[1] == 200:
                return "finish", 200
            time.sleep(0.5)
        return "error", 200 # エラーだが、ここはLINEのサーバーに応答する都合上200を返す
    
    # 全角の！を半角に変換
    message = message.replace("！", "!")

    if not message.startswith("!"):
        return "finish", 200
    logger.info("start command process")
    # コマンド処理

    Commands(channel_access_token, request= request, botId=botId, debug= debug).process(message)

    return

def react_join_webhook(request, botId, event_index):
    logger.info("got join webhook")
    # リクエストボディーをJSONに変換
    request_json = request.get_json()

    bot_info = BOT_INFOS.get_row(botId)
    channel_access_token = bot_info["channel_access_token"]
    bot_name = bot_info["bot_name"]

    debug = request_json.get("debug", False) 

    if debug:
        remaining_message_count = 200
        event = request_json['events'][event_index]
        group_id = event['source']['groupId']
        logger.info(messages.JOIN.format(bot_name, remaining_message_count))
    else:
        # グループの人数を取得
        line_bot_api = LineBotApi(channel_access_token)
        event = request_json['events'][event_index]
        group_id = event['source']['groupId']
        group_member_count = line_bot_api.get_group_members_count(group_id)
        
        # 残り送信可能なメッセージ数を取得
        remaining_message_count = line_bot_api.get_message_quota().value

        # 残り送信可能な回数を計算(小数点以下切り捨て)
        remaining_message_count = remaining_message_count // group_member_count
    
        line_bot_api.reply_message(
            event['replyToken'],
            TextSendMessage(text= messages.JOIN.format(bot_name, remaining_message_count))
        )

    # 参加したグループがリマインド対象のグループであればdatabaseを更新
    # リマインド対象のグループIDを取得 
    TARGET_GROUP_ID = group_info_manager.group_id
    logger.info(f"target group id: {TARGET_GROUP_ID}\n, group id: {group_id}")

    # リマインド対象のグループIDと一致する場合
    if group_id == TARGET_GROUP_ID:
        # リマインド対象のグループに参加したことを記録
        BOT_INFOS.update_value(botId, "in_group", True)
    return


# lineWebhook用のエンドポイント
@app.route('/lineWebhook/<botId>/', methods=['POST'])
def lineWebhook(botId):
    logger.info("got LINE webhook, webhook type is on next line")
    botId = int(botId)
    # ユーザーからのメッセージを取得
    for i,event in enumerate(request.get_json()['events']):
        if event['type'] == 'message': # メッセージイベント
            react_message_webhook(request, botId, i)

        elif event['type'] == 'join': # グループ参加イベント
            react_join_webhook(request, botId, i)

        elif event['type'] == 'leave': # グループ退出イベント
            logger.info("got left webhook")    
            # グループから抜けたことを記録
            BOT_INFOS.update_value(botId, "in_group", False)
          
        else:
            logger.info("not valid webhook type") 

    return "finish", 200

# プッシュメッセージ送信用のエンドポイント
@app.route('/pushMessage/', methods=['POST'])
def pushMessage():
    use_account = [account for account in BOT_INFOS.list_rows() if account["in_group"] == True]
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
    use_account = [account for account in BOT_INFOS.list_rows() if account["in_group"] == True]
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
