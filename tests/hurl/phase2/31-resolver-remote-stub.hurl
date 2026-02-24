# Phase 2 — DID resolver: remote did:webvh returns methodNotSupported (D25)
# Remote resolution is stubbed in Phase 2; will be implemented in Phase 3.

GET {{gateway}}/1.0/identifiers/did:webvh:nonexistent123:example.com%3A8080
HTTP 501
[Asserts]
jsonpath "$.didResolutionMetadata.error" == "methodNotSupported"
