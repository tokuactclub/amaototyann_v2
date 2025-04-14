#!/bin/bash


# gunicorn をバックグラウンドで起動
gunicorn amaototyann.src.server:app -w 1 &
GUNICORN_PID=$!
echo "Started gunicorn with PID: $GUNICORN_PID"


python3 -m amaototyann.debug.debugger


echo "Stopping processes..."
kill $GUNICORN_PID

# 一応ポート5000, 8000, 1000で実行中のプロセスを強制終了
    pid=$(lsof -ti tcp:$port)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid
    fi
done