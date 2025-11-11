"""共通モジュール."""

# loggerの設定
import json
import os
from logging import getLogger, config
import requests
import pandas as pd

# logs/app.logのフォルダ・ファイルが存在しない場合は作成
if not os.path.exists("amaototyann/logs"):
    os.makedirs("amaototyann/logs")

# loggerの作成
with open("amaototyann/src/log_config.json", "r", encoding="utf-8") as f:
    config.dictConfig(json.load(f))
logger = getLogger("logger")

# flaskのアクセスloggerを統合
werkzeug_logger = getLogger("werkzeug")
werkzeug_logger.handlers = logger.handlers
# werkzeug_logger.setLevel(logger.level)

# flask_appのloggerを統合する関数


def integrate_flask_logger(flask_app):
    flask_app.logger.handlers = logger.handlers
    flask_app.logger.setLevel(logger.level)
    flask_app.logger.propagate = False


IS_DEBUG_MODE = not os.getenv("IS_RENDER_SERVER", "false").lower() == "true"
if IS_DEBUG_MODE:
    from dotenv import load_dotenv
    load_dotenv(override=True)


DATABASE_URL = os.getenv('DATABASE_URL', "")
GAS_URL = os.getenv('GAS_URL', "")
if not DATABASE_URL:
    logger.error("DATABASE_URL is not set")
    raise EnvironmentError("DATABASE_URL is not set")
if not GAS_URL:
    logger.error("GAS_URL is not set")
    raise EnvironmentError("GAS_URL is not set")


class _BotInfo:
    def __init__(self):
        self._database = pd.DataFrame(columns=['id', 'bot_name', 'channel_access_token', 'channel_secret', 'gpt_webhook_url', 'in_group'])
        self._is_updated = False
        self.init_database_from_gas()

    def init_database_from_gas(self):
        """Update all bot info from GAS and update the in-memory database."""
        BOT_INFOS = requests.post(
            GAS_URL,
            json={"cmd": "getBotInfo"},
            timeout=60
        ).json()

        # Clear the existing database
        self._database = pd.DataFrame(columns=['id', 'bot_name', 'channel_access_token', 'channel_secret', 'gpt_webhook_url', 'in_group'])

        # Populate the database with new data
        for bot_info in BOT_INFOS:
            new_entry = pd.DataFrame([{
                'id': bot_info[0],
                'bot_name': bot_info[1],
                'channel_access_token': bot_info[2],
                'channel_secret': bot_info[3],
                'gpt_webhook_url': bot_info[4],
                'in_group': bot_info[5]
            }])
            self._database = pd.concat([self._database, new_entry], ignore_index=True)

    def add_row(self, bot_id: int, bot_name: str, channel_access_token: str, channel_secret: str, gpt_webhook_url: str, in_group: bool):
        if not all([bot_id, bot_name, channel_access_token, channel_secret, gpt_webhook_url, in_group]):
            raise ValueError('All fields are required')
        if bot_id in self._database['id'].values:
            raise ValueError('ID already exists')
        self._is_updated = True
        new_entry = pd.DataFrame([{
            'id': bot_id,
            'bot_name': bot_name,
            'channel_access_token': channel_access_token,
            'channel_secret': channel_secret,
            'gpt_webhook_url': gpt_webhook_url,
            'in_group': in_group
        }])
        self._database = pd.concat([self._database, new_entry], ignore_index=True)

    def get_row(self, bot_id: int):
        """get bot info by id """
        entry = self._database[self._database['id'] == bot_id]
        if entry.empty:
            raise ValueError(f'ID not found, id: {bot_id}')
        return entry.iloc[0].to_dict()

    def delete_row(self, bot_id: int):
        """delete bot info by id"""
        assert isinstance(bot_id, int), 'ID must be an integer'
        self._is_updated = True

        if bot_id in self._database['id'].values:
            self._database = self._database[self._database['id'] != bot_id].reset_index(drop=True)
        else:
            raise ValueError('ID not found')

    def list_rows(self):
        return self._database.to_dict(orient='records')

    def update_value(self, bot_id: int, column: str, value):
        assert isinstance(bot_id, int), 'ID must be an integer'
        self._is_updated = True
        if bot_id not in self._database['id'].values:
            raise ValueError('ID not found')
        if column not in self._database.columns:
            raise ValueError('Column not found')
        if column == 'in_group' and not isinstance(value, bool):
            value = True if str(value).lower() == 'true' else False
        logger.info("Updating %s for ID %s to %s", column, bot_id, value)
        self._database.loc[self._database['id'] == bot_id, column] = value

    def backup_to_gas(self):
        """Backup the current database to GAS."""
        if not self._is_updated:
            return "not need to backup", 200

        # Convert the database to a list for GAS
        db = self.list_rows()
        if db is None:
            logger.error("database is None")
            return "error", 500

        db = list(map(lambda x: [x["id"], x["bot_name"], x["channel_access_token"], x["channel_secret"], x["gpt_webhook_url"], x["in_group"]], db))

        # Send the database to GAS
        if IS_DEBUG_MODE:
            return "didn't backup due to debug mode", 200
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
    def __init__(self):
        self.init_group_info_from_gas()
        self._is_updated = False

    def init_group_info_from_gas(self):
        """Initialize group info from GAS."""
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
        """Set group info."""
        if not all([group_id, group_name]):
            raise ValueError('All fields are required')
        self._group_info = {
            'id': group_id,
            'groupName': group_name
        }
        self._is_updated = True

    def group_id(self):
        """return group id."""
        if self._group_info is None:
            raise ValueError("Group info not initialized")
        return self._group_info.get('id')

    def backup_to_gas(self):
        """Backup group info to GAS."""
        if not self._is_updated:
            return "not need to backup", 200

        if IS_DEBUG_MODE:
            return "didn't backup due to debug mode", 200

        # Send the group info to GAS
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


class BotInfo(_BotInfo):

    def __init__(self):
        pass

    def __getattribute__(self, name):
        def wrapped(*args, **kwargs):
            url = os.path.join(DATABASE_URL, "bot", name + "/")
            response = requests.post(url, json={
                'args': args,
                'kwargs': kwargs
            }, timeout=60)
            if response.status_code == 200:
                return response.json()["result"]
            else:
                logger.error("Error from server: %s", response.text)
                raise Exception("Error from server: %s" % response.text)
        return wrapped


class GroupInfo(_GroupInfo):
    """GroupInfo class that extends _GroupInfo."""

    def __init__(self):
        """"""
        pass

    def __getattribute__(self, name):
        def wrapped(*args, **kwargs):
            url = os.path.join(DATABASE_URL, "group", name + "/")
            response = requests.post(url, json={
                'args': args,
                'kwargs': kwargs
            }, timeout=60)
            if response.status_code == 200:
                return response.json()["result"]
            else:
                raise Exception("Error from server: %s" % response.text)
        return wrapped


# webhookを転送する関数
def transcribeWebhook(request, url, body=None):
    """webhookを転送する関数

    Args:
        request (Request): リクエスト
        url (str): 転送先のURL
        body (dict, optional): リクエストボディを変えたい場合指定

    Returns:
        Response: 転送先からのレスポンス
    """
    method = request.method
    logger.info("headersType:%s", type(request.headers))
    headers = {key: value for key, value in dict(request.headers).items() if key != 'Host'}
    if (not body):  # bodyを指定されなければeventのbodyを利用（本来の挙動）
        body = request.json

    logger.info("Method: %sType:%s", method, type(method))
    logger.info("URL : %sType:%s", url, type(url))
    logger.info("Headers: %sType:%s", headers, type(headers))
    logger.info("Body: %sType:%s", body, type(body))

    try:
        # Reconstruct headers and forward the request
        headers["Content-Type"] = "application/json;charset=utf-8"
        response = requests.request(
            method=method,
            url=url,
            headers=json.loads(json.dumps(headers)),
            json=json.loads(json.dumps(body)),
            timeout=60
        )

        logger.info('Forwarded Data: %s', response)
        logger.info('HTTP Status Code: %s', response.status_code)

        return 'Data forwarded successfully', 200
    except Exception as e:
        logger.error('Error: %s', e)
        return 'Failed to forward data', 500


db_bot = BotInfo()
db_group = GroupInfo()
