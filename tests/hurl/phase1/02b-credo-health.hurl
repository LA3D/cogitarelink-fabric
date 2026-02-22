# Cycle 8 — Credo sidecar smoke test
# RED: credo-sidecar /health returns HTTP 200
# CRITICAL: tests Rosetta (platform: linux/amd64) compatibility on Apple Silicon (D8)

GET http://localhost:3000/health

HTTP 200
