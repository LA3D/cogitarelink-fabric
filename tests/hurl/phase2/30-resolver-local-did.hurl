# Phase 2 — DID resolver: local did:webvh (D3, D5, D25)
# Capture node DID from Credo health, then resolve via gateway.

GET http://localhost:3000/health
HTTP 200
[Captures]
node_did: jsonpath "$.did"

GET {{gateway}}/1.0/identifiers/{{node_did}}
HTTP 200
[Asserts]
jsonpath "$.didDocument.id" exists
jsonpath "$.didResolutionMetadata.contentType" == "application/did+ld+json"
jsonpath "$.didDocumentMetadata" exists
