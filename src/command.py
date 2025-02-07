from linebot import LineBotApi
from linebot.models import TextSendMessage
import requests
from pprint import pprint
from datetime import datetime, timezone, timedelta
import os

from src import messages
from src.bubble_msg import taskBubbleMsg
from src.system import BotInfo
GAS_URL = os.getenv('GAS_URL')

# コマンドの文字列を格納するクラス
class CommandsScripts:
    HELP = "!help"
    CHANGE_GROUP = "!changeGroup"
    REMINDER = "!reminder"
    PRACTICE = "!practice"
    PLACE = "!place"
    HANDOVER = "!handover"
    HELLO = "!hello"
    FINISH = "!finish"
class Commands(object):
    def __init__(self,channel_access_token, request= None, debug=False):
        """基本的にwebhookのコマンドを処理し、リプライメッセージで応答する。
        ただし一部関数はwebhookを介さずともpushメッセージにより対応する。

        Args:
            channel_access_token (str): linebotのチャンネルアクセストークン
            request (): webhookで受け取ったrequestそのもの
            debug (bool, optional): デバッグモードかどうか
        """
        webhook_body = request.get_json()
        self.botId = int(request.args.get("botId"))

        if webhook_body is not None:
            self.webhook_body = webhook_body
            reply_token = webhook_body['events'][0]['replyToken']
            self.reply_token = reply_token
        else:
            group_info = requests.post(
                GAS_URL,
                json={"cmd":"getGroupInfo"}
                ).json()
            
            self.TARGET_GROUP_ID = group_info["id"]

        self.debug = debug
        if debug:
            self.line_bot_api = None
        else:
            self.line_bot_api = LineBotApi(channel_access_token)
        
    def process(self, cmd):
        """コマンドを処理する。
        Args:
            cmd (str): !から始まるコマンド
        """
        self._command_process(cmd)
    
    def _command_process(self, cmd:str):
        """コマンドの処理を行う

        Args:
            cmd (str): !から始まるコマンド
        """
        commands = cmd.split()
        cmd = commands[0]
        if cmd == CommandsScripts.HELP:
            self._send_text_message(messages.HELP)

        elif cmd == CommandsScripts.CHANGE_GROUP:
            self._change_group()
            
        elif cmd == CommandsScripts.REMINDER:
            self._reminder()

        elif cmd == CommandsScripts.PRACTICE:
            self._practice()

        elif cmd == CommandsScripts.PLACE:
            # TODO 活動場所メッセージ送信
            # 現在登録機構がないためpass
            pass

        elif cmd == CommandsScripts.HANDOVER:
            self._send_text_message(messages.HANDOVER)

        elif cmd == CommandsScripts.HELLO:
            self._send_text_message('Hello, World!')
        elif cmd == CommandsScripts.FINISH:
            self._finish_event(id=commands[1])
        else:
            self._send_text_message(messages.CMD_ERROR)
            return False
        return True


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
            print(events)
            if len(events)>0:
                self._send_text_message("\n\n".join(events))
            else:
                self._send_text_message(messages.NO_PRACTICE)
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
                day_difference = self._calculate_date_difference( event["date"])
                if day_difference < 0:
                    continue

                # 差分がremindDateに含まれればリマインダー対象
                if str(day_difference) in event["remindDate"].split(","):
                    # dateをMM/DDに変換
                    event["date"] = datetime.fromisoformat(event["date"].rstrip("Z")).strftime("%m/%d")
                    event["last_days"] = day_difference
                    result_events.append(event)
            # リマインド対象がなければその旨を送信
            if len(result_events) == 0:
                self._send_text_message(messages.NONE_REMIND_TASK)
                return
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

    def _finish_event(self, id):
        try:
            response = requests.post(
                GAS_URL,
                json={"cmd":"finish","options":{"id":id}},
                )
            task_name = response.text
            if task_name != "error":
                self._send_text_message(f"{task_name}の通知を終わるよ！")
            else:
                self._send_text_message("エラーで通知を終われなかったよ！ごめんね！")
        except Exception as e:
            print(e)
    
    def _change_group(self):
        group_id = self.webhook_body['events'][0]['source']['groupId']
        print(f"change group: {group_id}")

        # group_id から lineのapiでgroup_name を取得
        group_name = self.line_bot_api.get_group_summary(group_id).group_name

        result = requests.post(
            GAS_URL,
            json={
                "cmd":"changeGroup",
                "options":{
                    "id":group_id,
                    "groupName":group_name,
                    "botId":self.botId
                }
            }
        ).text
        if result == "error":
            self._send_text_message("エラーが発生しました")
            return
        
        self._send_text_message(messages.CHANGE_GROUP)

    def _send_text_message(self, text):
        if self.debug:
            print(text)
        elif self.reply_token is None:
            self.line_bot_api.push_message(
                self.TARGET_GROUP_ID, TextSendMessage(text=text)
            )
        else:
            self.line_bot_api.reply_message(
                self.reply_token, TextSendMessage(text=text)
            )
    def _send_bubble_message(self, bubble):
        if self.debug:
            pprint(bubble)
        elif self.reply_token is None:
            self.line_bot_api.push_message(
                self.TARGET_GROUP_ID, bubble
            )
        else:
            self.line_bot_api.reply_message(
                self.reply_token, bubble
            )
    
    def _calculate_date_difference(self, iso_datetime: str, tz_offset_hours: int = 0):
        """指定の日時と現在の日時の差分を計算する

        Args:
            iso_datetime (str): ISO 8601 形式の日時文字列. 例: "2021-01-01T00:00:00Z"
            tz_offset_hours (int, optional): タイムゾーンのオフセット（時間）. Defaults to 0.

        Returns:
            _type_: 日数の差分
        """
        assert type(iso_datetime) == str, f"iso_datetime must be str, but got {type(iso_datetime)}"
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
    Commands("test", "test",debug=True).process("!reminder")