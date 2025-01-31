from flask import Flask, request
import os
import base64
import hashlib
import hmac

import requests
import time
import threading

from linebot import LineBotApi
from linebot.models import TextSendMessage

from bubble_msg import taskBubbleMsg
import messages

# ローカル開発の場合.envファイルから環境変数を読み込む
from dotenv import load_dotenv
load_dotenv()   

CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

# Flaskのインスタンスを作成
app = Flask(__name__)

# サーバー停止を阻止し常時起動させるスクリプト
SERVER_BOOT = False

# 定期的にbootエンドポイントにアクセスするスクリプト
def bootServer():
    global SERVER_BOOT
    if SERVER_BOOT:
        return
    SERVER_BOOT = True

    # threadsで実行するための処理
    def inner():
        while True:
            url = "https://amaotowebhook.onrender.com/boot"
            requests.post(url)
            time.sleep(60 * 5)
        
    thread = threading.Thread(target=inner)
    thread.start()

# サーバーを起動させるためのエンドポイント
@app.route('/boot', methods=['POST'])
def boot():
    print("boot")
    return "boot"


@app.route('/')
def hello_world():
    return 'Hello, World!'

# lineWebhook用のエンドポイント
@app.route('/lineWebhook', methods=['POST'])
def lineWebhook():
    # 初回起動時にサーバーを常時するスクリプトを起動させる
    bootServer()
    
    # リクエストボディーを取得
    body = request.get_data(as_text=True)
    # 署名の検証
    hash = hmac.new(CHANNEL_SECRET.encode('utf-8'),
    body.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hash)

    # リクエストがLINE Platformから送信されたものか検証
    if signature != request.headers['X-Line-Signature']:
        return 'Unauthorized', 401
    
    # リクエストボディーをJSONに変換
    request_json = request.get_json()

    # ユーザーからのメッセージを取得
    message:str = request_json['events'][0]['message']['text']

    if message.startswith("引き継ぎ資料") or message.startswith("引継ぎ資料"):
        # コマンドに変換
        message = "!handover"

    if not message.startswith("!"):
        return # コマンドではない場合何もせずに終了
    
    # リプライトークンを取得
    reply_token = request_json['events'][0]['replyToken']
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
    
    cmd = message.split()[0][1:]
    # コマンドの処理
    if cmd == 'handover':
        # リプライトークンを用いて返信
        line_bot_api.reply_message(
            reply_token, TextSendMessage(text=messages.HANDOVER)
        )
    elif cmd == 'hello':
        # リプライトークンを用いて返信
        line_bot_api.reply_message(reply_token, TextSendMessage(text='Hello, World!'))
    else:
        # リプライトークンを用いて返信
        line_bot_api.reply_message(reply_token, TextSendMessage(text= messages.CMD_ERROR))


# プッシュメッセージ送信用のエンドポイント
@app.route('/pushMessage', methods=['POST'])
def pushMessage():
    
    # プッシュメッセージを送信
    request_json = request.get_json()
    target_group_id = request_json['target_group_id']
    msg_type = request_json['msg_type']
    msg_data = request_json['msg_data']



    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)

    # タスクリマインダーの場合バブルメッセージを送信
    if msg_type == 'task':
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        task_bubble_msg = taskBubbleMsg()
        task_bubble_msg.addReminder(*msg_data) # TODO エディタ上でエラーが出ない程度に適当に書いてる
        msg = task_bubble_msg.getMessages()



        line_bot_api.push_message(target_group_id,msg)
    else: # TODO とりあえず適当にメッセージを送信してる
        message = "test message"
        line_bot_api.push_message(target_group_id, TextSendMessage(text=message)) 

# 動作テスト用エンドポイント
@app.route("/test")
def test():
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
    
    group_id = os.getenv("TEST_GROUP_ID")

    task_bubble_msg = taskBubbleMsg()
    task_bubble_msg.addReminder("舞台監督", "foo", "01/10", 4, "台本", "memo", "hoge") # TODO エディタ上でエラーが出ない程度に適当に書いてる
    msg = task_bubble_msg.getMessages()



    line_bot_api.push_message(group_id,msg)# TODO msgの指定方法が正しいか不明


    return "finish"





if __name__ == '__main__':
    app.run(debug=True)
    