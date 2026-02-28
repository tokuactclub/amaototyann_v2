#!/bin/bash
echo "=========================="
echo "Starting server..."
echo "=========================="
uvicorn amaototyann.src.server:app --host 0.0.0.0 --port 8000
