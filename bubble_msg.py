def createMsg(contents):
    return {
      "type": "flex",
      "altText": "リマインダー",
      "contents":{
      "type": "carousel",
      "contents": contents}       
    }
class taskBubbleMsg:
    """締切りタスクのバブルメッセージを作成するクラス
    """
    def __init__(self):
        self.contents = []
    def addReminder(self, job, person, deadline, last_days, task, memo, id):
        """リマインダーを追加する

        Args:
            job (str): 仕事の名前
            person (str): 担当者
            deadline (str): 締切
            last_days (int): 残り日数
            task (str): タスク
            memo (str): メモ
            id (str): タスクのID
        """

        
        # テキスト形式で出力するコード。残しておく。
        # strict = "進捗を報告してください" if last_days < 4 else ""
        # msg = "\n".join(filter(lambda x: x != "", [f"{job}{person}", f"締切：{task}", strict, memo, f"残り日数：{last_days}"]))
        # string_messages.append(msg)
        
        bubble = {
            "type": "bubble",
            "size": "deca",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f" {job} ",
                        "align": "center",
                        "size": "xxl",
                        "weight": "bold"
                    },
                    {
                        "type": "text",
                        "text": f" {person} ",
                        "align": "center"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"締切{deadline}まで残り{last_days}日",
                        "align": "center",
                        "color": "#ff0000"
                    },
                    {
                        "type": "text",
                        "wrap": True,
                        "text": f" {task} \n{memo}",
                        "align": "center"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "message",
                                    "label": "順調です！",
                                    "text": f"{job}{task}順調です！"
                                }
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "message",
                                    "label": "終わりました！",
                                    "text": f"ama finish {id}"
                                }
                            },
                            {
                                "type": "button",
                                "action": {
                                    "type": "message",
                                    "label": "進捗ダメです！",
                                    "text": f"{job}{task}進捗ダメです！"
                                }
                            }
                        ],
                        "margin": "10px"
                    }
                ]
            }
        }

        self.contents.append(bubble)
    
    def getMessages(self):
        """作成したメッセージを取得する

        Returns:
            list: メッセージのリスト
        """
        messages = [create_msg(self.contents[i:i+12]) for i in range(0, len(self.contents), 12)]
        self.contents.clear()
        return messages
def create_msg(contents):
    # ここにメッセージを作成するロジックを実装してください
    return {"type": "carousel", "contents": contents}