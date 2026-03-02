#!/bin/sh
echo "=== fabric-node startup ==="

# If Caddy's internal CA is mounted, combine it with the system bundle so
# outbound HTTPS requests (e.g., self-admission) trust the internal TLS cert.
CADDY_CA=/caddy-ca/caddy/pki/authorities/local/root.crt
if [ -f "$CADDY_CA" ]; then
  COMBINED=/tmp/combined-ca.pem
  cat /usr/lib/ssl/cert.pem "$CADDY_CA" > $COMBINED
  export SSL_CERT_FILE=$COMBINED
  echo "SSL_CERT_FILE set to combined CA bundle (system + Caddy)"
fi

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
