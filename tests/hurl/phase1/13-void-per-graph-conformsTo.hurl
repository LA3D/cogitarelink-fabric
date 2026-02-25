# Phase 1 — Per-graph dct:conformsTo in VoID (D9 L1 gap closure)
# Each named graph subset should declare its governing shape.

# Turtle: observations + entities subsets have conformsTo
GET {{gateway}}/.well-known/void
Accept: text/turtle

HTTP 200
[Asserts]
body contains "graph/observations"
body contains "ObservationShape"
body contains "graph/entities"
body contains "EntityShape"

# JSON-LD: entities subset has conformsTo
GET {{gateway}}/.well-known/void
Accept: application/ld+json

HTTP 200
[Asserts]
body contains "ObservationShape"
body contains "EntityShape"
