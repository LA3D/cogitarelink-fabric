# Phase 2.5a — WU-3: _inject_context() on CONSTRUCT routes
# Verify JSON-LD responses include @context after injection

# Test 1: /ontology/sosa JSON-LD has @context + @graph
GET {{gateway}}/ontology/sosa
Accept: application/ld+json
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "@context"
body contains "@graph"
body contains "meta.jsonld"

# Test 2: /.well-known/catalog JSON-LD has discovery @context
GET {{gateway}}/.well-known/catalog
Accept: application/ld+json
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "@context"
body contains "discovery.jsonld"

# Test 3: /fabric/registry JSON-LD has discovery @context
GET {{gateway}}/fabric/registry
Accept: application/ld+json
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "@context"
body contains "discovery.jsonld"

# Test 4: Turtle responses unaffected (no @context injection)
GET {{gateway}}/ontology/sosa
Accept: text/turtle
HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
