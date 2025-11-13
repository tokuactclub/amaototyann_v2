
import time
from linebot import LineBotApi
from linebot.models import TextSendMessage
from amaototyann.src.command import Commands, CommandsScripts
from amaototyann.src import messages, logger, transcribeWebhook, IS_DEBUG_MODE, db_bot, db_group


class Converter(object):
    def __init__(self):
        self.Tcs_same_dic = {}
        self.Fcs_same_dic = {}
        self.Tcs_start_dic = {}
        self.Fcs_start_dic = {}

    def add_argument(self, key: list | str, value: str, condition="same", case_sensitive=False):
        if isinstance(key, str):
            key = [key]

        if case_sensitive:
            if condition == "same":
                self.Tcs_same_dic.update({k: value for k in key})
            elif condition == "start":
                self.Tcs_start_dic.update({k: value for k in key})
        else:
            if condition == "same":
                self.Fcs_same_dic.update({k.lower(): value for k in key})
            elif condition == "start":
                self.Fcs_start_dic.update({k.lower(): value for k in key})

    def convert(self, message: str) -> str:
        # 全ての条件を満たす場合、優先度はcase_sensitive > not_case_sensitive > start > not_case_sensitive_start
        # ただし、同じ条件であればcase_sensitiveが優先される
        if result := self.Tcs_same_dic.get(message):
            return result
        if result := self.Fcs_same_dic.get(message.lower()):
            return result

        for key, val in self.Tcs_start_dic.items():
            if message.startswith(key):
                return val
        for key, val in self.Fcs_start_dic.items():
            if message.lower().startswith(key):
                return val
        return message


def convert_jp_command(message: str) -> str:

    converter = Converter()
    converter.add_argument(["引き継ぎ資料", "引継ぎ資料", "ScrapBox", "ひきつぎしりょう", "すくらっぷぼっくす"], CommandsScripts.HANDOVER, condition="start")
    converter.add_argument(["Youtube", "ユーチューブ", "ようつべ"], CommandsScripts.YOUTUBE, condition="same")
    converter.add_argument(["Instagram", "インスタグラム", "いんすたぐらむ", "インスタ", "いんすた"], CommandsScripts.INSTAGRAM, condition="same")
    converter.add_argument(["Twitter", "ツイッター", "ついったー", "X", "エックス", "えっくす"], CommandsScripts.TWITTER, condition="same")
    converter.add_argument(["ホームページ", "HP", "ほーむぺーじ"], CommandsScripts.HOMEPAGE, condition="same")

    message = converter.convert(message)
    return message


def react_message_webhook(request, botId, event_index):
    logger.info("got react message webhook")
    # リクエストボディーをJSONに変換
    request_json = request.get_json()
    bot = db_bot.get_row(botId)
    channel_access_token = bot["channel_access_token"]
    gpt_url = bot["gpt_webhook_url"]

    message: str = request_json['events'][event_index]['message']['text']

    # convert message to command if it is jp command
    message = convert_jp_command(message)

    # チャットボット機能の際は転送
    if message.startswith("あまおとちゃん") and not IS_DEBUG_MODE:
        for _ in range(3):
            response = transcribeWebhook(request, gpt_url)
            if response[1] == 200:
                return "finish", 200
            time.sleep(0.5)
        return "error", 200  # エラーだが、ここはLINEのサーバーに応答する都合上200を返す

    # 全角の！を半角に変換
    message = message.replace("！", "!")

    if not message.startswith("!"):
        return "finish", 200
    logger.info("start command process")
    # コマンド処理

    Commands(channel_access_token, request=request, botId=botId).process(message)

    return


def react_leave_webhook(request, botId, event_index):
    logger.info("got left webhook")
    # グループから抜けたことを記録
    db_bot.update_value(botId, "in_group", False)
