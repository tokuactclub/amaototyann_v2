import requests
import os
from pprint import pprint
import json
# loggerの設定
from logging import getLogger, config
with open("src/log_config.json", "r") as f:
    config.dictConfig(json.load(f))
logger = getLogger(__name__)

class BotInfo():
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        
        # スプレッドシートの値を取得後に更新されたかどうか
        self.is_updated = False

    def get(self, id):
        url = f"{self.database_url}/get/{id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get data for ID {id}: {response.status_code} - {response.text}")
            return None
    
    def update(self, id, column, value):
        self.is_updated = True
        url = f"{self.database_url}/update/{id}/{column}/"
        response = requests.get(url, params={"value": value})
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to update data for ID {id}: {response.status_code} - {response.text}")
            return None
        
    def get_all(self):
        url = f"{self.database_url}/list/"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get all data: {response.status_code} - {response.text}")
            return None