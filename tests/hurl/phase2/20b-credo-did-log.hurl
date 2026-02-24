# Phase 2 — Credo DID log (D5)
# did.jsonl must be served after bootstrap.

GET http://localhost:3000/did.jsonl

HTTP 200
[Asserts]
header "content-type" contains "application/jsonl"
body contains "versionId"
body contains "did:webvh:"
