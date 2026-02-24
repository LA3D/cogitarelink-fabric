# Phase 2 — Conformance VC as service directory (D12, D25)

GET {{gateway}}/.well-known/conformance-vc.json
HTTP 200
[Asserts]
jsonpath "$.credentialSubject.voidEndpoint" contains "/.well-known/void"
jsonpath "$.credentialSubject.sparqlExamplesEndpoint" contains "/.well-known/sparql-examples"
jsonpath "$.credentialSubject.resolverEndpoint" contains "/1.0/identifiers/"
jsonpath "$.credentialSubject.ldnInbox" contains "/inbox"
jsonpath "$.credentialSubject.sparqlEndpoint" contains "/sparql"
jsonpath "$.credentialSubject.shaclEndpoint" contains "/.well-known/shacl"
