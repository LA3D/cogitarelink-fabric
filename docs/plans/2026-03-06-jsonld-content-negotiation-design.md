# Phase 2.5a: JSON-LD Content Negotiation Infrastructure — Design

**Date**: 2026-03-06
**Status**: Approved
**Implements**: D22 (fabric ontology), D31 (JSON-LD as hypermedia transport)
**Prerequisite for**: Phase 2.5b experiments, KF-NodeRLM-Experiment-PLAN

---

## Problem

The fabric serves JSON-LD responses from 6+ routes, but Oxigraph returns **bare JSON arrays** with full IRIs and no `@context`. Agents receiving these responses cannot use JSON-LD processing (expand, compact, frame) because there's no context to resolve terms against. Path B navigation (D31) is impossible — there's nothing to dereference.

### Oxigraph JSON-LD Behavior (Confirmed via Source Analysis)

Oxigraph's `oxjsonld` crate provides `JsonLdSerializer` with `with_prefix()` and `with_base_iri()` configuration. However, Oxigraph Server's HTTP endpoint uses `RdfSerializer::from_format(RdfFormat::JsonLd)` which:

1. Creates `JsonLdSerializer::new()` with **no prefixes configured**
2. `RdfSerializer::with_prefix()` is a **silent no-op** for JSON-LD (the prefix is dropped)
3. With no prefixes/base IRI, the serializer skips the `@context`/`@graph` wrapper entirely

**Result**: SPARQL CONSTRUCT responses as `application/ld+json` return:

```json
[
  {
    "@id": "http://www.w3.org/ns/sosa/ActuatableProperty",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": [{"@id": "http://www.w3.org/2002/07/owl#Class"}],
    "http://www.w3.org/2000/01/rdf-schema#comment": [{"@value": "An actuatable quality..."}]
  }
]
```

No `@context`, no prefix compaction, no `@graph` wrapper. Full IRIs throughout.

### What Oxigraph Does NOT Support

- External `@context` URLs — only inline prefix-to-namespace mappings
- JSON-LD compact/expand/frame/flatten algorithms — serializer only
- Prefix passthrough from `RdfSerializer` to `JsonLdSerializer`

### What This Means

All JSON-LD `@context` handling must happen in the FastAPI gateway layer. Oxigraph is a correct RDF serializer; the gateway adds the JSON-LD navigation layer.

---

## Design

### Approach: Gateway-Level Context Injection

FastAPI post-processes Oxigraph's bare JSON-LD arrays by wrapping them with an external `@context` URL reference. Purpose-specific context files map prefixes to canonical namespace URIs.

```
Oxigraph CONSTRUCT → bare array [{"@id": "http://..."}]
    ↓ FastAPI _inject_context()
{"@context": "https://bootstrap.cogitarelink.ai/.well-known/context/data.jsonld",
 "@graph": [{"@id": "http://..."}]}
```

The `@context` URL is dereferenceable — agents (or jsonld.js) can fetch it to get prefix mappings, then compact the full IRIs into readable terms.

### Architecture

```
Agent
  ↓ GET /entity/xxx (Accept: application/ld+json)
FastAPI gateway
  ↓ CONSTRUCT query
Oxigraph → bare JSON array
  ↓ _inject_context(response, "data")
FastAPI → {"@context": ".../.well-known/context/data.jsonld", "@graph": [...]}
  ↓
Agent (can now use jsonld.js compact/frame/expand)
```

---

## Work Units

### WU-1: `/ontology/{vocab}` Dynamic Route

**Purpose**: Serve cached ontology content from named graphs via HTTP. Without this, Path B navigation dead-ends — an agent encounters `sosa:Observation`, the `@context` maps it to `http://www.w3.org/ns/sosa/Observation`, but there's no fabric-local endpoint to dereference against.

**Route contract**:
```
GET /ontology/{vocab}
Accept: application/ld+json  → JSON-LD with meta @context
Accept: text/turtle           → Turtle
Accept: application/n-triples → N-Triples
404 if named graph <{NODE_BASE}/ontology/{vocab}> is empty
```

**Implementation**:
- CONSTRUCT `{ ?s ?p ?o }` against named graph `<{NODE_BASE}/ontology/{vocab}>`
- Content negotiation via `Accept` header (same pattern as `_sparql_construct`)
- For JSON-LD: use `_inject_context()` with `"meta"` context type
- Auth: PUBLIC — no `verify_vp_bearer`. Discovery infrastructure.
- Security: validate `{vocab}` against allowlist or `^[a-z][a-z0-9-]*$` pattern to prevent graph URI injection

**Files**: `fabric/node/main.py` (add route)

**Tests**:
- pytest unit: mock Oxigraph → verify CONSTRUCT query, content type routing, 404 on empty
- HURL: GET `/ontology/sosa` (Turtle) → 200, contains `sosa:Observation`
- HURL: GET `/ontology/sosa` (JSON-LD) → 200, has `@context`
- HURL: GET `/ontology/nonexistent` → 404

### WU-2: Purpose-Specific `@context` Files

**Purpose**: Three context files + one aggregate provide prefix-to-namespace mappings for different response types. Served as static JSON from `/.well-known/context/`.

**Files to create**:

| File | Prefixes | Used by |
|---|---|---|
| `contexts/data.jsonld` | sosa, ssn, sio, prov, fabric, time, qudt, xsd, dct, rdfs, owl, skos | `/entity/`, data responses |
| `contexts/discovery.jsonld` | void, sd, dcat, dct, prof, fabric, rdfs, foaf, ldp | `.well-known/*`, catalog, registry, agents |
| `contexts/meta.jsonld` | rdfs, owl, sh, skos, xsd, vann, voaf, dct | `/ontology/*`, shapes, examples |
| `contexts/fabric-context.jsonld` | Aggregate — references all three via array | One-stop for agents |

**Context file format** (example `data.jsonld`):
```json
{
  "@context": {
    "sosa": "http://www.w3.org/ns/sosa/",
    "ssn": "http://www.w3.org/ns/ssn/",
    "prov": "http://www.w3.org/ns/prov#",
    "fabric": "https://w3id.org/cogitarelink/fabric#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    ...
  }
}
```

**Aggregate format** (`fabric-context.jsonld`):
```json
{
  "@context": [
    "/.well-known/context/data.jsonld",
    "/.well-known/context/discovery.jsonld",
    "/.well-known/context/meta.jsonld"
  ]
}
```

Note: aggregate uses relative URLs — resolved against the serving base. Alternatively use absolute `{NODE_BASE}` URLs for safety.

**Route**: `GET /.well-known/context/{name}` — serves from `fabric/node/contexts/` directory. Static file serving, `Content-Type: application/ld+json`.

**Auth**: PUBLIC

**Files**: `fabric/node/contexts/*.jsonld` (new), `fabric/node/main.py` (add route)

**Tests**:
- HURL: GET each context file → 200, valid JSON, expected prefixes present
- pytest: each file parses as valid JSON, all expected namespace URIs present

### WU-3: `_inject_context()` Helper

**Purpose**: Fix all 6+ routes serving bare JSON-LD arrays from Oxigraph CONSTRUCT.

**Implementation**:
```python
import json

_CONTEXT_MAP = {
    "data": f"{NODE_BASE}/.well-known/context/data.jsonld",
    "discovery": f"{NODE_BASE}/.well-known/context/discovery.jsonld",
    "meta": f"{NODE_BASE}/.well-known/context/meta.jsonld",
}

def _inject_context(body: bytes, context_type: str) -> bytes:
    """Wrap Oxigraph's bare JSON-LD array with @context."""
    doc = json.loads(body)
    ctx_url = _CONTEXT_MAP[context_type]
    if isinstance(doc, list):
        doc = {"@context": ctx_url, "@graph": doc}
    elif isinstance(doc, dict) and "@context" not in doc:
        doc["@context"] = ctx_url
    elif isinstance(doc, dict):
        # Oxigraph included inline @context — prepend our URL
        existing = doc["@context"]
        doc["@context"] = [ctx_url, existing] if not isinstance(existing, list) else [ctx_url] + existing
    return json.dumps(doc, ensure_ascii=False).encode()
```

**Routes affected**:

| Route | Context type |
|---|---|
| `/.well-known/void` | Already has inline JSON-LD — skip (uses `void_templates.py`) |
| `/.well-known/catalog` | `discovery` |
| `/entity/{uuid7}` | `data` |
| `/fabric/registry` | `discovery` |
| `/agents` | `discovery` |
| `/agents/{agent_id}` | `discovery` |
| `/ontology/{vocab}` (WU-1) | `meta` |

**Integration**: Modify `_sparql_construct()` to accept `context_type` parameter. When format is JSON-LD, apply `_inject_context()` before returning.

**Files**: `fabric/node/main.py`

**Tests**:
- pytest unit: `_inject_context()` with bare array → wrapped with `@context` + `@graph`
- pytest unit: `_inject_context()` with dict (no context) → `@context` added
- pytest unit: `_inject_context()` with dict (existing context) → prepended
- HURL: GET `/entity/{known-uuid}` (JSON-LD) → has `@context`
- HURL: GET `/.well-known/catalog` (JSON-LD) → has `@context`

### WU-4: VoID `void:vocabulary` on Named Graphs

**Purpose**: Make the vocab-namespace → local-graph mapping explicit in VoID, eliminating `_resolve_vocab_graphs()` STRSTARTS queries for Path B bootstrap.

**Enhancement**:
```turtle
sd:namedGraph [
    sd:name <{base}/ontology/sosa> ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ;
    prov:wasDerivedFrom <http://www.w3.org/ns/sosa/> ;
] ;
```

**Depends on**: WU-1 (the `/ontology/{vocab}` route these entries reference)

**Files**: `fabric/node/void_templates.py` — both `_VOID_TURTLE` and `_VOID_JSONLD` templates

**Tests**:
- HURL: GET `/.well-known/void` → contains `void:vocabulary` associated with ontology named graphs
- pytest: parse VoID Turtle → for each `/ontology/*` graph, a `void:vocabulary` triple exists

### WU-5: Shapes + Examples JSON-LD Content Negotiation

**Purpose**: Add `application/ld+json` as content negotiation option for `/.well-known/shacl` and `/.well-known/sparql-examples` (currently Turtle-only).

**Implementation**: When `Accept: application/ld+json`:
- Read Turtle source file
- Parse via rdflib
- Serialize as JSON-LD
- Apply `_inject_context()` with `"meta"` context type

**Depends on**: WU-2 (needs `meta.jsonld` context file), WU-3 (`_inject_context`)

**Files**: `fabric/node/main.py` — shape and example serving routes

**Tests**:
- HURL: GET `/.well-known/shacl` (JSON-LD) → 200, has `@context`, contains `sh:NodeShape` equivalent
- HURL: GET `/.well-known/sparql-examples` (JSON-LD) → 200, has `@context`
- Turtle responses unchanged (regression check)

---

## Dependency Graph

```
WU-1 (ontology route)  ←─── WU-4 (VoID vocab entries)
WU-2 (context files)   ←─── WU-5 (shapes/examples JSON-LD)
WU-3 (inject context)  ←─── WU-5
```

WU-1, WU-2, WU-3 are independent. WU-4 depends on WU-1. WU-5 depends on WU-2 + WU-3.

**Execution order**: WU-1 → WU-2 → WU-3 → WU-4 → WU-5

Each WU follows TDD (RED → GREEN) then agentic code review before proceeding.

---

## Success Criteria

- `/ontology/{vocab}` serves content-negotiated responses for all cached ontologies
- All JSON-LD responses include appropriate `@context` URL
- Purpose-specific context files served at `/.well-known/context/{name}`
- VoID declares `void:vocabulary` on each ontology `sd:namedGraph`
- All new routes are PUBLIC (no auth)
- Existing 264 pytest + 47 HURL tests still pass (no regression)
- New tests cover all five work units

---

## Non-Goals

- JSON-LD compact/expand/frame processing server-side (that's the agent's job)
- Modifying Oxigraph's serializer configuration (no control from HTTP API)
- `@context` with term definitions beyond prefix mappings (keep contexts simple)
- RDF 1.2 triple terms in JSON-LD (Oxigraph doesn't support yet)
