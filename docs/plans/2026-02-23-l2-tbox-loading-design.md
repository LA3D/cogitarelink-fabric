# L2 TBox Loading Design — Full Ontology Cache for Fabric Nodes

**Date**: 2026-02-23
**Phase**: Phase 2 — D9 L2 TBox layer completion
**Decisions**: D4 (Oxigraph), D7 (PROF+VoID), D9 (four-layer KR), D20 (SDL use case)

## Problem

Phase 1 bootstrap loads a single 70-line SOSA stub into one named graph (`/ontology/sosa`). The CoreProfile declares SOSA and OWL-Time as L2 requirements, but OWL-Time was never loaded. PROV-O, SIO, PROF, and Role are needed for provenance, entity typing, and profile conformance but aren't present.

The agent's routing plan renders "Local ontology cache" with prefix-to-namespace mappings but can't show the local graph path (the Phase 1.5 TODO) because `_resolve_vocab_graphs` finds no graphs for most vocabularies.

## Ontology Inventory

Seven ontologies loaded into Oxigraph named graphs via convention `<{base}/ontology/{stem}>`:

| File | Graph | Source | Lines | Purpose |
|---|---|---|---|---|
| `sosa.ttl` | `/ontology/sosa` | Copy from ontology-agent-kr | 424 | Observation/sensor modeling (D20) |
| `time.ttl` | `/ontology/time` | Download from W3C | ~700 | Temporal entities (OWL-Time) |
| `prov.ttl` | `/ontology/prov` | Copy from rlm | 2,466 | Provenance (D16, D18) |
| `prof.ttl` | `/ontology/prof` | Copy from rlm | 175 | Profiles vocabulary (D7) |
| `role.ttl` | `/ontology/role` | Copy from rlm | 114 | PROF role concepts (D7) |
| `sio.ttl` | `/ontology/sio` | Copy from ontology-agent-kr (subset) | 144 | Entity type reasoning |
| `fabric.ttl` | `/ontology/fabric` | Rename fabric-vocab.ttl | 430 | Fabric-specific vocabulary (D22) |

**Excluded**: `fabric-core-profile.ttl` (served at `/.well-known/profile`, not a named graph). Convention: `*-profile.ttl` files are skipped by bootstrap.

**Deleted**: `sosa-tbox-stub.ttl` — replaced by full SOSA.

## Bootstrap Architecture: Convention Auto-Loading

`bootstrap.py` scans `ontology/*.ttl`, skips `*-profile.ttl`, and loads each file into `<{base}/ontology/{stem}>` via Oxigraph's Graph Store HTTP Protocol (PUT, idempotent).

```python
for f in sorted(ONTOLOGY_DIR.glob("*.ttl")):
    if f.name.endswith("-profile.ttl"):
        continue
    graph_uri = f"{NODE_BASE}/ontology/{f.stem}"
    put_graph(graph_uri, f.read_text())
```

- Alphabetical load order (deterministic)
- Individual failures non-fatal (warn and continue)
- No manifest file needed — filename is the convention

## VoID Updates

Static `void:vocabulary` declarations for data-relevant vocabularies:

- `void:vocabulary <http://www.w3.org/ns/sosa/>` (observations)
- `void:vocabulary <http://www.w3.org/2006/time#>` (temporal)
- `void:vocabulary <http://www.w3.org/ns/prov#>` (provenance)
- `void:vocabulary <http://semanticscience.org/ontology/>` (entity types)

PROF, Role, and Fabric vocab are structural — not declared as `void:vocabulary` since instance data doesn't use those namespaces directly.

## Routing Plan TODO Completion

With real named graphs loaded, `_resolve_vocab_graphs` finds them via STRSTARTS queries. New `FabricEndpoint.vocab_graph_map: dict[str, str]` stores the namespace-to-graph mapping. The routing plan renders:

```
Local ontology cache (no external dereferencing needed):
  sosa: <http://www.w3.org/ns/sosa/> -> /ontology/sosa
  time: <http://www.w3.org/2006/time#> -> /ontology/time
  prov: <http://www.w3.org/ns/prov#> -> /ontology/prov
  sio: <http://semanticscience.org/ontology/> -> /ontology/sio
```

## CoreProfile Update

Add `prof:hasResource` entries for PROV-O, SIO, PROF, and Role to `fabric-core-profile.ttl`.

## Testing

- **Unit**: Bootstrap scans and loads all `.ttl` files (mock `put_graph`)
- **Integration**: Each named graph exists after Docker rebuild (`ASK { GRAPH <.../ontology/sosa> { ?s ?p ?o } }`)
- **Integration**: `_resolve_vocab_graphs` returns real graph URIs
- **Integration**: Routing plan renders `-> /ontology/{stem}` paths
- **Regression**: Existing 14+ tests still pass (full SOSA is superset of stub)

## Experiment

Re-run Phase 1.5 experiments with enriched TBox. Richer ontology context (more class/property labels, domain/range via SPARQL) may show lift from layers 1.5b-d that were saturated with the minimal stub.

## File Summary

| File | Action |
|---|---|
| `ontology/sosa-tbox-stub.ttl` | Delete |
| `ontology/sosa.ttl` | New (copy) |
| `ontology/time.ttl` | New (download) |
| `ontology/prov.ttl` | New (copy) |
| `ontology/prof.ttl` | New (copy) |
| `ontology/role.ttl` | New (copy) |
| `ontology/sio.ttl` | New (copy) |
| `ontology/fabric-vocab.ttl` | Rename to `fabric.ttl` |
| `ontology/fabric-core-profile.ttl` | Edit (add resources) |
| `fabric/node/bootstrap.py` | Edit (convention auto-load) |
| `fabric/node/main.py` | Edit (VoID vocabulary entries) |
| `agents/fabric_discovery.py` | Edit (vocab_graph_map + routing plan) |
| `tests/` | New unit + integration tests |
