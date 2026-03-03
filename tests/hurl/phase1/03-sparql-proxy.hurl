# Cycle 3 — SPARQL proxy through gateway
# RED: POST /sparql proxies to Oxigraph and returns results

# Auth setup: get VP token
POST {{gateway}}/test/create-vp
Content-Type: application/json
{"agentRole":"DevelopmentAgentRole","authorizedGraphs":["*"],"authorizedOperations":["read"]}
HTTP 201
[Captures]
vp_token: jsonpath "$.token"

POST {{gateway}}/sparql
Accept: application/sparql-results+json
Authorization: Bearer {{vp_token}}
[FormParams]
query: SELECT * WHERE {} LIMIT 1

HTTP 200
[Asserts]
header "Content-Type" contains "application/sparql-results+json"
jsonpath "$.results.bindings" isCollection
