#!/bin/sh
echo "=== fabric-node startup ==="
python bootstrap.py 2>&1 || echo "WARNING: bootstrap failed (exit $?) — continuing without TBox"
echo "=== starting uvicorn ==="
exec uvicorn main:app --host 0.0.0.0 --port 8080
