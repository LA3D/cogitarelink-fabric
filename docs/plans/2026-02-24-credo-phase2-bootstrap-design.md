# Credo Phase 2 Bootstrap — Design

**Date**: 2026-02-24
**Scope**: Fix Credo 0.6.x initialization, create node `did:webvh`, issue `FabricConformanceCredential`
**Decisions**: D3, D5, D8, D12, D13, D25

---

## Problem

The Credo sidecar exists as a Phase 1 skeleton: Express `/health` works but
`agent.initialize()` fails because `package.json` pins `@credo-ts/*@^0.6.0` while
code imports from the old `@hyperledger/aries-askar-nodejs` package. In 0.6.x,
Aries Askar moved to `@openwallet-foundation/askar-nodejs` and wallet configuration
moved from `Agent.InitConfig.walletConfig` into `AskarModule({ store: ... })`.

Phase 2 requires a functioning identity layer: node DID, VC issuance, and
`.well-known/` integration with FastAPI.

## Approach

Incremental fix — build on the working Express skeleton, fix the known breakage,
add capabilities one at a time with HURL tests at each step.

---

## Section 1: Fix Credo 0.6.x Initialization

### Package changes (`fabric/credo/package.json`)

Remove:
- `@hyperledger/aries-askar-nodejs`

Add:
- `@openwallet-foundation/askar-nodejs` (peer dep of `@credo-ts/askar@0.6.x`)
- `@credo-ts/webvh` (^0.6.0) — `did:webvh` registrar/resolver
- `@credo-ts/dids` if not included in core (check — may be in `@credo-ts/core`)

### Code changes (`fabric/credo/src/index.ts`)

```typescript
// OLD (broken)
import { ariesAskar } from '@hyperledger/aries-askar-nodejs'
const config: InitConfig = {
  label: 'cogitarelink-fabric-credo',
  walletConfig: { id: 'fabric-node-wallet', key: '...' },
}
new AskarModule({ ariesAskar })

// NEW (0.6.x — from mediator.ts sample)
import { askar } from '@openwallet-foundation/askar-nodejs'
const config: InitConfig = {
  label: 'cogitarelink-fabric-credo',
  // walletConfig removed — now in AskarModule
}
new AskarModule({
  askar,
  store: { id: 'fabric-node-wallet', key: process.env.WALLET_KEY! },
})
```

### Test

Update `tests/hurl/phase1/02b-credo-health.hurl`:
```hurl
GET http://localhost:3000/health
HTTP 200
[Asserts]
jsonpath "$.agent" == "ready"
```

---

## Section 2: did:webvh DID Creation

### Agent module configuration

```typescript
import { WebVhModule, WebVhDidRegistrar, WebVhDidResolver } from '@credo-ts/webvh'
import { DidsModule } from '@credo-ts/core'

modules: {
  askar: new AskarModule({ askar, store: { ... } }),
  webvh: new WebVhModule(),
  dids: new DidsModule({
    registrars: [new WebVhDidRegistrar()],
    resolvers: [new WebVhDidResolver()],
  }),
}
```

### New sidecar routes

**`POST /dids/node`** — Create or retrieve node DID
- Domain from `NODE_DOMAIN` env var (default: `localhost:8080`)
- Calls `agent.dids.create({ method: 'webvh', domain })`
- Writes `did.jsonl` to shared volume at `/shared/did.jsonl`
- Returns `{ did, didDocument }`

**`GET /did.jsonl`** — Serve DID log file
- Reads from `/shared/did.jsonl`
- Content-Type: `application/jsonl`

### DID Document service endpoints (D13, D25)

The node's DID document should include:
- `sparqlEndpoint`: `{NODE_BASE}/sparql`
- `shacl`: `{NODE_BASE}/.well-known/shacl`
- `ldp:inbox`: `{NODE_BASE}/inbox` (D25)
- `conformanceVC`: `{NODE_BASE}/.well-known/conformance-vc.json`

### Docker Compose change

Add shared volume between credo-sidecar and fabric-node:
```yaml
services:
  fabric-node:
    volumes:
      - did-data:/shared:ro    # read-only for FastAPI
  credo-sidecar:
    volumes:
      - did-data:/shared       # read-write for Credo

volumes:
  did-data:
```

### FastAPI routes

- `GET /.well-known/did.jsonl` — reads `/shared/did.jsonl`
- `GET /.well-known/did.json` — reads `/shared/did.jsonl`, extracts latest DID document

### HURL tests

New `tests/hurl/phase2/20-credo-did-create.hurl`:
```hurl
POST http://localhost:3000/dids/node
HTTP 200
[Asserts]
jsonpath "$.did" startsWith "did:webvh:"
jsonpath "$.didDocument" exists
```

New `tests/hurl/phase2/21-well-known-did.hurl`:
```hurl
GET http://localhost:8080/.well-known/did.jsonl
HTTP 200

GET http://localhost:8080/.well-known/did.json
HTTP 200
[Asserts]
jsonpath "$.id" startsWith "did:webvh:"
```

---

## Section 3: VC Issuance — FabricConformanceCredential

### New sidecar routes

**`POST /credentials/issue`** — Issue a W3C VC 2.0 credential
- Body: `{ type, credentialSubject, ... }`
- Uses Data Integrity proofs (`eddsa-rdfc-2022` cryptosuite)
- Issuer: node's `did:webvh`
- Returns signed VC as JSON-LD

**`POST /credentials/verify`** — Verify a presented VC
- Body: signed VC JSON-LD
- Checks: proof integrity, issuer DID resolution, expiry
- Returns `{ verified: boolean, checks: string[] }`

### FabricConformanceCredential (D12)

First concrete VC — self-attestation for bootstrap node:
```json
{
  "@context": ["https://www.w3.org/ns/credentials/v2"],
  "type": ["VerifiableCredential", "FabricConformanceCredential"],
  "issuer": "did:webvh:SCID:localhost%3A8080",
  "credentialSubject": {
    "id": "did:webvh:SCID:localhost%3A8080",
    "conformsTo": "https://w3id.org/cogitarelink/fabric#CoreProfile",
    "sparqlEndpoint": "http://localhost:8080/sparql",
    "shaclEndpoint": "http://localhost:8080/.well-known/shacl",
    "attestedAt": "2026-02-24T..."
  },
  "proof": { "type": "DataIntegrityProof", "cryptosuite": "eddsa-rdfc-2022", "..." }
}
```

Stored at `/shared/conformance-vc.json`.

### FastAPI route

- `GET /.well-known/conformance-vc.json` — reads from shared volume

### HURL tests

New `tests/hurl/phase2/22-credo-vc-issue.hurl`:
```hurl
POST http://localhost:3000/credentials/issue
Content-Type: application/json
{
  "type": "FabricConformanceCredential",
  "credentialSubject": {
    "conformsTo": "https://w3id.org/cogitarelink/fabric#CoreProfile"
  }
}
HTTP 200
[Asserts]
jsonpath "$.proof" exists
jsonpath "$.type[1]" == "FabricConformanceCredential"
```

New `tests/hurl/phase2/23-well-known-conformance-vc.hurl`:
```hurl
GET http://localhost:8080/.well-known/conformance-vc.json
HTTP 200
[Asserts]
jsonpath "$.type[1]" == "FabricConformanceCredential"
jsonpath "$.proof" exists
```

New `tests/hurl/phase2/24-credo-vc-verify.hurl`:
```hurl
# Verify the self-issued FabricConformanceCredential
# (This test depends on 22 having run first)
```

---

## Section 4: Startup Orchestration

On container start, the sidecar auto-bootstraps:

1. Initialize Credo agent (Askar wallet)
2. Check if node DID exists in wallet → if not, create `did:webvh`
3. Write `did.jsonl` to `/shared/did.jsonl`
4. Self-issue `FabricConformanceCredential`
5. Write VC to `/shared/conformance-vc.json`
6. Report ready on `/health`

### Health endpoint enrichment

```json
{
  "status": "ok",
  "agent": "ready",
  "did": "did:webvh:SCID:localhost%3A8080",
  "conformanceVC": true
}
```

### Docker Compose startup order

```yaml
credo-sidecar:
  depends_on:
    fabric-node:
      condition: service_healthy    # FastAPI must be up before Credo bootstraps
```

Wait — this creates a circular dependency if FastAPI depends on Credo for DID
content. Resolution: FastAPI serves `.well-known/did.*` and `conformance-vc.json`
with 404 until the files appear on the shared volume. No startup dependency on
Credo — eventual consistency via filesystem.

Revised order:
- `fabric-node` depends on `oxigraph` (data layer)
- `credo-sidecar` depends on `oxigraph` (no FastAPI dependency)
- FastAPI reads shared volume files lazily (404 until Credo writes them)

---

## Deliverables Summary

| Step | Sidecar Route | FastAPI Route | HURL Test |
|------|--------------|---------------|-----------|
| Fix init | — | — | `02b` updated (agent: ready) |
| Node DID | `POST /dids/node`, `GET /did.jsonl` | `GET /.well-known/did.jsonl`, `GET /.well-known/did.json` | `20`, `21` |
| VC issue | `POST /credentials/issue` | `GET /.well-known/conformance-vc.json` | `22`, `23` |
| VC verify | `POST /credentials/verify` | — | `24` |
| Bootstrap | Startup auto-init | — | Health test |

## Key Technical Risks

1. **`@credo-ts/webvh` 0.6.x API** — limited docs; may need to read source
2. **`did:webvh` with localhost domain** — URL encoding of port in SCID; test that resolution round-trips
3. **Askar native bindings on linux/amd64 (Rosetta)** — Phase 1 proved Express works; full agent init is untested on Rosetta with OWF Askar
4. **VC 2.0 Data Integrity proof format** — `eddsa-rdfc-2022` cryptosuite availability in Credo 0.6.x

## Sources

- [Credo mediator sample](https://github.com/openwallet-foundation/credo-ts/blob/main/samples/mediator.ts) — 0.6.x AskarModule pattern
- [@credo-ts/webvh npm](https://www.npmjs.com/package/@credo-ts/webvh) — 0.6.2 with did:webvh support
- [Credo 0.6 release discussion](https://github.com/openwallet-foundation/credo-ts/discussions/1861) — breaking changes
- [Credo releases](https://github.com/openwallet-foundation/credo-ts/releases)
- [Agent config docs](https://credo.js.org/guides/tutorials/agent-config)
