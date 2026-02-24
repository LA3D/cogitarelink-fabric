---
paths: ["**/*.ts"]
---

# TypeScript Patterns (Credo-TS sidecar)

## Credo 0.6.x initialization
```typescript
import { Agent, ConsoleLogger, DidsModule, Hasher, Kms, LogLevel, TypedArrayEncoder } from '@credo-ts/core'
import { agentDependencies, NodeKeyManagementService, NodeInMemoryKeyManagementStorage } from '@credo-ts/node'
import { AskarModule } from '@credo-ts/askar'
import { askar } from '@openwallet-foundation/askar-nodejs'
import { WebVhModule, WebVhDidRegistrar, WebVhDidResolver } from '@credo-ts/webvh'

const agent = new Agent({
  config: { label: 'fabric-node-sidecar', allowInsecureHttpUrls: true, logger: new ConsoleLogger(LogLevel.warn) },
  dependencies: agentDependencies,
  modules: {
    askar: new AskarModule({ askar, store: { id: 'fabric-node-wallet', key: process.env.WALLET_KEY! } }),
    kms: new Kms.KeyManagementModule({ backends: [new NodeKeyManagementService(new NodeInMemoryKeyManagementStorage())] }),
    webvh: new WebVhModule(),
    dids: new DidsModule({ registrars: [new WebVhDidRegistrar()], resolvers: [new WebVhDidResolver()] }),
  },
})
await agent.initialize()
```

**Key 0.6.x changes from 0.5.x:**
- `walletConfig` moved from `InitConfig` to `AskarModule({ store: { id, key } })`
- `@hyperledger/aries-askar-nodejs` → `@openwallet-foundation/askar-nodejs`
- `Kms.KeyManagementModule` required (new in 0.6.x)
- `DidsModule` must explicitly include `WebVhDidRegistrar`/`WebVhDidResolver` — auto-registration doesn't discover `WebVhModule` singletons

## did:webvh creation
```typescript
// Domain must be percent-encoded (: → %3A)
const result = await agent.dids.create({ method: 'webvh', domain: 'localhost%3A8080' } as any)
const did = result.didState.did  // "did:webvh:localhost%3A8080:..."

// DID log is in wallet metadata (not a separate API)
const [record] = await agent.dids.getCreatedDids({ did })
const log = record.metadata.get('log')  // array of log entries
const logLines = log.map(entry => JSON.stringify(entry)).join('\n')
```

## VC 2.0 Data Integrity Proofs — eddsa-jcs-2022 (inline)

Credo 0.6.x W3cJsonLdCredentialService has a broken ESM import in `nativeDocumentLoader.mjs`
and JSON-LD safe mode rejects custom credential types. Use inline JCS signing instead:

```typescript
import { canonicalize } from 'json-canonicalize'

// JCS hash: canonicalize → sha-256
function jcsHash(obj: unknown): Uint8Array {
  return Hasher.hash(TypedArrayEncoder.fromString(canonicalize(obj)), 'sha-256')
}

// Sign: hash(proofOptions) || hash(document) → Ed25519 via KMS
const keyApi = agent.agentContext.dependencyManager.resolve(Kms.KeyManagementApi)
const { signature } = await keyApi.sign({ keyId, algorithm: 'EdDSA', data: hashData })
```

**Why not Credo's built-in VC signing:**
1. `nativeDocumentLoader.mjs` has broken ESM import (missing `.js` extension) — crashes on `@digitalcredentials/jsonld`
2. JSON-LD safe mode rejects custom types (`FabricConformanceCredential`) not in `@context`
3. `W3cCredential` class serializes `expirationDate: undefined` which breaks validation
4. `@credo-ts/webvh` package `exports` field blocks deep imports of `EddsaJcs2022Cryptosuite`

## Multi-proof chaining (D19)
Use `previousProof` for HitL dual-proof:
```typescript
const proof2 = {
  type: 'DataIntegrityProof',
  previousProof: proof1.id,
  ...
}
```

## did:webvh (D3, D5)
- Node DID: `did:webvh:{encoded-domain}:{scid}` (fabric endpoint identity)
- Agent DID: `did:webvh:{agent-domain}` (separate from node DID — Phase 3)
- Witness: `did:key` (required by did:webvh spec for witness signing)
- `digestMultibase` in VCs for content integrity (D5)

## Express wrapper
Keep thin — business logic stays in Python layer:
```typescript
app.post('/credentials/issue', async (req, res) => {
  const { type, credentialSubject } = req.body
  if (!type || !credentialSubject) return res.status(400).json({ error: 'type and credentialSubject required' })
  const vc = await issueVC(types, credentialSubject)
  res.json(vc)
})
```

## Shared volume (D8)
Credo writes to `/shared`; FastAPI reads (read-only mount):
- `/shared/did.jsonl` — DID log (JSONL, one entry per line)
- `/shared/conformance-vc.json` — self-issued FabricConformanceCredential

## Dockerfile
- Use `node:20-slim` (not 22 — ESM compat)
- Native build deps: `python3 make g++` (required for `@openwallet-foundation/askar-nodejs`)
- `platform: linux/amd64` in docker-compose (Apple Silicon Rosetta for Askar)
- `npx ts-node --transpile-only` — skip type checking at runtime
