# Phase 2 — D13/D14: Agent credential structure verification
# Register agent, then verify credential has correct fields

POST {{gateway}}/agents/register
Content-Type: application/json
```json
{
  "agentRole": "QARole",
  "authorizedGraphs": ["/graph/observations"],
  "authorizedOperations": ["read"]
}
```
HTTP 201
[Asserts]
jsonpath "$.credential.type" includes "VerifiableCredential"
jsonpath "$.credential.type" includes "AgentAuthorizationCredential"
jsonpath "$.credential.issuer" contains "did:webvh:"
jsonpath "$.credential.credentialSubject.agentRole" == "fabric:QARole"
jsonpath "$.credential.credentialSubject.authorizedGraphs" includes "/graph/observations"
jsonpath "$.credential.credentialSubject.authorizedOperations" includes "read"
jsonpath "$.credential.credentialSubject.homeNode" contains "did:webvh:"
jsonpath "$.credential.proof.type" == "DataIntegrityProof"
jsonpath "$.credential.proof.proofValue" startsWith "z"
