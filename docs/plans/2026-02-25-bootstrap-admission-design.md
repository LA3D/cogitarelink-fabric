# Bootstrap Admission, Agent Registration, and Self-Catalog — Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement D12 (bootstrap node admission with witness co-signing), D13/D14 (agent registration with AgentAuthorizationCredential), and D23 Stage 1 (self-catalog from VoID).

**Architecture:** Single-node self-registration at startup. Admission endpoint accepts remote nodes, verifies their VC + D26 hashes, co-signs with `previousProof` chaining, and adds to `/graph/registry`. Agent registration creates agent DIDs under the node domain and issues role-based credentials. Self-catalog extracts DCAT dataset descriptions from the node's own VoID.

**Tech Stack:** FastAPI (Python), Credo-TS (TypeScript), Oxigraph (SPARQL), HURL (conformance tests), pytest (unit tests).

---

## Scope Decisions

- **Single-node self-registration** — bootstrap node registers itself in `/graph/registry` at startup. Real multi-node in Phase 3.
- **Admission endpoint testable via HURL** — self-admission test (node admits itself) validates the full flow.
- **Witness co-signing included** — `POST /credentials/cosign` on Credo adds second `DataIntegrityProof` with `previousProof` chain.
- **Agent registration issues credentials only** — no enforcement gate on SPARQL UPDATE (that's Week 6-7, VC-gated access).
- **Self-catalog only** — bootstrap extracts DCAT from own VoID. Harvest from remote nodes happens at admission time when second node exists.

---

## Section 1: Bootstrap Self-Registration

At startup, after Credo creates the node DID and conformance VC, `bootstrap_data.py` inserts a self-entry into `/graph/registry`.

### Registry entry structure

```turtle
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .
@prefix dct:    <http://purl.org/dc/terms/> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .

<did:webvh:SCID:localhost%3A8080> a fabric:FabricNode ;
    fabric:nodeDID "did:webvh:SCID:localhost%3A8080" ;
    fabric:conformanceCredential <http://localhost:8080/.well-known/conformance-vc.json> ;
    fabric:voidEndpoint <http://localhost:8080/.well-known/void> ;
    fabric:sparqlEndpoint <http://localhost:8080/sparql> ;
    fabric:ldnInbox <http://localhost:8080/inbox> ;
    fabric:resolverEndpoint <http://localhost:8080/1.0/identifiers/> ;
    dct:conformsTo <https://w3id.org/cogitarelink/fabric#CoreProfile> ;
    fabric:registeredAt "2026-02-25T..."^^xsd:dateTime ;
    fabric:registeredBy <did:webvh:SCID:localhost%3A8080> .
```

### Bootstrap sequencing

1. Oxigraph starts → FastAPI starts → Credo creates node DID + issues conformance VC
2. `bootstrap_data.py` enhanced:
   - Load all TBox ontologies (`ontology/*.ttl`) into named graphs
   - Read conformance VC from `/shared/conformance-vc.json` to extract node DID
   - INSERT self-entry into `/graph/registry`
   - Extract DCAT from VoID, INSERT into `/graph/catalog`

### New route

- `GET /fabric/registry` — SPARQL CONSTRUCT against `/graph/registry`, returns Turtle or JSON-LD (content-negotiated)

---

## Section 2: Admission Endpoint with Witness Co-Signing

`POST /fabric/admission` accepts a node wanting to join the fabric.

### Request

```json
{ "nodeBase": "https://remote-node.example.org" }
```

### Flow

1. Fetch `{nodeBase}/.well-known/did.json` — get DID document
2. Fetch `{nodeBase}/.well-known/conformance-vc.json` — get conformance VC (self-signed)
3. Verify VC `eddsa-jcs-2022` proof (call Credo `/credentials/verify`)
4. Fetch `{nodeBase}/.well-known/void` — verify `dct:conformsTo fabric:CoreProfile`
5. Verify `relatedResource` hashes match fetched artifacts (D26 `verify_related_resources()`)
6. **Co-sign the VC**: call Credo `POST /credentials/cosign` — adds second `DataIntegrityProof` with `previousProof` chain
7. INSERT remote node entry into `/graph/registry` with `fabric:registeredBy` = bootstrap DID
8. Return 201 with co-signed VC

### Co-signed VC structure (VC 2.0 multi-proof)

```json
{
  "type": ["VerifiableCredential", "FabricConformanceCredential"],
  "issuer": "did:webvh:SCID:remote-node",
  "credentialSubject": { "..." },
  "proof": [
    {
      "type": "DataIntegrityProof",
      "cryptosuite": "eddsa-jcs-2022",
      "verificationMethod": "did:webvh:SCID:remote-node#key-0",
      "proofPurpose": "assertionMethod",
      "proofValue": "z..."
    },
    {
      "type": "DataIntegrityProof",
      "cryptosuite": "eddsa-jcs-2022",
      "verificationMethod": "did:webvh:SCID:bootstrap-node#key-0",
      "proofPurpose": "assertionMethod",
      "previousProof": "urn:uuid:...",
      "proofValue": "z..."
    }
  ]
}
```

### Credo sidecar changes

New route: `POST /credentials/cosign`
- Input: existing VC JSON
- Verify original proof
- Generate proof ID (`urn:uuid:...`) for original proof if missing
- Sign JCS-canonicalized credential with bootstrap node's Ed25519 key
- Set `previousProof` on new proof referencing original proof ID
- Return dual-proof VC

### Error cases

- Invalid VC proof → 403 Forbidden
- D26 hash mismatch → 409 Conflict (artifacts changed since VC was issued)
- VoID missing `dct:conformsTo fabric:CoreProfile` → 422 Unprocessable

---

## Section 3: Agent Registration

`POST /agents/register` on Credo sidecar creates agent identity and issues `AgentAuthorizationCredential`.

### Request

```json
{
  "agentRole": "IngestCuratorRole",
  "authorizedGraphs": ["/graph/observations", "/graph/entities"],
  "authorizedOperations": ["read", "write"]
}
```

### Flow

1. Credo creates agent `did:webvh` — `did:webvh:SCID:{node-domain}:agents:{uuidv7}`
2. Issues `AgentAuthorizationCredential` VC signed by node key:
   ```json
   {
     "type": ["VerifiableCredential", "AgentAuthorizationCredential"],
     "issuer": "did:webvh:SCID:node-domain",
     "credentialSubject": {
       "id": "did:webvh:SCID:node-domain:agents:uuid7",
       "agentRole": "fabric:IngestCuratorRole",
       "authorizedGraphs": ["/graph/observations", "/graph/entities"],
       "authorizedOperations": ["read", "write"],
       "homeNode": "did:webvh:SCID:node-domain"
     }
   }
   ```
3. Writes agent DID log + credential to `/shared/agents/{uuid7}/`
4. FastAPI inserts agent record into `/graph/agents`
5. Returns 201 with agent DID + credential

### FastAPI routes

- `GET /agents` — list registered agents from `/graph/agents`
- `GET /agents/{agent_id}` — single agent record (CONSTRUCT from `/graph/agents`)

### No enforcement

Credential is issued and stored. SPARQL UPDATE does not check for it — that's Week 6-7 (VC-gated access).

---

## Section 4: Self-Catalog (D23 Stage 1)

At bootstrap, extract DCAT dataset descriptions from own VoID, store in `/graph/catalog`.

### DCAT structure

Each `void:subset` in VoID becomes a `dcat:Dataset`:

```turtle
<http://localhost:8080/graph/observations> a dcat:Dataset ;
    dct:title "Observations" ;
    dcat:keyword "sosa", "observation" ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ;
    dcat:accessService <http://localhost:8080/sparql> ;
    dct:publisher <did:webvh:SCID:localhost%3A8080> ;
    dct:issued "2026-02-25T..."^^xsd:dateTime .
```

### Route

- `GET /.well-known/catalog` — SPARQL CONSTRUCT against `/graph/catalog`, content-negotiated

### Bootstrap enhancement

After loading TBox + inserting registry self-entry, parse VoID template → extract subset declarations → generate DCAT triples → INSERT into `/graph/catalog`.

---

## Section 5: Testing Strategy

### HURL conformance tests (Phase 2, 40-47)

| # | Test | Verifies |
|---|------|----------|
| 40 | Registry self-entry | After bootstrap, `/graph/registry` contains self-entry with correct DID + endpoints |
| 41 | Registry route | `GET /fabric/registry` returns Turtle with `fabric:FabricNode` |
| 42 | Admission endpoint | `POST /fabric/admission` with self-URL → 201 + registry entry |
| 43 | Co-signed VC | Returned VC has proof array with `previousProof` |
| 44 | Agent register | `POST /agents/register` → 201 + agent DID |
| 45 | Agent credential | Returned VC has correct role + authorized graphs |
| 46 | Agents list | `GET /agents` returns at least one agent |
| 47 | Self-catalog | `GET /.well-known/catalog` returns DCAT dataset |

### pytest unit tests

- Registry helpers: SPARQL INSERT/query for registry entries
- Admission validation: mock VC verification, D26 hash check
- Agent registration helpers: agent DID path generation, credential structure
- Catalog extraction: VoID → DCAT transformation

### Error cases

- Admission with invalid VC → 403
- Admission with D26 hash mismatch → 409
- Agent registration with unknown role → 400

---

## Changes Summary

### Credo sidecar (`fabric/credo/src/index.ts`)
- New route: `POST /credentials/cosign` — multi-proof with `previousProof`
- New route: `POST /agents/register` — create agent DID + issue AgentAuthorizationCredential
- Shared volume: write agent files to `/shared/agents/{uuid7}/`

### FastAPI gateway (`fabric/node/main.py`)
- New route: `GET /fabric/registry` — query `/graph/registry`
- New route: `POST /fabric/admission` — admission flow
- New route: `GET /.well-known/catalog` — DCAT catalog
- New route: `GET /agents` — list agents
- New route: `GET /agents/{agent_id}` — single agent

### Bootstrap script (`scripts/bootstrap_data.py`)
- Load all TBox ontologies into named graphs
- Initialize `/graph/registry` with self-entry
- Initialize `/graph/catalog` with self-catalog from VoID

### New files
- `fabric/node/registry.py` — registry/admission helper functions (pure Python, no FastAPI dep)
- `fabric/node/catalog.py` — VoID→DCAT extraction helpers
- `tests/hurl/phase2/40-47` — 8 HURL tests
- `tests/pytest/unit/test_registry.py` — registry unit tests
- `tests/pytest/unit/test_catalog.py` — catalog unit tests
