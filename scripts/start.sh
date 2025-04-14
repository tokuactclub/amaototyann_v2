python3 src/database.py &
gunicorn src.server:app --timeout 300 -w 4
pkill -f src/database.py
