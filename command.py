from linebot import LineBotApi
from linebot.models import TextSendMessage
import messages

def command_process(cmd, channel_access_token, reply_token):
    """コマンドの処理を行う

    Args:
        cmd (str): !から始まるコマンド
        channel_access_token (str): linebotのチャンネルアクセストークン
        reply_token (str): webhookで受け取ったリプライトークン
    """
    cmd = cmd.split()[0][1:] # !を取り除く
    line_bot_api = LineBotApi(channel_access_token)

    if cmd == 'help':
        line_bot_api.reply_message(
            reply_token, TextSendMessage(text=messages.HELP)
        )
    elif cmd == 'change_group':
        # TODO グループ変更処理
        line_bot_api.reply_message(
            reply_token, TextSendMessage(text=messages.CHANGE_GROUP)
        )
    elif cmd == 'reminder':
        # TODO リマインダー処理
        pass
    elif cmd == 'practice':
        # TODO 部活ある or ない メッセージ送信
        pass
    elif cmd == 'place':
        # TODO 部活場所メッセージ送信
        pass
    
    elif cmd == 'handover':
        line_bot_api.reply_message(
            reply_token, TextSendMessage(text=messages.HANDOVER)
        )
    elif cmd == 'hello':
        line_bot_api.reply_message(reply_token, TextSendMessage(text='Hello, World!'))
    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text= messages.CMD_ERROR))