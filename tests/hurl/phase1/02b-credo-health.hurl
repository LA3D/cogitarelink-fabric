# Credo sidecar health — agent must be ready (Phase 2: full init with OWF Askar)
# Tests Rosetta (platform: linux/amd64) compatibility on Apple Silicon (D8)

GET http://localhost:3000/health

HTTP 200
[Asserts]
jsonpath "$.agent" == "ready"
