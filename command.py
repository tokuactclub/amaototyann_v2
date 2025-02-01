from linebot import LineBotApi
from linebot.models import TextSendMessage
import messages
import requests
from pprint import pprint
from datetime import datetime, timezone, timedelta

from bubble_msg import taskBubbleMsg
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

            # リマインダー対象のイベントを取得
            result_events = []
            for event in events:
                # 終了しているものは除外
                if event["finish"] == "true":
                    continue

                # 日時の差分を計算
                day_difference = self._calculate_date_difference(event["date"])
                if day_difference < 0:
                    continue

                # 差分がremindDateに含まれればリマインダー対象
                if str(day_difference) in event["remindDate"].split(","):
                    # dateをMM/DDに変換
                    event["date"] = datetime.fromisoformat(event["date"].rstrip("Z")).strftime("%m/%d")
                    event["last_days"] = day_difference
                    result_events.append(event)

            # バブルメッセージを作成
            msg_task = taskBubbleMsg()
            for event in result_events:
                msg_task.addReminder(
                    job=event["job"],
                    person=event["person"],
                    deadline=event["date"],
                    last_days=event["last_days"],
                    task=event["task"],
                    memo=event["memo"],
                    id=event["id"],
                )
            # メッセージを送信
            self.line_bot_api.reply_message(
                self.reply_token,
                msg_task.getMessages()
            )
        except Exception as e:
            print(e)

    def _reply_text_message(self, text):
        self.line_bot_api.reply_message(
            self.reply_token, TextSendMessage(text=text)
            )
    
    def _calculate_date_difference(iso_datetime: str, tz_offset_hours: int = 0):
        """指定の日時と現在の日時の差分を計算する

        Args:
            iso_datetime (str): ISO 8601 形式の日時文字列. 例: "2021-01-01T00:00:00Z"
            tz_offset_hours (int, optional): タイムゾーンのオフセット（時間）. Defaults to 0.

        Returns:
            _type_: 日数の差分
        """
        # ISO 8601 の日時文字列を UTC の datetime に変換
        dt = datetime.fromisoformat(iso_datetime.rstrip("Z")).replace(tzinfo=timezone.utc)

        # 指定されたタイムゾーンのオフセットを適用
        tz = timezone.utc if tz_offset_hours == 0 else timezone(timedelta(hours=tz_offset_hours))
        local_date = dt.astimezone(tz).date()

        # 現在の日付（指定のタイムゾーン）
        today = datetime.now(tz).date()

        # 日数の差分を計算
        day_difference = (local_date - today).days

        return day_difference


if __name__ == "__main__":
    Commands("channel_access_token", "reply_token").process("!reminder")