from linebot import LineBotApi
from linebot.models import TextSendMessage
import messages
import requests
from pprint import pprint
GAS_URL = "https://script.google.com/macros/s/AKfycby8acn6-HFL9snjXpYp1bK8S8Ju7w6WR4la6znsMjJNpvsDLSnZl0D-UtyfG2P_o1JL/exec"
class Commands(object):
    def __init__(self,channel_access_token, reply_token):
        """_summary_

        Args:
            channel_access_token (str): linebotのチャンネルアクセストークン
            reply_token (str): webhookで受け取ったリプライトークン
        """
        
        self.line_bot_api = None
        # self.line_bot_api = LineBotApi(channel_access_token)
        self.reply_token = reply_token
        
    def process(self, cmd):
        """コマンドを処理する。
        Args:
            cmd (str): !から始まるコマンド
        """
        self._command_process(cmd)
    
    def _command_process(self, cmd):
        """コマンドの処理を行う

        Args:
            cmd (str): !から始まるコマンド
        """
        cmd = cmd.split()[0][1:] # !を取り除く
        if cmd == 'help':
            self._reply_text_message(messages.HELP)

        elif cmd == 'change_group':
            # TODO グループ変更処理
            self.line_bot_api.reply_message(
                self.reply_token, TextSendMessage(text=messages.CHANGE_GROUP)
            )
        elif cmd == 'reminder':
            self._reminder()

        elif cmd == 'practice':
            self._practice()

        elif cmd == 'place':
            # TODO 活動場所メッセージ送信
            # 現在登録機構がないためpass
            pass

        elif cmd == 'handover':
            self.line_bot_api.reply_message(
                self.reply_token, TextSendMessage(text=messages.HANDOVER)
            )
        elif cmd == 'hello':
            self._reply_text_message('Hello, World!')
        else:
            self._reply_text_message(messages.CMD_ERROR)


    def _practice(self):
        try:
            response = requests.post(
                GAS_URL,
                json={"cmd":"practice"},
                )
            events = response.json()

            events = map(
                lambda x: messages.PRACTICE.format(x["place"], x["start"], x["end"], x["memo"]),
                events
                )
            events = list(events)
            if len(events)>0:
                self._reply_text_message(events.join("\n\n"))
            else:
                self._reply_text_message("今日の練習はありません")
        except Exception as e:
            print(e)
    def _reminder(self):
        try:
            response = requests.post(
                GAS_URL,
                json={"cmd":"reminder"},
                )
            events = response.json()
            pprint(events)
        except Exception as e:
            print(e)

    def _reply_text_message(self, text):
        self.line_bot_api.reply_message(
            self.reply_token, TextSendMessage(text=text)
            )


if __name__ == "__main__":
    Commands("channel_access_token", "reply_token").process("!reminder")