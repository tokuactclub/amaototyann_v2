python3 src/database.py &
gunicorn src.server:app -w 1
pkill -f src/database.py
