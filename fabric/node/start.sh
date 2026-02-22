#!/bin/sh
set -e
echo "=== fabric-node startup ==="
python bootstrap.py || echo "WARNING: bootstrap failed (continuing)"
echo "=== starting uvicorn ==="
exec uvicorn main:app --host 0.0.0.0 --port 8080
