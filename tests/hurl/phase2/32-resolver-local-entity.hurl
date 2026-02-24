# Phase 2 — DID resolver: local entity URI deref returns notFound for missing entity (D25)

GET {{gateway}}/1.0/identifiers/http://localhost:8080/entity/00000000-0000-7000-8000-000000000000
HTTP 404
[Asserts]
jsonpath "$.didResolutionMetadata.error" == "notFound"
