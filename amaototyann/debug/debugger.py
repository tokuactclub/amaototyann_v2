from flask import Flask, render_template_string, request, jsonify
import requests
import json
import os
from amaototyann.src.system import BotInfo

app = Flask(__name__)

# Get the list of available webhook templates
templates_dir = os.path.join(os.path.dirname(__file__), "webhook_templates")
template_files = [f for f in os.listdir(templates_dir) if f.endswith(".json")]

# Load the HTML template from the templates folder
html_template_path = os.path.join(os.path.dirname(__file__), "templates/webhook_sender.html")
with open(html_template_path, "r") as f:
    html_template = f.read()

@app.route("/", methods=["GET", "POST"])
def index():
    response = None
    selected_template = request.form.get("template") if request.method == "POST" else None
    bot_id = request.form.get("botId") if request.method == "POST" else None  # botIdを取得
    webhook_template = {}
    editable_fields = {}
    database_data = []  # データベースから取得したデータを格納

    # データベース接続とデータ取得
    try:
        bot_info = BotInfo()
        database_data = bot_info.get_all()
        database_data = list(map(lambda x: [x["id"], x["bot_name"], x["in_group"]], database_data))
        
        # group_idを取得してjoin.jsonの値を更新
        group_info = requests.post(
            os.getenv("GAS_URL"),
            json={"cmd": "getGroupInfo"}
        ).json()
        group_id = group_info["id"]

        # join.jsonを読み込んで値を更新
        join_json_path = "amaototyann/debug/webhook_templates/join.json"
        with open(join_json_path, "r") as f:
            join_data = json.load(f)
        join_data["group_id"] = group_id
        logger.info(f"Updated group_id in memory: {join_data['group_id']}")
    except Exception as e:
        response = {"error": f"Failed to fetch database data or update group_id: {str(e)}"}

    if selected_template:
        try:
            # Load the selected template
            template_path = os.path.join(templates_dir, selected_template)
            with open(template_path, "r") as f:
                webhook_template = json.load(f)
            webhook_template["debug"] = True

            # If the selected template is message.json, prepare editable fields
            if selected_template == "message.json":
                editable_fields = {"message.text": webhook_template["events"][0]["message"]["text"]}
        except Exception as e:
            response = {"error": f"Failed to load template: {str(e)}"}

    if request.method == "POST" and webhook_template:
        # Update webhook_template with edited fields if applicable
        if selected_template == "message.json" and "message.text" in request.form:
            webhook_template["events"][0]["message"]["text"] = request.form["message.text"]

        try:
            # botIdが指定されていない場合はデフォルト値を使用
            bot_id = bot_id or 1
            server_url = os.path.join(os.getenv("SERVER_URL"), "lineWebhook", str(bot_id) + "/")
            # Send the JSON payload to the specified server
            res = requests.post(server_url, json=webhook_template)
            response = {
                "status_code": res.status_code,
                "response_body": res.json() if res.headers.get("Content-Type") == "application/json" else res.text
            }
        except Exception as e:
            response = {"error": str(e)}

    return render_template_string(
        html_template,
        response=response,
        templates=template_files,
        editable_fields=editable_fields,
        database_data=database_data  # データベースデータをテンプレートに渡す
    )

if __name__ == "__main__":
    app.run(debug=True, port= 10000)