"""バブルメッセージを作成するモジュール."""
from linebot.models import FlexSendMessage


class taskBubbleMsg:
    """締切りタスクのバブルメッセージを作成するクラス."""

    def __init__(self):
        self.contents = []

    def addReminder(self, job, person, deadline, last_days, task, memo, id):
        bubble = {
            "type": "bubble",
            "size": "deca",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": f" {job} ", "align": "center", "size": "xxl", "weight": "bold"},
                    {"type": "text", "text": f" {person} ", "align": "center"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": f"締切{deadline}まで残り{last_days}日", "align": "center", "color": "#ff0000"},
                    {"type": "text", "wrap": True, "text": f" {task} \n{memo}", "align": "center"},
                    {"type": "separator", "margin": "md"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "button", "action": {"type": "message", "label": "順調です！", "text": f"{job}{task}順調です！"}},
                            {"type": "button", "action": {"type": "message", "label": "終わりました！", "text": f"!finish {id}"}},
                            {"type": "button", "action": {"type": "message", "label": "進捗ダメです！", "text": f"{job}{task}進捗ダメです！"}}
                        ],
                        "margin": "10px"
                    }
                ]
            }
        }
        self.contents.append(bubble)

    def getMessages(self):
        messages = [self._create_msg(self.contents[i:i + 12]) for i in range(0, len(self.contents), 12)]
        self.contents.clear()
        return messages

    def _create_msg(self, contents):
        json = {
            "type": "flex",
            "altText": "リマインダー",
            "contents": {"type": "carousel", "contents": contents}
        }
        return FlexSendMessage.new_from_json_dict(json)
