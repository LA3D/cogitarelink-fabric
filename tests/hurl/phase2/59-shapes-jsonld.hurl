# Phase 2.5a — WU-5: Shapes + SPARQL examples JSON-LD content negotiation

# Test 1: SHACL shapes as JSON-LD
GET {{gateway}}/.well-known/shacl
Accept: application/ld+json
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "@context"

# Test 2: SHACL shapes as Turtle (regression check)
GET {{gateway}}/.well-known/shacl
Accept: text/turtle
HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "NodeShape"

# Test 3: SPARQL examples as JSON-LD
GET {{gateway}}/.well-known/sparql-examples
Accept: application/ld+json
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "@context"

# Test 4: SPARQL examples as Turtle (regression check)
GET {{gateway}}/.well-known/sparql-examples
Accept: text/turtle
HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
