# Phase 2 — D12: Admission endpoint (self-admission test)
# Node admits itself — validates the full admission flow

POST {{gateway}}/fabric/admission
Content-Type: application/json
```json
{"nodeBase": "{{gateway}}"}
```
HTTP 201
[Asserts]
jsonpath "$.type" includes "VerifiableCredential"
jsonpath "$.type" includes "FabricConformanceCredential"
jsonpath "$.issuer" contains "did:webvh:"
jsonpath "$.proof" count == 2
jsonpath "$.proof[1].previousProof" exists
