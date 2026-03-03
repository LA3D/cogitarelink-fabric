# Cycle 7 — Entity dereference (FAIR A1)
# RED: INSERT an entity, then GET /entity/{id} returns Turtle via CONSTRUCT

# Auth setup: get VP token
POST {{gateway}}/test/create-vp
Content-Type: application/json
{"agentRole":"DevelopmentAgentRole","authorizedGraphs":["*"],"authorizedOperations":["read","write"]}
HTTP 201
[Captures]
vp_token: jsonpath "$.token"

# Step 1: Insert a test entity
POST {{gateway}}/sparql/update
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer {{vp_token}}

```
update=PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {
  GRAPH <{{gateway}}/graph/entities> {
    <{{gateway}}/entity/deref-test-001>
        a sosa:Observation ;
        sosa:hasSimpleResult "1.23"^^xsd:decimal .
  }
}
```

HTTP 204

# Step 2: Dereference the entity URI — expect Turtle with CONSTRUCT result
GET {{gateway}}/entity/deref-test-001
Accept: text/turtle

HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "deref-test-001"
body contains "sosa/Observation"

# Step 3: Negative test — nonexistent entity returns 404
GET {{gateway}}/entity/nonexistent-00000

HTTP 404
