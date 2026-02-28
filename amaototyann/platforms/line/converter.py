"""日本語コマンド変換モジュール."""

# 完全一致辞書 (case-insensitive)
_EXACT_MATCH: dict[str, str] = {}

# 前方一致辞書 (case-insensitive)
_PREFIX_MATCH: dict[str, str] = {}


def _register(keys: list[str], value: str, *, prefix: bool = False) -> None:
    """変換ルールを登録する."""
    target = _PREFIX_MATCH if prefix else _EXACT_MATCH
    for key in keys:
        target[key.lower()] = value


# === 変換ルール登録 ===
_register(
    ["引き継ぎ資料", "引継ぎ資料", "ScrapBox", "ひきつぎしりょう", "すくらっぷぼっくす"],
    "!handover", prefix=True,
)
_register(["Youtube", "ユーチューブ", "ようつべ"], "!youtube")
_register(
    ["Instagram", "インスタグラム", "いんすたぐらむ", "インスタ", "いんすた"],
    "!instagram",
)
_register(
    ["Twitter", "ツイッター", "ついったー", "X", "エックス", "えっくす"],
    "!twitter",
)
_register(["ホームページ", "HP", "ほーむぺーじ"], "!homepage")


def convert_jp_command(message: str) -> str:
    """日本語のメッセージをコマンドに変換する."""
    lower = message.lower()

    # 完全一致チェック
    if result := _EXACT_MATCH.get(lower):
        return result

    # 前方一致チェック
    for key, val in _PREFIX_MATCH.items():
        if lower.startswith(key):
            return val

    return message
