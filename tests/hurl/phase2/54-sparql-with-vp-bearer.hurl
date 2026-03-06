# Phase 2 — D13: SPARQL with VP Bearer auth succeeds
# Get a VP token via test helper, then use it on /sparql

# Step 1: Get VP token
POST {{gateway}}/test/create-vp
Content-Type: application/json
{
  "agentRole": "DevelopmentAgentRole",
  "authorizedGraphs": ["*"],
  "authorizedOperations": ["read", "write"]
}
HTTP 201
[Captures]
vp_token: jsonpath "$.token"

# Step 2: SELECT via POST with Bearer token → 200
POST {{gateway}}/sparql
Content-Type: application/sparql-query
Accept: application/sparql-results+json
Authorization: Bearer {{vp_token}}
```
SELECT * WHERE {} LIMIT 1
```
HTTP 200
[Asserts]
jsonpath "$.results.bindings" isCollection

# Step 2b: SELECT via GET with Bearer token → 200 (SPARQL 1.1 Protocol §2.1.1)
GET {{gateway}}/sparql?query=SELECT%20*%20WHERE%20%7B%7D%20LIMIT%201
Accept: application/sparql-results+json
Authorization: Bearer {{vp_token}}
HTTP 200
[Asserts]
jsonpath "$.results.bindings" isCollection

# Step 3: UPDATE with Bearer token → 204
POST {{gateway}}/sparql/update
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer {{vp_token}}

```
update=INSERT DATA { GRAPH <{{gateway}}/graph/test-auth> { <urn:auth:test> <urn:p> "ok" } }
```
HTTP 204

# Step 4: Verify the insert worked
POST {{gateway}}/sparql
Content-Type: application/sparql-query
Accept: application/sparql-results+json
Authorization: Bearer {{vp_token}}
```
SELECT ?o WHERE { GRAPH <{{gateway}}/graph/test-auth> { <urn:auth:test> <urn:p> ?o } }
```
HTTP 200
[Asserts]
jsonpath "$.results.bindings[0].o.value" == "ok"

# Step 5: Clean up
POST {{gateway}}/sparql/update
Content-Type: application/x-www-form-urlencoded
Authorization: Bearer {{vp_token}}

```
update=DROP SILENT GRAPH <{{gateway}}/graph/test-auth>
```
HTTP 204
