---
paths: ["**/*.ts"]
---

# TypeScript Patterns (Credo-TS sidecar)

## Credo initialization
```typescript
import { Agent } from "@credo-ts/core";
import { agentDependencies } from "@credo-ts/node";
import { AskarModule } from "@credo-ts/askar";
import { WebVhDidRegistrar, WebVhDidResolver } from "@credo-ts/webvh";

const agent = new Agent({
  config: { label: "fabric-node-sidecar", walletConfig: { id: "fabric", key: process.env.WALLET_KEY! } },
  dependencies: agentDependencies,
  modules: { askar: new AskarModule({ ariesAskar }), /* DID modules */ },
});
await agent.initialize();
```

## VC 2.0 Data Integrity Proofs (not JWT)
Use `eddsa-rdfc-2022` cryptosuite:
```typescript
const vc = await agent.credentials.issue({
  credentialRecord: { type: ["VerifiableCredential", "AgentAuthorizationCredential"], ... },
  proofType: "DataIntegrityProof",
  proofOptions: { cryptosuite: "eddsa-rdfc-2022" },
});
```

## Multi-proof chaining (D19)
Use `previousProof` for HitL dual-proof:
```typescript
// Second proof references first
const proof2 = {
  type: "DataIntegrityProof",
  previousProof: proof1.id,  // chain reference
  ...
};
```

## did:webvh (D3, D5)
- Node DID: `did:webvh:{node-domain}` (fabric endpoint identity)
- Agent DID: `did:webvh:{agent-domain}` (separate from node DID)
- Witness: `did:key` (required by did:webvh v1.0 spec for witness signing)
- `digestMultibase` in VCs for content integrity (D5)

## Express wrapper
Keep thin — business logic stays in Python layer:
```typescript
app.post("/credentials/issue", async (req, res) => {
  const vc = await issueCredential(agent, req.body);
  res.json(vc);
});
```

## Phase 1 mock path
Before full Credo integration, use mock VC from `credentials/claude-code-agent-vc.json`.
Sidecar returns mock VCs with valid structure for JSON-LD round-trip testing.
Flag mock VCs with `"mock": true` in `credentialSubject` (not in production path).

## Volumes
Share `did.jsonl` between FastAPI and Credo via Docker volume (D8).
Credo writes; FastAPI reads for DID-in-header verification.
