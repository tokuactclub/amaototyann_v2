# loggerの設定
import json
import os
from logging import getLogger, config

# logs/app.logのフォルダ・ファイルが存在しない場合は作成
if not os.path.exists("amaototyann/logs"):
    os.makedirs("amaototyann/logs")

with open("amaototyann/src/log_config.json", "r") as f:
    config.dictConfig(json.load(f))
logger = getLogger("logger")


is_render_server = os.getenv("IS_RENDER_SERVER")
if not is_render_server or is_render_server == "False":
    from dotenv import load_dotenv
    load_dotenv(override=True)

import pandas as pd  # type: ignore
import os
import requests  # type: ignore

class BotInfo:
    def __init__(self):
        self.database = pd.DataFrame(columns=['id', 'bot_name', 'channel_access_token', 'channel_secret', 'gpt_webhook_url', 'in_group'])
        self.is_updated = False
        self.init_database_from_gas()

    def init_database_from_gas(self):
        """Update all bot info from GAS and update the in-memory database."""
        BOT_INFOS = requests.post(
                    os.getenv('GAS_URL'),
                    json={"cmd": "getBotInfo"}
                    ).json()

        # Clear the existing database
        self.database = pd.DataFrame(columns=['id', 'bot_name', 'channel_access_token', 'channel_secret', 'gpt_webhook_url', 'in_group'])

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
            self.database = pd.concat([self.database, new_entry], ignore_index=True)

    def add_row(self, id: int, bot_name: str, channel_access_token: str, channel_secret: str, gpt_webhook_url: str, in_group: bool):
        if not all([id, bot_name, channel_access_token, channel_secret, gpt_webhook_url, in_group]):
            raise ValueError('All fields are required')
        if id in self.database['id'].values:
            raise ValueError('ID already exists')
        new_entry = pd.DataFrame([{
            'id': id,
            'bot_name': bot_name,
            'channel_access_token': channel_access_token,
            'channel_secret': channel_secret,
            'gpt_webhook_url': gpt_webhook_url,
            'in_group': in_group
        }])
        self.database = pd.concat([self.database, new_entry], ignore_index=True)

    def get_row(self, id: int):
        entry = self.database[self.database['id'] == id]
        if entry.empty:
            raise ValueError(f'ID not found, id: {id}')
        return entry.iloc[0].to_dict()

    def delete_row(self, id: int):
        assert isinstance(id, int), 'ID must be an integer'

        if id in self.database['id'].values:
            self.database = self.database[self.database['id'] != id].reset_index(drop=True)
        else:
            raise ValueError('ID not found')

    def list_rows(self):
        return self.database.to_dict(orient='records')

    def update_value(self, id: int, column: str, value):
        assert isinstance(id, int), 'ID must be an integer'
        if id not in self.database['id'].values:
            raise ValueError('ID not found')
        if column not in self.database.columns:
            raise ValueError('Column not found')
        if column == 'in_group'and not isinstance(value, bool):
            value = True if str(value).lower() == 'true' else False
        logger.info(f"Updating {column} for ID {id} to {value}")
        self.database.loc[self.database['id'] == id, column] = value
        logger.info(self.database)

# Initialize the database manager
db_bot = BotInfo()

# Initialize group info from GAS
try:
    group_info = requests.post(
        os.getenv('GAS_URL'),
        json={"cmd": "getGroupInfo"}
    ).json()
except Exception as e:
    logger.error(f"Failed to initialize group info: {e}")
    group_info = None