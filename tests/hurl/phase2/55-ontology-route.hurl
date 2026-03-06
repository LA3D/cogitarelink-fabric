# Phase 2.5a — WU-1: /ontology/{vocab} dynamic route (D22)
# Serve cached ontology content from named graphs via content negotiation

# Test 1: GET /ontology/sosa as Turtle
GET {{gateway}}/ontology/sosa
Accept: text/turtle
HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "sosa"

# Test 2: GET /ontology/sosa as JSON-LD (WU-3 injects @context)
GET {{gateway}}/ontology/sosa
Accept: application/ld+json
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "@context"
body contains "@graph"

# Test 3: GET /ontology/sio as Turtle (second ontology)
GET {{gateway}}/ontology/sio
Accept: text/turtle
HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"

# Test 4: GET /ontology/nonexistent returns 404
GET {{gateway}}/ontology/nonexistent
Accept: text/turtle
HTTP 404

# Test 5: Path traversal attempt — FastAPI/Starlette rejects before handler
GET {{gateway}}/ontology/..%2Fetc%2Fpasswd
HTTP 404
