#!/bin/sh
echo "=== fabric-node startup ==="
# Start uvicorn in background so gateway is available for Credo's waitForGateway()
uvicorn main:app --host 0.0.0.0 --port 8080 &
UVICORN_PID=$!

# Wait for uvicorn to be ready
echo "Waiting for uvicorn..."
for i in $(seq 1 30); do
  if python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')" 2>/dev/null; then
    echo "uvicorn ready"
    break
  fi
  sleep 1
done

# Run bootstrap (TBox + registry + catalog — waits for Credo VC)
echo "=== running bootstrap ==="
python bootstrap.py 2>&1 || echo "WARNING: bootstrap failed (exit $?) — continuing"

# Wait for uvicorn to exit (foreground the server process)
wait $UVICORN_PID
