# Write-Side Infrastructure — Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans after this design is approved.

**Goal:** Enable RLM agents to write structured data to the fabric node, with SHACL validation as a commit gate, PROV-O provenance on all writes, and agent-discoverable write targets via self-description.

**Decisions:** D10 (curator write tools), D24 (shape-bound minting), D25 (LDN notifications), D27 (vocabulary admission)

**Use case:** SDL IngestCurator — single-node write loop for electrochemical instrument station data (D20)

**Approach:** Write is permissive, commit is strict. Agents write Turtle to staging graphs immediately; `commit_graph` enforces SHACL validation as a gate before the data is considered committed.

---

## Tool Surface

Four tools as `make_*_tool(ep)` factories, matching the read-side pattern (`make_fabric_query_tool`, `make_rdfs_routes_tool`):

| Tool | Purpose | Behavior |
|------|---------|----------|
| `discover_write_targets(ep)` | Find writable graphs + their governing shapes | Parses VoID for `fabric:writable` annotation; returns graph URI, governing PROF profile, shape URI |
| `write_triples(ep)` | Insert Turtle into a named graph | POST to Graph Store Protocol (`/store?graph=<uri>`); permissive — no validation at write time |
| `validate_graph(ep)` | Check graph against its governing shape | CONSTRUCT graph contents → pyshacl validation against shape; returns conformance report with `sh:agentInstruction` fix hints |
| `commit_graph(ep)` | Validate + record provenance | Calls `validate_graph` internally; if conformant, writes PROV-O activity to `/graph/audit`; if non-conformant, returns validation report (agent iterates) |

All tools require VP Bearer auth (D13). Write tools check `authorizedOperations` includes `"write"`.

### Tool Signatures

```python
def make_discover_write_targets_tool(ep: FabricEndpoint) -> dspy.Tool:
    """Returns list of {graph, profile, shape, description} for writable graphs."""

def make_write_triples_tool(ep: FabricEndpoint) -> dspy.Tool:
    """write_triples(graph: str, turtle: str) -> str
    Writes Turtle content to the specified named graph via Graph Store Protocol POST.
    Returns confirmation or error message."""

def make_validate_graph_tool(ep: FabricEndpoint) -> dspy.Tool:
    """validate_graph(graph: str) -> str
    Validates graph contents against its governing SHACL shape.
    Returns conformance result with fix instructions if non-conformant."""

def make_commit_graph_tool(ep: FabricEndpoint) -> dspy.Tool:
    """commit_graph(graph: str) -> str
    Validates and commits: runs SHACL validation, records PROV-O provenance
    on success. Returns validation report on failure."""
```

---

## Data Model

### VoID Extension: `fabric:writable`

Named graphs that accept writes declare this in VoID:

```turtle
<https://bootstrap.cogitarelink.ai/graph/entities>
    a sd:NamedGraph ;
    sd:name <https://bootstrap.cogitarelink.ai/graph/entities> ;
    void:vocabulary <http://www.w3.org/ns/sosa/>, <http://semanticscience.org/ontology/sio.owl> ;
    dct:conformsTo <https://bootstrap.cogitarelink.ai/shapes/instrument-v0.1> ;
    fabric:writable true .
```

`discover_write_targets` parses this to tell the agent where it can write and what shape governs that graph.

### InstrumentShape (SHACL)

Added to `shapes/endpoint-sosa.ttl`. Governs `sosa:Platform` entities in `/graph/entities`:

```turtle
ex:InstrumentShape a sh:NodeShape ;
    sh:targetClass sosa:Platform ;
    dct:conformsTo <https://bootstrap.cogitarelink.ai/shapes/instrument-v0.1> ;
    sh:description "Shape for instrument/platform entities. Required: identity and hosting. Recommended: manufacturer and model for Wikidata linking." ;

    # Required
    sh:property [
        sh:path rdfs:label ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
        sh:agentInstruction "Every instrument must have a human-readable label." ;
    ] ;
    sh:property [
        sh:path sosa:hosts ;
        sh:minCount 1 ;
        sh:class sosa:Sensor ;
        sh:agentInstruction "An instrument must host at least one sensor." ;
    ] ;
    sh:property [
        sh:path schema:serialNumber ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
        sh:agentInstruction "Provide the instrument serial number for provenance tracking." ;
    ] ;

    # Recommended (not required — agent should attempt but won't block commit)
    sh:property [
        sh:path schema:manufacturer ;
        sh:maxCount 1 ;
        sh:severity sh:Warning ;
        sh:agentInstruction "If known, provide the manufacturer. Check Wikidata for owl:sameAs linking." ;
    ] ;
    sh:property [
        sh:path schema:model ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:severity sh:Warning ;
        sh:agentInstruction "If known, provide the instrument model identifier." ;
    ] .
```

`sh:agentInstruction` is a custom annotation (non-standard SHACL) that `validate_graph` includes in its output so the LLM agent knows how to fix violations.

### SensorEntityShape

Governs `sosa:Sensor` entities referenced by instruments:

```turtle
ex:SensorEntityShape a sh:NodeShape ;
    sh:targetClass sosa:Sensor ;
    sh:property [
        sh:path rdfs:label ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path sosa:observes ;
        sh:minCount 1 ;
        sh:agentInstruction "Declare what observable property this sensor measures." ;
    ] .
```

---

## Entity Model

Clear separation between instrument identity and chemistry:

### Instruments (`/graph/entities`) — Identity and Provenance

An instrument entity represents a physical device:

- **Type**: `sosa:Platform` (the instrument itself) hosting `sosa:Sensor` instances
- **Required**: label, serial number, hosts relationship
- **Recommended**: manufacturer (`schema:manufacturer`), model (`schema:model`)
- **Linking**: `owl:sameAs` to Wikidata for types (e.g., `wd:Q12913` mass spectrometer) and manufacturers (e.g., `wd:Q277898` Agilent Technologies)

Wikidata coverage: good for instrument types and major manufacturers; spotty for specific models. Agent should attempt linking but not fail if no match found.

### Chemistry (`/graph/observations`) — Measurement-Level

Chemical compounds appear only at the observation level, not as instrument properties:

- Observations link to compounds via `sio:is-about <pubchem:CID_...>`
- PubChem CIDs discoverable via QLever SERVICE federation (D29)
- Compounds are properties of measurements, not of instruments

This separation means InstrumentShape does not include any chemistry-related properties.

---

## Curator Workflow

SDL IngestCurator write loop (single-node, single-agent):

```
1. discover_write_targets()     → learn /graph/entities accepts sosa:Platform, governed by InstrumentShape
2. Read instrument metadata     → from CSV/JSON source (injected as task data)
3. write_triples(/graph/entities, turtle)  → construct sosa:Platform + sosa:Sensor Turtle, POST to graph
4. validate_graph(/graph/entities)         → check against InstrumentShape
5. [if non-conformant]          → read sh:agentInstruction, fix Turtle, write again, re-validate
6. commit_graph(/graph/entities)           → SHACL gate + PROV-O provenance recorded
7. [stretch] Wikidata enrichment           → query QLever Wikidata for manufacturer/type owl:sameAs
8. write_triples(/graph/observations, turtle) → observation data with sio:is-about links
9. commit_graph(/graph/observations)       → validate + provenance
```

Steps 5 iterates until conformant — same self-description-driven pattern as read-side navigation. The agent reads fix guidance from `sh:agentInstruction` and adjusts its Turtle output.

Step 7 (Wikidata enrichment) is a stretch goal: agent discovers QLever Wikidata in `/.well-known/catalog` (D29), queries for manufacturer/instrument type entities, adds `owl:sameAs` triples. Not required for initial implementation.

---

## PROV-O Provenance

`commit_graph` records a `prov:Activity` in `/graph/audit`:

```turtle
<https://bootstrap.cogitarelink.ai/activity/{uuid7}>
    a prov:Activity ;
    prov:wasAssociatedWith <did:webvh:...agent-did> ;
    prov:used <https://bootstrap.cogitarelink.ai/shapes/instrument-v0.1> ;
    prov:generated <https://bootstrap.cogitarelink.ai/graph/entities> ;
    prov:endedAtTime "2026-03-03T14:30:00Z"^^xsd:dateTime ;
    dct:description "IngestCurator committed instrument entities" .
```

This connects agent identity (D13), shape version, target graph, and timestamp — queryable for audit.

---

## Shape Governance

Shapes are first-class governed artifacts, not static schema files:

### Shape as Governed Artifact

- Each shape has a versioned URI (e.g., `instrument-v0.1`)
- Shape content is hash-bound via D26 `relatedResource` + `digestMultibase` in the conformance VC
- Named graphs declare their governing shape via `dct:conformsTo`
- `commit_graph` records the shape version used in PROV-O provenance (`prov:used <shape-uri>`)

### Evolution Path

```
v0.1 (minimal)           v0.2 (recommended)
─────────────────         ─────────────────────
rdfs:label [required]     rdfs:label [required]
sosa:hosts [required]     sosa:hosts [required]
schema:serialNumber [req] schema:serialNumber [req]
                          schema:manufacturer [warning]
                          schema:model [warning]
```

Shape evolution follows the same pattern as ontology versioning — new version, new URI, old data still valid against old shape. Migration is a separate concern.

### Agentic Conformance Workflow

The agent discovers and conforms to shapes through the same self-description mechanism as read-side navigation:

1. Agent calls `discover_write_targets()` — learns graph URI + shape URI
2. Shape declaration in VoID/SD tells agent what's expected
3. Agent constructs entity Turtle based on available source data
4. `validate_graph()` checks conformance, returns `sh:agentInstruction` hints on failure
5. Agent iterates (fix → re-validate) until conformant
6. `commit_graph()` records success with shape version in provenance

This is the write-side analog of the read-side "navigate self-describing endpoint" pattern: the fabric tells the agent what structure it expects, the agent conforms, and the fabric validates.

---

## Deferred (Not in Scope)

| Item | Decision | Rationale |
|------|----------|-----------|
| UUIDv7 PID minting protocol | D24 | Shape-bound minting adds complexity; build basic write first |
| Cross-node boundary validation | D24 | Single-node scope for now |
| Trust gap → `/graph/pending` | D24 | HitL escalation deferred |
| LDN notification tools (`send_notification`, `check_inbox`) | D25 | Infrastructure exists but agent tools not needed yet |
| Shape versioning protocol | — | Manual versioning sufficient initially |
| Shape composition across profiles | — | Single profile per graph for now |
| PubChem compound linking | D29 | Observation-level, separate from instrument writes |
| SSSOM crosswalk generation | D21 | Entity dedup is post-write concern |
| Vocabulary admission enforcement | D27 | VocabularyMetadataShape not needed for write tools |

---

## Key Files (Expected)

| File | Purpose |
|------|---------|
| `agents/fabric_write.py` | `make_write_triples_tool`, `make_commit_graph_tool`, `make_validate_graph_tool`, `make_discover_write_targets_tool` |
| `shapes/endpoint-sosa.ttl` | InstrumentShape + SensorEntityShape additions |
| `fabric/node/main.py` | Write-auth check on Graph Store Protocol routes |
| `experiments/fabric_navigation/run_experiment.py` | Write-phase feature flags + tool advertisement |
