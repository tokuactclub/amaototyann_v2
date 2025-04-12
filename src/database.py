from flask import Flask, request, jsonify
import pandas as pd
import os
import requests


app = Flask(__name__)
global database

def init_database_from_gas():
    """Update all bot info from GAS and update the in-memory database."""
    global database
    BOT_INFOS = requests.post(
                os.getenv('GAS_URL'),
                json={"cmd":"getBotInfo"}
                ).json()
    
    # Clear the existing database
    database = pd.DataFrame(columns=['id', 'bot_name', 'channel_access_token', 'channel_secret', 'gpt_webhook_url', 'in_group'])
    
    # Populate the database with new data
    for bot_info in BOT_INFOS: 
        new_entry = pd.DataFrame([{
            'id': bot_info[0],
            'bot_name': bot_info[1],
            'channel_access_token': bot_info[2],
            'channel_secret': bot_info[3],
            'gpt_webhook_url': bot_info[4],
            'in_group': bot_info[5] 
        }])
        database = pd.concat([database, new_entry], ignore_index=True)

init_database_from_gas()

@app.route('/overwrite_all')
def overwrite_all():
    init_database_from_gas()
    return jsonify({'message': 'All bot info updated successfully'}), 200

@app.route('/add', methods=['POST'])
def add_row():
    data = request.get_json()
    # Extract required fields
    id = data.get('id')
    id = int(id)
    bot_name = data.get('bot_name')
    channel_access_token = data.get('channel_access_token')
    channel_secret = data.get('channel_secret')
    gpt_webhook_url = data.get('gpt_webhook_url')
    in_group = data.get('in_group')
    if not all([id, bot_name, channel_access_token, channel_secret, gpt_webhook_url, in_group]):
        return jsonify({'error': 'All fields are required'}), 400
    global database
    if id in database['id'].values:
        return jsonify({'error': 'ID already exists'}), 400
    new_entry = pd.DataFrame([{
        'id': id,
        'bot_name': bot_name,
        'channel_access_token': channel_access_token,
        'channel_secret': channel_secret,
        'gpt_webhook_url': gpt_webhook_url,
        'in_group': in_group
    }])
    database = pd.concat([database, new_entry], ignore_index=True)
    return jsonify({'message': 'Entry added successfully'}), 201

@app.route('/get/<id>', methods=['GET'])
def get_row(id):
    global database
    id = int(id)
    entry = database[database['id'] == id]
    if entry.empty:
        return jsonify({'error': f'ID not found, id:{id}'}), 404
    return jsonify(entry.iloc[0].to_dict()), 200

@app.route('/delete/<id>', methods=['DELETE'])
def delete_row(id):
    global database
    id = int(id)
    if id in database['id'].values:
        database = database[database['id'] != id].reset_index(drop=True)
        return jsonify({'message': 'Entry deleted successfully'}), 200
    return jsonify({'error': 'ID not found'}), 404

@app.route('/list', methods=['GET'])
def list_rows():
    global database
    return jsonify(database.to_dict(orient='records')), 200

@app.route('/update_row/<id>/<column>', methods=['GET'])  # Updated function name
def update_value(id, column):  # Updated function name
    global database
    id = int(id)
    if id not in database['id'].values:
        return jsonify({'error': 'ID not found'}), 404
    if column not in database.columns:
        return jsonify({'error': 'Column not found'}), 404
    value = request.args.get('value')
    if value is None:
        return jsonify({'error': 'Value is required'}), 400
    database.loc[database['id'] == id, column] = value
    return jsonify({'message': 'Value updated successfully'}), 200
if __name__ == '__main__':
    app.run(debug=True, port=5000)