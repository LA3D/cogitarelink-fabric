# Phase 2 DID Integration — Design

**Date**: 2026-02-24
**Scope**: W3C DID Resolution HTTP API, W3C LDN inbox, conformance VC as service directory
**Decisions**: D3, D5, D8, D12, D25

---

## Problem

The Phase 2 bootstrap established node identity (did:webvh), VC issuance, and shared
volume integration. But there's no standard way for agents to:

1. **Resolve identifiers** — given a DID or HTTP URI, get the document behind it
2. **Discover services** — given a node DID, find its SPARQL endpoint, SHACL shapes, inbox
3. **Send notifications** — push JSON-LD messages to other nodes/agents (catalog updates,
   admission requests, trust gap escalations)

These are prerequisites for multi-node federation (Phase 3) and VC-gated access (Phase 2
Week 6-7).

## Design Principles

Stay as close to W3C standards as possible. Standards in LLM pretraining improve agent
performance and provide guardrails — the same thesis as SHACL/VoID self-description.

---

## Section 1: DID Resolver — W3C DID Resolution HTTP API

### Spec

[W3C DID Resolution v0.3](https://w3c.github.io/did-resolution/) — Editor's Draft.
Builds on [DID Core v1.0](https://www.w3.org/TR/did-core/) (W3C Recommendation).

### Route

`GET /1.0/identifiers/{identifier}` on the FastAPI gateway.

The path parameter captures the full identifier (DID or HTTP URI). Dispatch based on
identifier type:

| Identifier pattern | Resolution path | Implementation |
|---|---|---|
| `did:webvh:...` with local domain | Local | Read `/shared/did.jsonl`, extract DID document |
| `did:webvh:...` with remote domain | Remote | HTTP fetch `{decoded-domain}/.well-known/did.json` |
| `did:key:...` | Inline | Decode public key from DID (no network) |
| `https://{local-domain}/entity/{uuid}` | Local entity | Oxigraph CONSTRUCT (reuse existing entity logic) |
| `https://` (external) | HTTP dereference | httpx GET with content negotiation |
| Anything else | Error | `methodNotSupported` or `invalidDid` |

### Response Format — DID Resolution Result

For DID resolution:
```json
{
  "didDocument": {
    "id": "did:webvh:...",
    "@context": ["https://www.w3.org/ns/did/v1"],
    "verificationMethod": [...],
    "authentication": [...],
    "assertionMethod": [...]
  },
  "didResolutionMetadata": {
    "contentType": "application/did+ld+json"
  },
  "didDocumentMetadata": {
    "created": "2026-02-24T...",
    "updated": "2026-02-24T...",
    "versionId": "1"
  }
}
```

For HTTP URI dereferencing:
```json
{
  "content": { /* RDF as JSON-LD */ },
  "dereferencingMetadata": {
    "contentType": "application/ld+json"
  },
  "contentMetadata": {}
}
```

### Error Format

```json
{
  "didDocument": null,
  "didResolutionMetadata": {
    "error": "notFound",
    "message": "DID not found"
  },
  "didDocumentMetadata": {}
}
```

Standard error codes: `invalidDid` (400), `notFound` (404),
`representationNotSupported` (406), `methodNotSupported` (501), `internalError` (500).

### Content Negotiation

| Accept header | Response |
|---|---|
| `application/did-resolution` (default) | Full three-field envelope |
| `application/did+ld+json` | DID document only (JSON-LD) |
| `application/did+json` | DID document only (plain JSON) |

### Local DID Resolution

For the node's own DID: read `/shared/did.jsonl` (same file FastAPI already serves
at `/.well-known/did.json`), parse last entry, extract DID document from `state` field,
populate metadata from log entry fields (`versionId`, timestamps).

This avoids a circular dependency — the resolver doesn't call the Credo sidecar, it
reads the same shared volume file.

### Local Entity Dereference

For `https://{NODE_BASE}/entity/{uuid}` URIs: reuse the existing CONSTRUCT logic from
the `/entity/{entity_id}` route. Wrap result in the dereferencing response format.

### Remote Resolution

For remote `did:webvh` DIDs: decode domain from DID string (reverse percent-encoding),
fetch `https://{domain}/.well-known/did.json` via httpx, wrap in resolution result.

---

## Section 2: LDN Inbox — W3C Linked Data Notifications

### Spec

[W3C LDN](https://www.w3.org/TR/ldn/) — W3C Recommendation (May 2017). Stable.

### Routes

| Method | Path | Purpose |
|---|---|---|
| `POST /inbox` | Receive notification | Accept JSON-LD, store in Oxigraph |
| `GET /inbox` | List notifications | Return `ldp:contains` listing |
| `GET /inbox/{notification-id}` | Get single notification | Return stored JSON-LD |

### Inbox Discovery

Per LDN spec, advertise inbox via `Link` header on DID-related responses:

```
Link: <http://localhost:8080/inbox>; rel="http://www.w3.org/ns/ldp#inbox"
```

Added to: `/.well-known/did.json`, `/1.0/identifiers/{did}` (for local DID).

### POST /inbox — Receive Notification

- Content-Type: `application/ld+json` (required by LDN spec)
- Validation:
  - Payload size < 64KB
  - Valid JSON with `@context`
  - Phase 2: accept all valid JSON-LD (single bootstrap node, no registry yet)
  - Phase 3: verify `actor` DID against `/graph/registry`
- Storage: SPARQL INSERT into `/graph/inbox` named graph
  - Mint notification IRI: `{NODE_BASE}/inbox/{uuid7}`
  - Store original JSON-LD as `fabric:notificationContent` (serialized string)
  - Store metadata triples: `rdf:type`, `dct:created`, `fabric:actor`
- Response: `201 Created` with `Location: {NODE_BASE}/inbox/{uuid7}`

### GET /inbox — List Notifications

```json
{
  "@context": "http://www.w3.org/ns/ldp",
  "@id": "http://localhost:8080/inbox",
  "contains": [
    "http://localhost:8080/inbox/01234...",
    "http://localhost:8080/inbox/56789..."
  ]
}
```

Content-Type: `application/ld+json`.

Implementation: SPARQL SELECT for notification IRIs in `/graph/inbox`, ordered by
`dct:created` descending.

### GET /inbox/{notification-id} — Get Single Notification

Return the stored JSON-LD notification body.
Content-Type: `application/ld+json`.
404 if notification IRI not found in `/graph/inbox`.

### SHACL Constraints (future)

Phase 3: advertise via `Link: <...>; rel="http://www.w3.org/ns/ldp#constrainedBy"`
pointing to a notification SHACL shape. Phase 2 accepts any valid JSON-LD.

### Security Mitigations

- Dedicated `/graph/inbox` named graph — isolated from data graphs
- Payload size cap (64KB)
- Phase 2: single-node bootstrap, accept all senders
- Phase 3: sender DID verification against `/graph/registry`

---

## Section 3: FabricConformanceCredential as Service Directory

### Rationale

`@credo-ts/webvh` does not expose an API to inject custom service endpoints into the
DID document at creation time. Rather than fight the framework, we use the existing
conformance VC as the canonical service directory. It's signed by the node's DID, so
agents can trust the service URLs.

### Updated credentialSubject

```json
{
  "id": "did:webvh:...",
  "conformsTo": "https://w3id.org/cogitarelink/fabric#CoreProfile",
  "sparqlEndpoint": "http://localhost:8080/sparql",
  "shaclEndpoint": "http://localhost:8080/.well-known/shacl",
  "voidEndpoint": "http://localhost:8080/.well-known/void",
  "sparqlExamplesEndpoint": "http://localhost:8080/.well-known/sparql-examples",
  "resolverEndpoint": "http://localhost:8080/1.0/identifiers/",
  "ldnInbox": "http://localhost:8080/inbox",
  "attestedAt": "2026-02-24T..."
}
```

New fields: `voidEndpoint`, `sparqlExamplesEndpoint`, `resolverEndpoint`, `ldnInbox`.
All derived from `NODE_BASE`.

### Agent Discovery Flow

```
Agent has: node DID (from registry or prior knowledge)
  │
  ├─ 1. GET /1.0/identifiers/{did}
  │      → DID Resolution Result + Link header reveals inbox
  │
  ├─ 2. GET /.well-known/conformance-vc.json
  │      → Signed VC with full service directory
  │
  ├─ 3. Verify VC proof
  │      → Trust established: service URLs attested by node DID
  │
  ├─ 4. GET {voidEndpoint}
  │      → Four-layer KR discovery (existing Phase 1 flow)
  │
  └─ 5. POST {ldnInbox}
         → Send notifications
```

---

## Section 4: Implementation Scope

### New Routes (FastAPI)

- `GET /1.0/identifiers/{identifier:path}` — W3C DID Resolution
- `POST /inbox` — LDN receive
- `GET /inbox` — LDN list
- `GET /inbox/{notification_id}` — LDN get single

### Modified Files

- `fabric/node/main.py` — new routes + `Link` header on `/.well-known/did.json`
- `fabric/credo/src/index.ts` — add service URL fields to conformance VC credentialSubject

### New HURL Tests

- `30-resolver-local-did.hurl` — resolve node's own DID
- `31-resolver-not-found.hurl` — unknown DID → `notFound`
- `32-resolver-local-entity.hurl` — resolve local entity HTTP URI
- `33-ldn-inbox-post.hurl` — POST notification → 201
- `34-ldn-inbox-list.hurl` — GET inbox → `ldp:contains`
- `35-ldn-inbox-get.hurl` — GET individual notification
- `36-conformance-vc-services.hurl` — verify new service fields in VC

### No New Containers or Dependencies

Everything runs on the existing three-container stack (FastAPI + Oxigraph + Credo).
httpx (already in FastAPI requirements) handles remote DID resolution and HTTP
dereference. UUIDv7 for notification IDs uses Python's `uuid` module.

---

## Technical Risks

1. **did:webvh domain decoding**: The DID contains percent-encoded domain
   (`localhost%253A8080`). Need to correctly reverse this to fetch remote DID documents.
   Mitigated by testing against the local node's own DID.

2. **Oxigraph JSON-LD storage**: Storing notification JSON-LD as serialized string in a
   triple (not as parsed RDF) is simpler but means notifications aren't directly
   queryable as RDF triples. Acceptable for Phase 2; Phase 3 can parse and store as
   native triples if needed.

3. **did:key resolution**: Requires decoding the multibase-encoded public key from the
   DID string. Well-documented but needs a small decoder. Can stub with `methodNotSupported`
   initially and add when agent DIDs (Phase 2 Week 5-6) need it.

4. **External HTTP dereference**: Fetching arbitrary URLs from the server has security
   implications (SSRF). Mitigate with: allowlist of known vocabulary namespaces, timeout,
   response size cap.

## Sources

- [W3C DID Resolution v0.3](https://w3c.github.io/did-resolution/)
- [W3C DID Core v1.0](https://www.w3.org/TR/did-core/)
- [W3C Linked Data Notifications](https://www.w3.org/TR/ldn/)
- [DIF Universal Resolver](https://github.com/decentralized-identity/universal-resolver)
