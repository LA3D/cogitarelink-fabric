# Phase 2 — D12: GET /fabric/registry returns Turtle with FabricNode
# Content-negotiated registry endpoint

GET {{gateway}}/fabric/registry
Accept: text/turtle
HTTP 200
Content-Type: text/turtle
[Asserts]
body contains "FabricNode"
body contains "nodeDID"
body contains "did:webvh:"
body contains "sparqlEndpoint"
body contains "voidEndpoint"
