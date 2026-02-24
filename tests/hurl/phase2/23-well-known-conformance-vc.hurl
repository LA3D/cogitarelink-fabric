# Phase 2 — FastAPI conformance VC route (D12, D8)
# Served from shared volume, written at Credo startup.

GET {{gateway}}/.well-known/conformance-vc.json

HTTP 200
[Asserts]
jsonpath "$.proof" exists
jsonpath "$.proof.type" == "DataIntegrityProof"
jsonpath "$.type[1]" == "FabricConformanceCredential"
jsonpath "$.credentialSubject.conformsTo" == "https://w3id.org/cogitarelink/fabric#CoreProfile"
