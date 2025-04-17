#!/bin/bash


# Flask起動ログを監視して指定文字列が現れるまで待つ関数
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



# ポート8000, 10000で実行中のプロセスを強制終了
for port in  5000 8000 10000; do
    pid=$(lsof -ti tcp:$port)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid
    fi
done


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
gunicorn amaototyann.src.server:app --timeout 300 -w 1 &
GUNICORN_PID=$!

wait_for_log_string " [INFO] Listening at: http://127.0.0.1:8000"

echo "============================"
echo "Server started."
echo "starting debugger..."
echo "============================"

# start debugger
python3 -m amaototyann.debug.debugger 


echo "Stopping processes..."
kill $GUNICORN_PID
kill $DB_PID

# 一応ポート8000, 10000で実行中のプロセスを強制終了
for port in  8000 10000; do
    pid=$(lsof -ti tcp:$port)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid
    fi
done