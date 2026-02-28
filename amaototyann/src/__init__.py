"""共通モジュール."""

import json
import os
from logging import getLogger, config
from pathlib import Path
import requests

_BASE_DIR = Path(__file__).parent

# logs ディレクトリの作成
_LOG_DIR = _BASE_DIR.parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# logger の作成
with open(_BASE_DIR / "log_config.json", "r", encoding="utf-8") as f:
    config.dictConfig(json.load(f))
logger = getLogger("logger")


IS_DEBUG_MODE = not os.getenv("IS_RENDER_SERVER", "false").lower() == "true"
if IS_DEBUG_MODE:
    from dotenv import load_dotenv
    load_dotenv(override=True)

GAS_URL = os.getenv('GAS_URL', "")
if not GAS_URL:
    logger.error("GAS_URL is not set")
    raise EnvironmentError("GAS_URL is not set")


class _BotInfo:
    """LINE Bot 情報をインメモリで管理するクラス."""

    def __init__(self):
        self._database: list[dict] = []
        self._is_updated = False
        self.init_database_from_gas()

    def init_database_from_gas(self):
        """GAS から Bot 情報を取得してインメモリDBを更新."""
        for _ in range(3):
            try:
                bot_infos = requests.post(
                    GAS_URL,
                    json={"cmd": "getBotInfo"},
                    timeout=60
                ).json()
                self._database = [
                    {
                        'id': info[0], 'bot_name': info[1],
                        'channel_access_token': info[2], 'channel_secret': info[3],
                        'gpt_webhook_url': info[4], 'in_group': info[5]
                    }
                    for info in bot_infos
                ]
                break
            except Exception as e:
                logger.error("Failed to initialize bot info: %s", e)

    def get_row(self, bot_id: int) -> dict:
        """Bot ID から Bot 情報を取得."""
        for row in self._database:
            if row['id'] == bot_id:
                return row
        raise ValueError(f'ID not found, id: {bot_id}')

    def list_rows(self) -> list[dict]:
        """全 Bot 情報を取得."""
        return self._database

    def update_value(self, bot_id: int, column: str, value):
        """Bot 情報の値を更新."""
        self._is_updated = True
        for row in self._database:
            if row['id'] == bot_id:
                if column == 'in_group' and not isinstance(value, bool):
                    value = str(value).lower() == 'true'
                row[column] = value
                logger.info("Updating %s for ID %s to %s", column, bot_id, value)
                return
        raise ValueError('ID not found')

    def backup_to_gas(self):
        """Bot 情報を GAS にバックアップ."""
        if not self._is_updated:
            return "not need to backup", 200
        if IS_DEBUG_MODE:
            return "didn't backup due to debug mode", 200

        db = [
            [x["id"], x["bot_name"], x["channel_access_token"],
             x["channel_secret"], x["gpt_webhook_url"], x["in_group"]]
            for x in self._database
        ]
        response = requests.post(
            GAS_URL,
            json={"cmd": "setBotInfo", "options": {"bot_info": db}},
            timeout=60
        )
        if response.text == "success":
            logger.info("bot info backup success")
            self._is_updated = False
            return "success", 200
        else:
            logger.error("bot info backup error")
            return "error", 500


class _GroupInfo:
    """グループ情報をインメモリで管理するクラス."""

    def __init__(self):
        self.init_group_info_from_gas()
        self._is_updated = False

    def init_group_info_from_gas(self):
        """GAS からグループ情報を取得."""
        for _ in range(3):
            try:
                self._group_info = requests.post(
                    GAS_URL,
                    json={"cmd": "getGroupInfo"},
                    timeout=60
                ).json()
                break
            except Exception as e:
                logger.error("Failed to initialize group info: %s", e)

    def set_group_info(self, group_id: str, group_name: str):
        """グループ情報を設定."""
        if not all([group_id, group_name]):
            raise ValueError('All fields are required')
        self._group_info = {
            'id': group_id,
            'groupName': group_name
        }
        self._is_updated = True

    def group_id(self):
        """グループ ID を返す."""
        if self._group_info is None:
            raise ValueError("Group info not initialized")
        return self._group_info.get('id')

    def backup_to_gas(self):
        """グループ情報を GAS にバックアップ."""
        if not self._is_updated:
            return "not need to backup", 200
        if IS_DEBUG_MODE:
            return "didn't backup due to debug mode", 200

        response = requests.post(
            GAS_URL,
            json={
                "cmd": "setGroupInfo",
                "options": {
                    "id": self._group_info['id'],
                    "groupName": self._group_info['groupName'],
                }
            },
            timeout=60
        )
        if response.text == "success":
            logger.info("Group info backup success")
            self._is_updated = False
            return "success", 200
        else:
            logger.error("Group info backup error")
            return "error", 500


db_bot = _BotInfo()
db_group = _GroupInfo()

from amaototyann.src import messages  # noqa: E402
