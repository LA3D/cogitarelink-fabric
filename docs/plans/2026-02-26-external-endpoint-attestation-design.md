# D29 External Endpoint Attestation — Design

**Date**: 2026-02-26
**Status**: Approved
**Decisions**: D29 (new), extends D23 (catalog), D20 (SDL use case)

---

## Problem

Fabric agents can only discover and reason about SPARQL endpoints that are full fabric nodes (DID + conformance VC + VoID). High-value external endpoints — QLever Wikidata, PubChem, OpenStreetMap — lack this self-description infrastructure but are essential for enriching observational data. Agents need a way to discover them, understand their vocabulary coverage, and decide when to use SERVICE federation against them.

---

## Use Cases (SDL Instrument Station, D20)

| External Endpoint | Enrichment |
|---|---|
| QLever Wikidata | Sensor identity, instrument manufacturers, device specifications |
| QLever PubChem | Chemical compounds, reagents, molecular properties (already used in D20) |
| QLever OpenStreetMap | Geographic context — locations, facilities for remote sensing observations |

These three cover the immediate experimental targets. UniProt (extensive named graphs) and WikiPathways are deferred — their graph structure complexity may require Option C (proxy VoID named graphs) which we track as a follow-on.

---

## Design

### Core Principle

Fabric nodes vouch for external endpoints by including them as `dcat:DataService` entries in `/graph/catalog`. The catalog is the trust surface — no new VC type, no registry entry. The vouch is the fabric node asserting the entry in its own catalog, which has identity integrity through the node's DID.

### New Ontology Term

One new predicate in the fabric namespace (D22):

```turtle
fabric:vouchedBy rdfs:domain dcat:DataService ;
                 rdfs:range  fabric:FabricNode ;
                 rdfs:label  "vouched by" ;
                 rdfs:comment "A fabric node that attests this external endpoint is trustworthy and provides its service description." .
```

### Data Model

External endpoint entries live in `/graph/catalog` alongside the `dcat:Dataset` entries from D23 Stage 1. Format:

```turtle
@prefix dct:    <http://purl.org/dc/terms/> .
@prefix dcat:   <http://www.w3.org/ns/dcat#> .
@prefix void:   <http://rdfs.org/ns/void#> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .
@prefix spex:   <https://purl.expasy.org/sparql-examples/ontology#> .

<{base}/external/qlever-pubchem> a dcat:DataService ;
    dct:title "QLever PubChem SPARQL Endpoint" ;
    dct:description "PubChem RDF via QLever — chemical compounds, CIDs, molecular properties" ;
    dcat:endpointURL <https://qlever.cs.uni-freiburg.de/api/pubchem> ;
    void:vocabulary <http://rdf.ncbi.nlm.nih.gov/pubchem/vocabulary> ,
                    <http://semanticscience.org/resource/> ;
    fabric:vouchedBy <{node_did}> ;
    spex:SparqlExample [
        dct:title "Lookup compound by name" ;
        spex:query """PREFIX compound: <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/>
SELECT ?cid ?name WHERE {
  ?cid a compound:Compound ; rdfs:label ?name .
  FILTER(CONTAINS(LCASE(?name), "potassium chloride"))
} LIMIT 10""" ] .

<{base}/external/qlever-wikidata> a dcat:DataService ;
    dct:title "QLever Wikidata SPARQL Endpoint" ;
    dct:description "Wikidata via QLever — instruments, manufacturers, sensors, devices" ;
    dcat:endpointURL <https://qlever.cs.uni-freiburg.de/api/wikidata> ;
    void:vocabulary <http://www.wikidata.org/ontology#> ,
                    <http://schema.org/> ;
    fabric:vouchedBy <{node_did}> ;
    spex:SparqlExample [
        dct:title "Find manufacturer of instrument by label" ;
        spex:query """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:  <http://www.wikidata.org/entity/>
SELECT ?item ?manufacturer WHERE {
  ?item rdfs:label "potentiostat"@en ;
        wdt:P176 ?manufacturer .
} LIMIT 10""" ] .

<{base}/external/qlever-osm> a dcat:DataService ;
    dct:title "QLever OpenStreetMap SPARQL Endpoint" ;
    dct:description "OpenStreetMap via QLever — geographic features, facilities, locations" ;
    dcat:endpointURL <https://qlever.cs.uni-freiburg.de/api/osm-planet> ;
    void:vocabulary <https://www.openstreetmap.org/wiki/Key:> ;
    fabric:vouchedBy <{node_did}> ;
    spex:SparqlExample [
        dct:title "Find research facilities near coordinates" ;
        spex:query """PREFIX geo: <http://www.opengis.net/ont/geosparql#>
SELECT ?place ?name WHERE {
  ?place osmkey:amenity "research" ; rdfs:label ?name .
} LIMIT 10""" ] .
```

### Bootstrap Loading

New file: `fabric/node/external-endpoints.ttl.template` (same `{base}`/`{node_did}` substitution pattern as `void_templates.py`).

`bootstrap.py` loads this after the self-catalog step, substituting `NODE_BASE` and the node DID from `conformance-vc.json`. Entries are INSERTed into `/graph/catalog` under the `<{base}/graph/catalog>` named graph — same graph as the self-catalog datasets.

### Agent Discovery

`GET /.well-known/catalog` already returns all of `/graph/catalog`. Agents see both:
- `dcat:Dataset` entries (local named graphs — from D23 Stage 1)
- `dcat:DataService` entries (external endpoints — D29)

The `discover_fabric` tool (D23 Stage 3, future) queries by vocabulary coverage — an agent looking for PubChem data will find the QLever entry.

For immediate experiments, agents read the catalog from `/.well-known/catalog` in their `endpoint_sd` and reason about it directly (same pattern as VoID).

---

## Experimental Design

New experiment phase targeting cross-service federation decisions:

**Competency questions requiring external endpoints:**
- "What is the molecular formula of the reagent used in observation X?" → PubChem SERVICE
- "Who manufactured the sensor that recorded observation Y?" → Wikidata SERVICE
- "What type of facility is at the coordinates where observation Z was recorded?" → OSM SERVICE

**Metrics** (same harness as phases 4-6):
- Does the agent spontaneously use `SERVICE <external-url>` when answering?
- Does it inspect the catalog entry first or hardcode the URL?
- Chain-of-thought traces: when does it decide external data is needed?
- Does providing example queries in the catalog entry increase SERVICE usage?

**Variables to test:**
- Catalog entry with vs. without example queries (is L4 content necessary?)
- Catalog entry in `endpoint_sd` vs. discoverable only via `/.well-known/catalog`
- Competency question phrasing that does vs. doesn't hint at external data

---

## Deferred: Option C (Proxy VoID Named Graphs)

For endpoints with rich named graph structure (UniProt, WikiPathways), agents may need the graph inventory in the same form as local VoID descriptions. This would require:
- A `/graph/external/{endpoint-id}` named graph per external endpoint
- VoID-style graph inventory authored by the vouching node
- `discover_endpoint()` extension to load these proxy descriptions

Trigger for implementing: experimental evidence that agents fail to construct correct SERVICE queries against named-graph-structured endpoints, or that UniProt/WikiPathways become experimental targets.

---

## New Decision: D29

> **D29: External SPARQL endpoint attestation** — fabric nodes vouch for non-fabric SPARQL endpoints by including `dcat:DataService` entries in `/graph/catalog` with `fabric:vouchedBy`, `void:vocabulary`, and `spex:SparqlExample` metadata. The catalog provides the service description the external endpoint lacks. No new VC type. Initial targets: QLever Wikidata (instruments/manufacturers), QLever PubChem (chemical compounds), QLever OSM (geographic context). Named-graph-rich endpoints (UniProt, WikiPathways) deferred to Option C follow-on.

---

## Files

| File | Action |
|---|---|
| `fabric/node/external-endpoints.ttl.template` | CREATE — three QLever entries with `{base}` + `{node_did}` substitution |
| `fabric/node/bootstrap.py` | MODIFY — load external endpoints into `/graph/catalog` after self-catalog |
| `ontology/fabric-ontology.ttl` | MODIFY — add `fabric:vouchedBy` predicate |
| `.claude/rules/decisions-index.md` | MODIFY — add D29 |
| `tests/hurl/phase2/48-external-endpoints-catalog.hurl` | CREATE — verify external entries in `/.well-known/catalog` |
| `tests/pytest/unit/test_external_endpoints.py` | CREATE — unit tests for template substitution |
