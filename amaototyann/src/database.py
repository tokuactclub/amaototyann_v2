
from flask import Flask, request, jsonify 
import pandas as pd 
from amaototyann.src import logger
from amaototyann.src import _BotInfo, _GroupInfo, integrate_flask_logger

app = Flask(__name__)
app.strict_slashes = False
integrate_flask_logger(app)

db_bot = _BotInfo()
db_group = _GroupInfo()


@app.route('/')
def route():
    return "Hello, World!"   

@app.route('/<db_type>/<function>/', methods=['POST'])
def db_endpoint(db_type,function):
    args_kwargs = request.get_json() or {}
    args = args_kwargs.get('args', [])
    kwargs = args_kwargs.get('kwargs', {})
    db = db_bot if db_type == 'bot' else db_group if db_type == 'group' else None

    if db is None:
        return jsonify({"status": "error", "message": f"Database '{db_type}' not found"}), 404

    try:
        func = getattr(db, function)
        if callable(func):
            result = func(*args, **kwargs)
            return jsonify({"status": "success", "result": result}), 200
        else:
            return jsonify({"status": "error", "message": f"'{function}' is not callable"}), 400
    except AttributeError:
        return jsonify({"status": "error", "message": f"Function '{function}' not found"}), 404
    except TypeError as e:
        return jsonify({"status": "error", "message": f"Argument error: {e}"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
    
