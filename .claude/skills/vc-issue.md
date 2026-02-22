# /vc-issue

Issue a W3C Verifiable Credential via Credo sidecar. Supports mock path for Phase 1.

## Usage
```
/vc-issue <role> [--subject <did>] [--mock]
```
Roles: AgentAuthorization, FabricConformance, FabricDelegation
Example: `/vc-issue AgentAuthorization --subject did:webvh:agent.fabric.example.org --mock`

## Supported Credential Types

### AgentAuthorizationCredential (D13)
```json
{
  "type": ["VerifiableCredential", "AgentAuthorizationCredential"],
  "credentialSubject": {
    "id": "{agent-did}",
    "fabric:hasRole": "fabric:IngestCuratorRole",
    "fabric:authorizedEndpoint": "https://node.example.org/sparql",
    "fabric:permittedGraphs": ["/graph/observations", "/graph/pending"]
  }
}
```

### FabricConformanceCredential (D12)
```json
{
  "type": ["VerifiableCredential", "FabricConformanceCredential"],
  "credentialSubject": {
    "id": "{node-did}",
    "dct:conformsTo": "fabric:CoreProfile",
    "fabric:conformanceCheckDate": "{iso-date}"
  }
}
```

### FabricDelegationCredential (D19, D15)
```json
{
  "type": ["VerifiableCredential", "FabricDelegationCredential"],
  "credentialSubject": {
    "id": "{agent-did}",
    "fabric:delegatedBy": "{human-did-or-orcid}",
    "fabric:sessionScope": "{session-description}",
    "fabric:expiresAt": "{iso-datetime}"
  }
}
```

## Phase 1 Mock Path (`--mock`)
- Generates valid JSON-LD VC structure without Credo sidecar running
- Adds `"mock": true` to `credentialSubject` — NOT a real VC, for schema testing only
- Saves to `credentials/{type}-{uuid}.json`
- Useful for validating JSON-LD context round-trips before Phase 2

## Phase 2 Live Path (Credo running)
```bash
POST http://localhost:3000/credentials/issue
Content-Type: application/json
{credential JSON}
```
Returns VC with `DataIntegrityProof` (`eddsa-rdfc-2022`).
For HitL dual-proof (D19): issue second VC with `previousProof` referencing first proof's `id`.
