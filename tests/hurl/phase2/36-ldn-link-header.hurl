# Phase 2 — LDN inbox discovery via Link header (D25)

GET {{gateway}}/.well-known/did.json
HTTP 200
[Asserts]
header "Link" contains "ldp#inbox"
