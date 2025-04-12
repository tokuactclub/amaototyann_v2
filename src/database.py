from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# In-memory database (pandas DataFrame) with updated column names
database = pd.DataFrame(columns=['id', 'bot_name', 'channel_access_token', 'channel_secret', 'gpt_webhook_url', 'in_group'])

@app.route('/add', methods=['POST'])
def add_entry():
    data = request.get_json()
    # Extract required fields
    id = data.get('id')
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
def get_entry(id):
    global database
    entry = database[database['id'] == id]
    if entry.empty:
        return jsonify({'error': 'ID not found'}), 404
    return jsonify(entry.iloc[0].to_dict()), 200

@app.route('/delete/<id>', methods=['DELETE'])
def delete_entry(id):
    global database
    if id in database['id'].values:
        database = database[database['id'] != id].reset_index(drop=True)
        return jsonify({'message': 'Entry deleted successfully'}), 200
    return jsonify({'error': 'ID not found'}), 404

@app.route('/list', methods=['GET'])
def list_entries():
    global database
    return jsonify(database.to_dict(orient='records')), 200

@app.route('/update_row/<id>', methods=['PATCH'])  # Updated function name
def update_row_by_id(id):  # Updated function name
    data = request.get_json()
    global database
    if id not in database['id'].values:
        return jsonify({'error': 'ID not found'}), 404
    for field, value in data.items():
        if field in database.columns:
            database.loc[database['id'] == id, field] = value
        else:
            return jsonify({'error': f'Field "{field}" is not valid'}), 400
    return jsonify({'message': 'Row updated successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True)