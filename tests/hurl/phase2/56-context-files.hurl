# Phase 2.5a — WU-2: Purpose-specific @context files
# Serve JSON-LD context files at /.well-known/context/{name}

# Test 1: data.jsonld
GET {{gateway}}/.well-known/context/data.jsonld
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "sosa"
body contains "prov"

# Test 2: discovery.jsonld
GET {{gateway}}/.well-known/context/discovery.jsonld
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "void"
body contains "dcat"

# Test 3: meta.jsonld
GET {{gateway}}/.well-known/context/meta.jsonld
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "owl"
body contains "shacl"

# Test 4: fabric-context.jsonld (aggregate)
GET {{gateway}}/.well-known/context/fabric-context.jsonld
HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "data.jsonld"
body contains "discovery.jsonld"
body contains "meta.jsonld"

# Test 5: nonexistent context returns 404
GET {{gateway}}/.well-known/context/nonexistent.jsonld
HTTP 404
