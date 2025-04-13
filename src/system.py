import requests # type: ignore
import os
from pprint import pprint
import json
# loggerの設定
from logging import getLogger, config
with open("src/log_config.json", "r") as f:
    config.dictConfig(json.load(f))
logger = getLogger("logger")

def load_dotenv():
    """.envファイルを読み込む関数
    """
    is_render_server = os.getenv("IS_RENDER_SERVER")
    if not is_render_server or is_render_server == "False":
        from dotenv import load_dotenv as ld # type: ignore
        ld(override=True)

def init_logger():
    global logger
    return logger
    


class BotInfo():
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        logger.info(f"BotInfo initialized to database. url: {self.database_url}")
        

    def get(self, id):
        url = os.path.join(self.database_url, "get", str(id) + "/")
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get data for ID {id} at URL {url}: {response.status_code} - {response.text}")
            return None
    
    def update(self, id:str|int, column, value):
        self.is_updated = True
        url = os.path.join(self.database_url, "update_value", str(id), column+"/")
        response = requests.get(url, params={"value": value})
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to update data for ID {id} at URL {url}: {response.status_code} - {response.text}")
            return None
        
    def get_all(self):
        url = os.path.join(self.database_url, "list/")
        response = requests.get(url)
        print(f"get_all response: {response}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get all data at URL {url}: {response.status_code} - {response.text}")
            return None
    
    @property
    def is_updated(self):
        url = os.path.join(self.database_url, "is_updated/") 
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['is_updated']
        else:
            logger.error(f"Failed to check update status at URL {url}: {response.status_code} - {response.text}")
            return None
        
    @is_updated.setter
    def is_updated(self, value):
        url = os.path.join(self.database_url, "is_updated/") 
        response = requests.get(url, params={"value": value})
        if response.status_code == 200:
            return response.json()['is_updated']
        else:
            logger.error(f"Failed to check update status at URL {url}: {response.status_code} - {response.text}")
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
    



if __name__ == "__main__":
    load_dotenv()       


    # BotInfoのテスト
    bot_info = BotInfo()
    
    # IDが1のデータのnameを更新
    updated_data = bot_info.update(1, "in_group", False)
    pprint(updated_data)
