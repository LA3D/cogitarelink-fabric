# Phase 2.5a — WU-4: void:vocabulary on ontology named graphs
# VoID declares vocabulary namespace for each ontology sd:namedGraph

# Test 1: VoID Turtle has void:vocabulary for ontology graphs
GET {{gateway}}/.well-known/void
Accept: text/turtle
HTTP 200
[Asserts]
body contains "void:vocabulary"
body contains "/ontology/sosa"
body contains "prov:wasDerivedFrom"

# Test 2: VoID JSON-LD has ontology named graph entries
GET {{gateway}}/.well-known/void
Accept: application/ld+json
HTTP 200
[Asserts]
body contains "void:vocabulary"
body contains "/ontology/sosa"
body contains "prov:wasDerivedFrom"
