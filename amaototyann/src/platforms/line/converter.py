"""日本語コマンド変換モジュール."""


class Converter:
    """日本語テキストをコマンド文字列に変換するクラス."""

    def __init__(self):
        self.Tcs_same_dic = {}
        self.Fcs_same_dic = {}
        self.Tcs_start_dic = {}
        self.Fcs_start_dic = {}

    def add_argument(self, key, value, condition="same", case_sensitive=False):
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
    """日本語のメッセージをコマンドに変換する."""
    converter = Converter()
    converter.add_argument(
        ["引き継ぎ資料", "引継ぎ資料", "ScrapBox", "ひきつぎしりょう", "すくらっぷぼっくす"],
        "!handover", condition="start"
    )
    converter.add_argument(["Youtube", "ユーチューブ", "ようつべ"], "!youtube", condition="same")
    converter.add_argument(
        ["Instagram", "インスタグラム", "いんすたぐらむ", "インスタ", "いんすた"],
        "!instagram", condition="same"
    )
    converter.add_argument(
        ["Twitter", "ツイッター", "ついったー", "X", "エックス", "えっくす"],
        "!twitter", condition="same"
    )
    converter.add_argument(["ホームページ", "HP", "ほーむぺーじ"], "!homepage", condition="same")
    return converter.convert(message)
