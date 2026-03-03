# Cycle A2 — TBox named graph exists with SOSA content (D9 L2, D6 /ontology/sosa)
# RED: SOSA TBox loaded into /ontology/sosa at node startup

# Auth setup: get VP token
POST {{gateway}}/test/create-vp
Content-Type: application/json
{"agentRole":"DevelopmentAgentRole","authorizedGraphs":["*"],"authorizedOperations":["read"]}
HTTP 201
[Captures]
vp_token: jsonpath "$.token"

POST {{gateway}}/sparql
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer {{vp_token}}

```
query=PREFIX sosa: <http://www.w3.org/ns/sosa/> PREFIX owl: <http://www.w3.org/2002/07/owl%23> ASK { GRAPH <{{gateway}}/ontology/sosa> { sosa:Observation a owl:Class } }
```

HTTP 200
[Asserts]
body contains "true"
