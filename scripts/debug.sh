#!/bin/bash

# ポートで実行中のプロセスを強制終了
for port in 8000; do
    pid=$(lsof -ti tcp:$port)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid
    fi
done

echo "=========================="
echo "Starting server (debug)..."
echo "=========================="
uvicorn amaototyann.server.app:app --host 0.0.0.0 --port 8000 --reload
