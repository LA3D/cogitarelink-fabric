# Cycle 3 — SPARQL proxy through gateway
# RED: POST /sparql proxies to Oxigraph and returns results

POST http://localhost:8080/sparql
Accept: application/sparql-results+json
[FormParams]
query: SELECT * WHERE {} LIMIT 1

HTTP 200
[Asserts]
header "Content-Type" contains "application/sparql-results+json"
jsonpath "$.results.bindings" isCollection
