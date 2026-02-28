#!/bin/bash
echo "=========================="
echo "Starting amaototyann v3..."
echo "=========================="
uv run uvicorn amaototyann.server.app:app --host 0.0.0.0 --port 8000
