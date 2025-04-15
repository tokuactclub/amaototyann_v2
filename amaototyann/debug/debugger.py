from flask import Flask, render_template_string, request
import requests
import json
import os
from amaototyann.src import logger, db_bot, group_info_manager

app = Flask(__name__)

# Get the list of available webhook templates
templates_dir = os.path.join(os.path.dirname(__file__), "webhook_templates")
template_files = [f for f in os.listdir(templates_dir) if f.endswith(".json")]

# Load the HTML template from the templates folder
html_template_path = os.path.join(os.path.dirname(__file__), "templates/webhook_sender.html")
with open(html_template_path, "r") as f:
    html_template = f.read()

def fetch_database_data():
    """Fetch the latest database data."""
    try:
        bot_info = db_bot
        database_data = bot_info.list_rows()
        return list(map(lambda x: [x["id"], x["bot_name"], x["in_group"]], database_data))
    except Exception as e:
        logger.error(f"Failed to fetch database data: {str(e)}")
        return []

@app.route("/", methods=["GET", "POST"])
def index():
    response = None
    bot_id = request.form.get("botId") if request.method == "POST" and "botId" in request.form else None  # botIdを取得
    selected_template = request.form.get("template") if request.method == "POST" else None
    webhook_template = {}
    editable_fields = {}
    database_data = fetch_database_data()  # リアルタイムでデータを取得

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

        elif selected_template == "join.json":
            # group_idを取得してjoin.jsonの値を更新
            group_id = group_info_manager.group_id
            webhook_template["events"][0]["source"]["groupId"] = group_id
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

            # Database contentを再取得
            database_data = fetch_database_data()

        except Exception as e:
            response = {"error": str(e)}

    return render_template_string(
        html_template,
        response=response,
        templates=template_files,
        editable_fields=editable_fields,
        database_data=database_data,  # 最新のデータをテンプレートに渡す
        bot_ids=[{"id": bot[0], "name": bot[1]} for bot in database_data],  # bot_idリストを渡す
        request_form=request.form  # request.formをテンプレートに渡す
    )

@app.route("/update_template", methods=["POST"])
def update_template():
    selected_template = request.form.get("template")
    webhook_template = {}
    editable_fields = {}
    database_data = fetch_database_data()  # bot_ids を再取得

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
            return f"<p>Error loading template: {str(e)}</p>"

    return render_template_string(
        """
        <form method="POST" action="/">
            <label for="template">Select Template:</label><br>
            <select id="template" name="template" required onchange="updateTemplate()">
                {% for template in templates %}
                    <option value="{{ template }}" {% if template == request.form.get('template') %}selected{% endif %}>{{ template }}</option>
                {% endfor %}
            </select><br><br>

            <label for="botId">Bot ID:</label><br>
            <select id="botId" name="botId" required>
                {% for bot in bot_ids %}
                    <option value="{{ bot.id }}" {% if bot.id == (request.form.get('botId')|int if request.form.get('botId') else None) %}selected{% endif %}>{{ bot.name }}</option>
                {% endfor %}
            </select><br><br>

            {% if editable_fields %}
                <h3>Edit Template Fields:</h3>
                {% for key, value in editable_fields.items() %}
                    {% if key == 'message.text' %}
                        <label for="{{ key }}">{{ key }}:</label><br>
                        <input type="text" id="{{ key }}" name="{{ key }}" value="{{ value }}"><br><br>
                    {% endif %}
                {% endfor %}
            {% endif %}

            <button type="submit">Send Webhook</button>
        </form>
        """,
        templates=template_files,
        editable_fields=editable_fields,
        bot_ids=[{"id": bot[0], "name": bot[1]} for bot in database_data],  # bot_ids を渡す
        request_form=request.form
    )

if __name__ == "__main__":
    app.run(debug=True, port= 10000)