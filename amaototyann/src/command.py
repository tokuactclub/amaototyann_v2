from linebot import LineBotApi 
from linebot.models import TextSendMessage 
import requests 
from datetime import datetime, timezone, timedelta
import os
import json

from amaototyann.src.bubble_msg import taskBubbleMsg
from amaototyann.src import messages
from amaototyann.src import db_bot, db_group
from amaototyann.src import IS_DEBUG_MODE
GAS_URL = os.getenv('GAS_URL')

# loggerの設定
from logging import getLogger, config
with open("amaototyann/src/log_config.json", "r") as f:
    config.dictConfig(json.load(f))
logger = getLogger("logger")


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
    YOUTUBE = "!youtube"
    INSTAGRAM = "!instagram"
    TWITTER = "!twitter"
    HOMEPAGE = "!homepage"
class Commands(object):
    def __init__(self, channel_access_token, request, botId=None):
        """基本的にwebhookのコマンドを処理し、リプライメッセージで応答する。
        ただし一部関数はwebhookを介さずともpushメッセージにより対応する。

        Args:
            channel_access_token (str): linebotのチャンネルアクセストークン
            request (bool, optional): webhookやpostで受け取ったrequestそのもの
            botId (str, optional): botのID. messageからコマンドを実行する際必要
        """
        logger.info(f"run Commands in {'debug' if IS_DEBUG_MODE else 'normal'} mode")

        body_json = request.get_json()
        self.is_webhook_request = bool(body_json.get("events"))
        if self.is_webhook_request:
            self.webhook_body = body_json
        
        if self.is_webhook_request:  # requestがwebhookの場合
            logger.info("webhook request")
            self.botId = int(botId)
            self.reply_token = self.webhook_body['events'][0]['replyToken']
        else:
            logger.info("push message")
            self.TARGET_GROUP_ID = db_group.group_id()
            logger.info(f"target group id: {self.TARGET_GROUP_ID}\nchannel_access_token: {channel_access_token}")

        self.line_bot_api = LineBotApi(channel_access_token)
        
    def process(self, cmd):
        """コマンドを処理する。
        Args:
            cmd (str): !から始まるコマンド
        """
        return self._command_process(cmd)
    
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

        elif cmd == CommandsScripts.YOUTUBE:
            self._send_text_message(messages.YOUTUBE)

        elif cmd == CommandsScripts.INSTAGRAM:
            self._send_text_message(messages.INSTAGRAM)

        elif cmd == CommandsScripts.TWITTER:
            self._send_text_message(messages.TWITTER)

        elif cmd == CommandsScripts.HOMEPAGE:
            self._send_text_message(messages.HOMEPAGE)
            
        else:
            self._send_text_message(messages.CMD_ERROR)
            logger.error(f"command not found: {cmd}")
            return False
        return True


    def _practice(self):
        try:
            response = requests.post(
                GAS_URL,
                json={"cmd":"practice"},
                )
            logger.info(f"response: {response}")
            events = response.json()
            logger.info(f"events: {events}")
            try:
                events = list(map(
                    lambda x: messages.PRACTICE.format(x["place"], x["start"].split()[3][:-3], x["end"].split()[3][:-3], "\n" + x["memo"] if x["memo"] else ""),
                    events
                    ))

            # GASのタイム表記の移行に伴う例外処理
            except Exception as e:
                events = list(map(
                    lambda x: messages.PRACTICE.format(x["place"], x["start"], x["end"], "\n" + x["memo"] if x["memo"] else ""),
                    events
                    ))
            logger.info(events)
            if len(events)>0:
                self._send_text_message("\n\n".join(events))
            elif self.is_webhook_request:
                self._send_text_message(messages.NO_PRACTICE)
        except Exception as e:
            logger.exception(e)

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
                day_difference = self._calculate_date_difference( event["date"], tz_offset_hours=9)
                if day_difference < 0:
                    continue

                # 差分がremindDateに含まれればリマインダー対象
                if str(day_difference) in event["remindDate"].split(","):
                    # dateをMM/DDに変換
                    event["date"] = datetime.fromisoformat(event["date"].rstrip("Z")).strftime("%m/%d")
                    event["last_days"] = day_difference
                    result_events.append(event)
            # リマインド対象がなければその旨を送信
            if len(result_events) == 0 and self.is_webhook_request:
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
            self._send_bubble_message(msg_task.getMessages())
        except Exception as e:
            logger.exception(e)

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
            logger.exception(e)
    
    def _change_group(self):
        group_id = self.webhook_body['events'][0]['source']['groupId']
        logger.info(f"change group: {group_id}")

        # group_id から lineのapiでgroup_name を取得
        if not IS_DEBUG_MODE:
            group_name = self.line_bot_api.get_group_summary(group_id).group_name
        else:
            group_name = "test_group_name"

        # group_infoを更新
        db_group.set_group_info(group_id, group_name)

        # bot_infoを更新
        # in_groupカラムを、bot_idのrowだけTrue,それ以外はFalseにする
        for row in db_bot.list_rows():
            if row["id"] == self.botId:
                db_bot.update_value(row["id"], "in_group", True)
            else:
                db_bot.update_value(row["id"], "in_group", False)

        
        self._send_text_message(messages.CHANGE_GROUP)

    def _send_text_message(self, text):
        if IS_DEBUG_MODE:
            logger.info(f"[DEBUG MODE] Message: {text}")
        elif self.is_webhook_request:
            self.line_bot_api.reply_message(
                self.reply_token, TextSendMessage(text=text)
            )
        else:
            self.line_bot_api.push_message(
                self.TARGET_GROUP_ID, TextSendMessage(text=text)
            )
    def _send_bubble_message(self, bubble):
        if IS_DEBUG_MODE:
            logger.info(f"[DEBUG MODE] Bubble Message: {bubble}")
        elif self.is_webhook_request:
            self.line_bot_api.reply_message(
                self.reply_token, bubble
            )
        else:
            self.line_bot_api.push_message(
                self.TARGET_GROUP_ID, bubble
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
    Commands(channel_access_token="test",request="test", debug=True).process("!reminder")