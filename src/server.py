from flask import Flask, request
import os

import requests
import time
import threading

from linebot import LineBotApi
import json

from src.bubble_msg import taskBubbleMsg
from src.command import Commands, CommandsScripts
from src.system import BotInfo
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
BOT_INFOS = BotInfo()
BOT_INFOS.fetch()



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

def react_message_webhook(request, channel_access_token, gpt_url, event_index):
    print("got react message webhook")
    # リクエストボディーをJSONに変換
    request_json = request.get_json()
    
    message:str = request_json['events'][event_index]['message']['text']

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
    Commands(channel_access_token, request= request).process(message)

    return

def react_join_webhook(request, channel_access_token, bot_name, event_index):
    print("got join webhook")
    botId = int(request.args.get("botId"))
    # リクエストボディーをJSONに変換
    request_json = request.get_json()
    
    # グループの人数を取得
    line_bot_api = LineBotApi(channel_access_token)
    group_id = request_json['events'][event_index]['source']['groupId']
    group_member_count = line_bot_api.get_group_members_count(group_id)
    
    # 残り送信可能なメッセージ数を取得
    remaining_message_count = line_bot_api.get_message_quota()

    # 残り送信可能な回数を計算(小数点以下切り捨て)
    remaining_message_count = remaining_message_count // group_member_count
    
    LineBotApi(channel_access_token).reply_message(
        request_json['events']['replyToken'],
        f"""{bot_name}がグループに参加したよ！
        今月残り{remaining_message_count}回メッセージを送れるよ！
        返信はカウントされないから安心してね！"""
    )

    # 参加したグループがリマインド対象のグループであればdatabaseを更新
    # リマインド対象のグループIDを取得 
    group_info = requests.post(
                GAS_URL,
                json={"cmd":"getGroupInfo"}
                ).json()
            
    TARGET_GROUP_ID = group_info["id"]

    # リマインド対象のグループIDと一致する場合
    if group_id == TARGET_GROUP_ID:
        # リマインド対象のグループに参加したことを記録
        BOT_INFOS[botId][4] = True
        BOT_INFOS.send()
    return

# lineWebhook用のエンドポイント
@app.route('/lineWebhook', methods=['POST'])
def lineWebhook():
    print("got LINE webhook")
    # ウェブフックを送信してきたアカウントを?botId=で取得
    botId = int(request.args.get("botId"))

    # botIdからbotの情報を取得
    BOT_INFOS.fetch()
    bot_name = BOT_INFOS[botId][0]
    channel_access_token = BOT_INFOS[botId][1]
    gpt_url = BOT_INFOS[botId][3]


    # ユーザーからのメッセージを取得
    for i,event in enumerate(request.get_json()['events']):
        if event['type'] == 'message': # メッセージイベント
            react_message_webhook(request, channel_access_token, gpt_url, i)
        elif event['type'] == 'join': # グループ参加イベント
            react_join_webhook(request, channel_access_token, bot_name, i)

    return "finish", 200

# プッシュメッセージ送信用のエンドポイント
@app.route('/pushMessage', methods=['POST'])
def pushMessage():
    use_account = [account for account in BOT_INFOS if account[4] == True]
    if len(use_account) == 0:
        return "error", 400
    use_account = use_account[0]
    channel_access_token = use_account[1]

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
    use_account = [account for account in BOT_INFOS if account[4] == True]
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
    app.run(debug=True)
    