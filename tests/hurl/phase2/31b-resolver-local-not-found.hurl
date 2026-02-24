# Phase 2 — DID resolver: local did:webvh with wrong SCID returns notFound (D25)

GET {{gateway}}/1.0/identifiers/did:webvh:nonexistent999:localhost%3A8080
HTTP 404
[Asserts]
jsonpath "$.didResolutionMetadata.error" == "notFound"
