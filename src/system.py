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
    logger.info(f"headersType:{type(request.headers)}")
    headers = {key: value for key, value in dict(request.headers).items() if key != 'Host'} 
    if(not body):#bodyを指定されなければeventのbodyを利用（本来の挙動）
        body = request.json
    
    logger.info(f"Method: {method}Type:{type(method)}")
    logger.info(f"URL : {url}Type:{type(url)}")
    logger.info(f"Headers: {headers}Type:{type(headers)}")
    logger.info(f"Body: {body}Type:{type(body)}")

    try:
        # Reconstruct headers and forward the request
        headers["Content-Type"] = "application/json;charset=utf-8"
        response = requests.request(
            method=method,
            url=url,
            headers=json.loads(json.dumps(headers)),
            json=json.loads(json.dumps(body)),
        )

        logger.info('Forwarded Data:', response)
        logger.info('HTTP Status Code:', response.status_code)

        return 'Data forwarded successfully', 200
    except Exception as e:
        logger.error('Error:', e)
        return 'Failed to forward data', 500