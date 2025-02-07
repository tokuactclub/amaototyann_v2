import requests
import os
from pprint import pprint
class BotInfo(list):
    def __init__(self):
        # self.GAS_URL = os.getenv('GAS_URL')
        self.GAS_URL = 'https://script.google.com/macros/s/AKfycby8acn6-HFL9snjXpYp1bK8S8Ju7w6WR4la6znsMjJNpvsDLSnZl0D-UtyfG2P_o1JL/exec'
        
        self.fetch()
        self.update_infos = False
    
    
    def __setitem__(self, index, value):
        if super().__getitem__(index) != value:
            self.update_infos = True
        super().__setitem__(index, value)

    def fetch(self):
        BOT_INFOS = requests.post(
                self.GAS_URL,
                json={"cmd":"getBotInfo"}
                ).json()
        super().__init__(BOT_INFOS)

    def send(self):
        requests.post(
            self.GAS_URL,
            json={"cmd":"setBotInfo", "options":{ "bot_info": self}}
            )

    
if __name__ == "__main__":
    botInfo = BotInfo()
    pprint(botInfo)
    botInfo[0][0] = "あまおとちゃん2"
    pprint(botInfo)
    # botInfo.test()
    botInfo.send()
    botInfo.fetch()
    pprint(botInfo)