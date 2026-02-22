# Cycle 4 — .well-known/void self-description
# RED: gateway exposes VoID description in Turtle and JSON-LD

# Request 1: Turtle representation
GET http://localhost:8080/.well-known/void
Accept: text/turtle

HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "void:sparqlEndpoint"
body contains "void:Dataset"

# Request 2: JSON-LD representation
GET http://localhost:8080/.well-known/void
Accept: application/ld+json

HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "void:Dataset"
body contains "void:sparqlEndpoint"
