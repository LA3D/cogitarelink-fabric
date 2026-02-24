# Phase 2 — VC verification route
# Verify the self-issued conformance VC from the gateway.

# Step 1: Fetch the conformance VC from FastAPI
GET http://localhost:8080/.well-known/conformance-vc.json

HTTP 200
[Captures]
vc_json: body

# Step 2: Verify it via Credo sidecar
POST http://localhost:3000/credentials/verify
Content-Type: application/json
```
{{vc_json}}
```

HTTP 200
[Asserts]
jsonpath "$.verified" == true
