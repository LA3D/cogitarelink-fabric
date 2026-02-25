# Phase 2 — D12/D19: Co-signed VC structure verification
# Verify both proofs have correct DataIntegrityProof structure

# First admit self to get a co-signed VC
POST {{gateway}}/fabric/admission
Content-Type: application/json
```json
{"nodeBase": "{{gateway}}"}
```
HTTP 201
[Asserts]
# Original proof
jsonpath "$.proof[0].type" == "DataIntegrityProof"
jsonpath "$.proof[0].cryptosuite" == "eddsa-jcs-2022"
jsonpath "$.proof[0].proofPurpose" == "assertionMethod"
jsonpath "$.proof[0].proofValue" startsWith "z"
jsonpath "$.proof[0].verificationMethod" contains "did:webvh:"
# Witness co-signature
jsonpath "$.proof[1].type" == "DataIntegrityProof"
jsonpath "$.proof[1].cryptosuite" == "eddsa-jcs-2022"
jsonpath "$.proof[1].proofPurpose" == "assertionMethod"
jsonpath "$.proof[1].proofValue" startsWith "z"
jsonpath "$.proof[1].verificationMethod" contains "did:webvh:"
jsonpath "$.proof[1].previousProof" startsWith "urn:uuid:"
