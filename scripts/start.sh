python3 -m amaototyann.src.database &
gunicorn src.server:app --timeout 300 -w 4
pkill -f src/database.py
