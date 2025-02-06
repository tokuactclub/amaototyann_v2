from flask import Flask, request
import os

import requests
import time
import threading

from linebot import LineBotApi
import json

from src.bubble_msg import taskBubbleMsg
from src.command import Commands, CommandsScripts

# ローカル開発の場合.envファイルから環境変数を読み込む
# IS_RENDER_SERVER が存在しない場合はローカル開発と判断
if not os.getenv("IS_RENDER_SERVER"):
    from dotenv import load_dotenv
    load_dotenv()   

GAS_URL = os.getenv('GAS_URL')

# botの情報を取得する.以下の形式の二次元配列である。詳細はスプレッドシート参照
# bot_name, channnel_access_token, channel_secret, gpt_webhook_url, in_group
# [ [ 'あまおとちゃん', '', '', '', false ],
#   [ 'あまおとくん', '', '', '', false ],
#   [ 'あまおとママ', '', '', '', false ],
#   [ 'あまおとパパ', '', '', '', false ] ]

# gasから取得する
BOT_INFOS = requests.post(
                GAS_URL,
                json={"cmd":"getBotInfo"}
                ).json()



# サーバー停止を阻止し常時起動させるスクリプト
# 定期的にbootエンドポイントにアクセスする

# threadsで実行するための処理
def boot_server():
    while True:
        try:
            url = "https://amaotowebhook.onrender.com/boot"
            requests.post(url)
        except Exception as e:
            print(e)
        time.sleep(60 * 5)
server_boot_script_running = os.getenv("SERVER_BOOT_SCRIPT_RUNNING")
if  not server_boot_script_running or server_boot_script_running == "False":
    # 別ワーカーで実行されていない場合のみ起動
    os.environ["SERVER_BOOT_SCRIPT_RUNNING"] = "True"
    thread = threading.Thread(target=boot_server)
    thread.start()

# webhookを転送する関数
def transcribeWebhook(request, url, body=None):
    """webhookを転送する関数

    Args:
        request (Request): リクエスト
        url (str): 転送先のURL
        body (dict, optional): リクエストボディを変えたい場合指定

    Returns:
        Response: 転送先からのレスポンス
    """
    method = request.method
    print(f"headersType:{type(request.headers)}")
    headers = {key: value for key, value in dict(request.headers).items() if key != 'Host'} 
    if(not body):#bodyを指定されなければeventのbodyを利用（本来の挙動）
        body = request.json

    print(f"Method: {method}Type:{type(method)}")
    print(f"URL : {url}Type:{type(url)}")
    print(f"Headers: {headers}Type:{type(headers)}")
    print(f"Body: {body}Type:{type(body)}")

    try:
        # Reconstruct headers and forward the request
        headers["Content-Type"] = "application/json;charset=utf-8"
        response = requests.request(
            method=method,
            url=url,
            headers=json.loads(json.dumps(headers)),
            json=json.loads(json.dumps(body)),
        )

        print('Forwarded Data:', response)
        print('HTTP Status Code:', response.status_code)

        return 'Data forwarded successfully', 200
    except Exception as e:
        print('Error:', e)
        return 'Failed to forward data', 500

    
# Flaskのインスタンスを作成
app = Flask(__name__)

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
    # ウェブフックを送信してきたアカウントを?botId=で取得
    botId = int(request.args.get("botId"))

    # botIdからbotの情報を取得
    channel_access_token = BOT_INFOS[botId][1]
    gpt_url = BOT_INFOS[botId][3]


    # リクエストボディーをJSONに変換
    request_json = request.get_json()
    
    # ユーザーからのメッセージを取得
    for event in request_json['events']:
        if event['type'] != 'message': # メッセージ以外のイベントは無視
            continue
        message:str = event['message']['text']

        # 引継ぎ資料がメッセージに含まれる場合コマンドに変換
        if message.startswith("引き継ぎ資料") or message.startswith("引継ぎ資料"):
            message = CommandsScripts.HANDOVER
            
        # チャットボット機能の際は転送
        if message.startswith("あまおとちゃん"):
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
        print("start command process")
        
        # コマンド処理
        Commands(channel_access_token, webhook_body= request_json).process(message)

    return "finish", 200

# プッシュメッセージ送信用のエンドポイント
@app.route('/pushMessage', methods=['POST'])
def pushMessage():
    # メッセージ送信に使うアカウントを?botId=で取得
    botId = int(request.args.get("botId"))
    channel_access_token = BOT_INFOS[botId][1]
    
    # プッシュメッセージを送信
    request_json = request.get_json()
    cmd = request_json['cmd'] # lineWebhookのコマンドと同じ形式 

    # コマンド処理

    result = Commands(channel_access_token).process(cmd)
    if result:
        return "finish", 200
    else:
        return "error", 400

# 動作テスト用エンドポイント
@app.route("/test")
def test():
    line_bot_api = LineBotApi(BOT_INFOS[1][1])
    
    group_id = os.getenv("TEST_GROUP_ID")

    task_bubble_msg = taskBubbleMsg()
    task_bubble_msg.addReminder("舞台監督", "foo", "01/10", 4, "台本", "memo", "hoge") # TODO エディタ上でエラーが出ない程度に適当に書いてる
    msg = task_bubble_msg.getMessages()



    line_bot_api.push_message(group_id,msg)# TODO msgの指定方法が正しいか不明


    return "finish"





if __name__ == '__main__':
    app.run(debug=True)
    