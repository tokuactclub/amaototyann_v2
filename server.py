from flask import Flask, request
import os
import base64
import hashlib
import hmac

from linebot import LineBotApi
from linebot.models import TextSendMessage
from bubble_msg import taskBubbleMsg
# ローカル開発の場合.envファイルから環境変数を読み込む
from dotenv import load_dotenv
load_dotenv()   

CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')

# Flaskのインスタンスを作成
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'

# lineWebhook用のエンドポイント
@app.route('/lineWebhook', methods=['POST'])
def lineWebhook():
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
    message = request_json['events'][0]['message']['text']

    # メッセージがコマンドかどうか判定する
    if message.split()[0] != 'ama':
        return # コマンドではない場合何もせずに終了
    
    # リプライトークンを取得
    reply_token = request_json['events'][0]['replyToken']
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
    
    cmd = message.split()[1:]
    # コマンドの処理
    if cmd == 'ping':
        # リプライトークンを用いて返信
        line_bot_api.reply_message(reply_token, TextSendMessage(text='pong'))
    elif cmd == 'hello':
        # リプライトークンを用いて返信
        line_bot_api.reply_message(reply_token, TextSendMessage(text='Hello, World!'))
    else:
        # リプライトークンを用いて返信
        line_bot_api.reply_message(reply_token, TextSendMessage(text='コマンドが見つかりませんでした'))


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



        line_bot_api.push_message(target_group_id,msg)# TODO msgの指定方法が正しいか不明
    else: # TODO とりあえず適当にメッセージを送信してる
        message = "test message"
        line_bot_api.push_message(target_group_id, TextSendMessage(text=message)) 
if __name__ == '__main__':
    app.run(debug=True)