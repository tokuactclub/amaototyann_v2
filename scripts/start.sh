
wait_for_log_string() {
    local TARGET="$1"
    local LOG_FILE="./amaototyann/logs/app.log"

    if [ ! -f "$LOG_FILE" ]; then
        # 作成
        mkdir -p "$(dirname "$LOG_FILE")"
    fi

    # 現在のログの行数を記録（ここ以前は無視）
    START_LINE=$(wc -l < "$LOG_FILE")

    # tailで現在の行数以降を監視
    tail -n +$((START_LINE + 1)) -F "$LOG_FILE" | while IFS= read -r line; do
        echo "$line" | grep -F "$TARGET">/dev/null
        if echo "$line" | grep -qF "$TARGET" || echo "$line" | grep -qF "$KEYWORD"; then
            echo "Flask is up!"
            break
        fi
    done
}

echo "=========================="
echo "Starting database..."
echo "=========================="
# DB起動して出力を監視
python3 -m amaototyann.src.database &
DB_PID=$!
# wait for server to start

wait_for_log_string "* Running on http://127.0.0.1:5000"

echo "==========================="
echo "Database started."
echo "Starting server..."
echo "==========================="
# start server
gunicorn amaototyann.src.server:app --timeout 300 -w 1