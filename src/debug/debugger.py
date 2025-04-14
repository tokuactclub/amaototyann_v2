from flask import Flask, render_template_string, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# Load the JSON payload (webhook_template) from the webhook_templates folder
template_path = os.path.join(os.path.dirname(__file__), "webhook_templates","message.json")
with open(template_path, "r") as f:
    webhook_template = json.load(f)
webhook_template["debug"] = True

# Load the HTML template from the templates folder
html_template_path = os.path.join(os.path.dirname(__file__), "templates/webhook_sender.html")
with open(html_template_path, "r") as f:
    html_template = f.read()

@app.route("/", methods=["GET", "POST"])
def index():
    response = None
    if request.method == "POST":
        botId = 1
        server_url = os.path.join(os.getenv("SERVER_URL"), "lineWebhook", str(botId) + "/")
        try:
            # Send the JSON payload to the specified server
            
            res = requests.post(server_url, json=webhook_template)
            response = {
                "status_code": res.status_code,
                "response_body": res.json() if res.headers.get("Content-Type") == "application/json" else res.text
            }
        except Exception as e:
            response = {"error": str(e)}
    return render_template_string(html_template, response=response)

if __name__ == "__main__":
    app.run(debug=True, port= 10000)