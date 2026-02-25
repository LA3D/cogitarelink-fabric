# Phase 2 — D26: relatedResource content integrity in conformance VC
# Verify VC contains relatedResource entries with SHA-256 digest hashes

GET {{gateway}}/.well-known/conformance-vc.json
HTTP 200
[Asserts]
jsonpath "$.relatedResource" count == 3
jsonpath "$.relatedResource[0].id" contains "/.well-known/void"
jsonpath "$.relatedResource[0].digestMultibase" startsWith "z"
jsonpath "$.relatedResource[0].digestSRI" startsWith "sha256-"
jsonpath "$.relatedResource[0].mediaType" exists
jsonpath "$.relatedResource[1].id" contains "/.well-known/shacl"
jsonpath "$.relatedResource[1].digestMultibase" startsWith "z"
jsonpath "$.relatedResource[2].id" contains "/.well-known/sparql-examples"
jsonpath "$.relatedResource[2].digestMultibase" startsWith "z"
