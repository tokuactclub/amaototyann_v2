from flask import Flask, request
import os

import requests
import time
import threading

from linebot import LineBotApi

from bubble_msg import taskBubbleMsg
from command import Commands

# ローカル開発の場合.envファイルから環境変数を読み込む
# IS_RENDER_SERVER が存在しない場合はローカル開発と判断
if not os.getenv("IS_RENDER_SERVER"):
    from dotenv import load_dotenv
    load_dotenv()   

CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
GP_URL = os.getenv('GP_URL')

# Flaskのインスタンスを作成
app = Flask(__name__)

# サーバー停止を阻止し常時起動させるスクリプト
SERVER_BOOT_SCRIPT_RUNNING = False

# 定期的にbootエンドポイントにアクセスするスクリプト
def bootServer():
    """サーバーを起動させ続ける。何度呼び出されても一度だけ処理を行う。
    """
    if SERVER_BOOT_SCRIPT_RUNNING:
        # 同一ワーカーで起動スクリプトが走っている場合
        # または別ワーカーで実行されており、それをすでに検知している場合
        return
    elif os.getenv("SERVER_BOOT_SCRIPT_RUNNING"):
        # 別ワーカーで実行されており、それを検知していない場合
        # 自身のワーカーに検知状態を保存
        SERVER_BOOT_SCRIPT_RUNNING = True
        return
    
    # 起動スクリプトが走っていない場合
    os.environ["SERVER_BOOT_SCRIPT_RUNNING"] = "True"
    SERVER_BOOT_SCRIPT_RUNNING = True
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
    print("got LINE webhook")
    # 初回起動時にサーバーを常時するスクリプトを起動させる
    bootServer()

    # リクエストボディーをJSONに変換
    request_json = request.get_json()
    
    # ユーザーからのメッセージを取得
    message:str = request_json['events'][0]['message']['text']

    # 引継ぎ資料がメッセージに含まれる場合コマンドに変換
    if message.startswith("引き継ぎ資料") or message.startswith("引継ぎ資料"):
        message = "!handover"
        
    # 全角の！を半角に変換
    message = message.replace("！", "!")

    if not message.startswith("!"):
        return "finish", 200
    print("start command process")
    
    # コマンド処理
    Commands(CHANNEL_ACCESS_TOKEN, webhook_body= request_json).process(message)

    return "finish", 200

# プッシュメッセージ送信用のエンドポイント
@app.route('/pushMessage', methods=['POST'])
def pushMessage():
    
    # プッシュメッセージを送信
    request_json = request.get_json()
    cmd = request_json['cmd'] # lineWebhookのコマンドと同じ形式 

    # コマンド処理

    result = Commands(CHANNEL_ACCESS_TOKEN).process(cmd)
    if result:
        return "finish", 200
    else:
        return "error", 400

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
    