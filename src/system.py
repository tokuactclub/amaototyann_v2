import requests
import os
from pprint import pprint

class BotInfo():
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")

    def get(self, id):
        url = f"{self.database_url}/get/{id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    def update(self, id, column, value):
        url = f"{self.database_url}/update/{id}/{column}/"
        response = requests.get(url, params={"value": value})
        if response.status_code == 200:
            return response.json()
        else:
            return None
        
    def get_all(self):
        url = f"{self.database_url}/list/"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return None