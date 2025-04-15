#!/bin/bash
# ポート8000, 10000で実行中のプロセスを強制終了
for port in  8000 1000; do
    pid=$(lsof -ti tcp:$port)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid
    fi
done


python3 -m amaototyann.debug.start


echo "Stopping processes..."
kill $GUNICORN_PID

# 一応ポート8000, 10000で実行中のプロセスを強制終了
for port in  8000 10000; do
    pid=$(lsof -ti tcp:$port)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid
    fi
done