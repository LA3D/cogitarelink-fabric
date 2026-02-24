# Phase 2 — VC verification negative test
# Tampered VC must fail verification.

POST http://localhost:3000/credentials/verify
Content-Type: application/json
{"@context":["https://www.w3.org/ns/credentials/v2"],"type":["VerifiableCredential","FabricConformanceCredential"],"issuer":"did:webvh:fake:123","issuanceDate":"2026-01-01T00:00:00Z","credentialSubject":{"conformsTo":"https://w3id.org/cogitarelink/fabric#CoreProfile"},"proof":{"type":"DataIntegrityProof","cryptosuite":"eddsa-jcs-2022","verificationMethod":"did:webvh:fake:123#key-1","proofPurpose":"assertionMethod","proofValue":"zTAMPERED_INVALID_PROOF_VALUE"}}

HTTP 200
[Asserts]
jsonpath "$.verified" == false
