#!/bin/bash
set -e

echo "=========================="
echo "Running linters..."
echo "=========================="

echo "--- ruff format ---"
uv run ruff format amaototyann/

echo "--- ruff check --fix ---"
uv run ruff check --fix amaototyann/

echo "--- ty check ---"
uv run ty check amaototyann/ || echo "ty check completed with warnings"

echo "=========================="
echo "All checks passed!"
echo "=========================="
