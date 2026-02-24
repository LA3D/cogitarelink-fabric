# Phase 2 — Credo DID creation (D3, D5)
# Bootstrap should have already created the DID at startup.
# POST /dids/node returns existing DID on repeated calls.

POST http://localhost:3000/dids/node

HTTP 200
[Asserts]
jsonpath "$.did" startsWith "did:webvh:"
jsonpath "$.didDocument" exists
