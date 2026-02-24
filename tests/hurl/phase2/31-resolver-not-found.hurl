# Phase 2 — DID resolver: unknown DID returns notFound (D25)

GET {{gateway}}/1.0/identifiers/did:webvh:example.com%3A8080:nonexistent123
HTTP 501
[Asserts]
jsonpath "$.didResolutionMetadata.error" == "methodNotSupported"
