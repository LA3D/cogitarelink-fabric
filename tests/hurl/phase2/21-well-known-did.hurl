# Phase 2 — FastAPI .well-known/did routes (D5, D8)
# Served from shared volume written by Credo sidecar.

GET {{gateway}}/.well-known/did.jsonl

HTTP 200
[Asserts]
body contains "versionId"

GET {{gateway}}/.well-known/did.json

HTTP 200
[Asserts]
# did:webvh log entries have DID document in "state" field
body contains "did:webvh:"
