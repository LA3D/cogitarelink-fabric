# Phase 2 — D12: Registry self-entry after bootstrap
# Verify /graph/registry contains self-entry with correct DID + endpoints

# Auth setup: get VP token
POST {{gateway}}/test/create-vp
Content-Type: application/json
{"agentRole":"DevelopmentAgentRole","authorizedGraphs":["*"],"authorizedOperations":["read"]}
HTTP 201
[Captures]
vp_token: jsonpath "$.token"

# Query registry graph for FabricNode entries
POST {{gateway}}/sparql
Content-Type: application/sparql-query
Accept: application/sparql-results+json
Authorization: Bearer {{vp_token}}
```
PREFIX fabric: <https://w3id.org/cogitarelink/fabric#>
SELECT ?node ?did ?void ?sparql ?inbox WHERE {
  GRAPH <{{gateway}}/graph/registry> {
    ?node a fabric:FabricNode ;
        fabric:nodeDID ?did ;
        fabric:voidEndpoint ?void ;
        fabric:sparqlEndpoint ?sparql ;
        fabric:ldnInbox ?inbox .
  }
}
```
HTTP 200
[Asserts]
jsonpath "$.results.bindings" count >= 1
jsonpath "$.results.bindings[0].did.value" contains "did:webvh:"
jsonpath "$.results.bindings[0].void.value" contains "/.well-known/void"
jsonpath "$.results.bindings[0].sparql.value" contains "/sparql"
jsonpath "$.results.bindings[0].inbox.value" contains "/inbox"
