# Phase 2 — D12: Registry self-entry after bootstrap
# Verify /graph/registry contains self-entry with correct DID + endpoints

# Query registry graph for FabricNode entries
POST {{gateway}}/sparql
Content-Type: application/sparql-query
Accept: application/sparql-results+json
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
