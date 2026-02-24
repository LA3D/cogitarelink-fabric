# Phase 2 — VC issuance error handling
# Missing required fields should return 400.

POST http://localhost:3000/credentials/issue
Content-Type: application/json
{}

HTTP 400
