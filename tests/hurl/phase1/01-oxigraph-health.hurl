# Cycle 1 — Oxigraph container health
# RED: Oxigraph SPARQL endpoint responds to a minimal SELECT query

POST http://localhost:7878/query
Accept: application/sparql-results+json
[FormParams]
query: SELECT * WHERE {} LIMIT 1

HTTP 200
[Asserts]
header "Content-Type" contains "application/sparql-results+json"
jsonpath "$.results.bindings" isCollection
