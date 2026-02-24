# Phase 2 — VC issuance route (D12)
# Issues a FabricConformanceCredential with DataIntegrityProof (eddsa-jcs-2022).

POST http://localhost:3000/credentials/issue
Content-Type: application/json
{"type":"FabricConformanceCredential","credentialSubject":{"conformsTo":"https://w3id.org/cogitarelink/fabric#CoreProfile"}}

HTTP 200
[Asserts]
jsonpath "$.proof" exists
jsonpath "$.proof.type" == "DataIntegrityProof"
jsonpath "$.proof.cryptosuite" == "eddsa-jcs-2022"
jsonpath "$.proof.proofValue" startsWith "z"
jsonpath "$.type[0]" == "VerifiableCredential"
jsonpath "$.type[1]" == "FabricConformanceCredential"
jsonpath "$.issuer" startsWith "did:webvh:"
