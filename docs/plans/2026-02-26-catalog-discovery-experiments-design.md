# Phase 7: Catalog Discovery Experiments — Design

**Date**: 2026-02-26
**Status**: Design
**Depends on**: D29 external endpoint attestation (complete), Phase 6 experiment infrastructure

## Problem

The fabric now advertises external SPARQL endpoints (QLever PubChem, Wikidata, OSM) as `dcat:DataService` entries in `/graph/catalog` with `fabric:vouchedBy` attestation and `spex:SparqlExample` hints. But no agent has ever seen this catalog. We don't know:

1. Whether the agent can discover and use external endpoints from catalog metadata
2. Whether catalog+example hints are sufficient for correct SPARQL against unfamiliar external schemas
3. How the agent handles mixed local+external reasoning (combine Oxigraph data with QLever results)

## Experiment Structure

Two conditions, same task set:

| Phase | Catalog visible? | External query tool? | What it tests |
|-------|-----------------|---------------------|---------------|
| **phase7a** (control) | No | No | Baseline — agent has only local SD, no catalog |
| **phase7b** (treatment) | Yes | Yes | Agent sees catalog in routing plan + can query external endpoints |

New feature flags:
- `catalog-in-sd`: Appends "External SPARQL Services" section to `routing_plan` with endpoint URLs, descriptions, vocabularies, and example queries parsed from `/graph/catalog`
- `external-query-tool`: Adds `query_external_sparql(endpoint_url, query)` tool to REPL namespace

### Why a new tool instead of SPARQL SERVICE federation

Oxigraph supports SERVICE but Docker containers cannot reach external HTTPS endpoints (tested: connection refused / timeout from inside containers). The RLM agent runs on the host where all three QLever endpoints are reachable. A direct `query_external_sparql` tool is also more realistic — in a real distributed fabric, agents query different endpoints separately rather than routing everything through a single SPARQL engine.

### QLever endpoint verification (from host)

| Endpoint | Status | Latency | Notes |
|----------|--------|---------|-------|
| PubChem | Working | ~10ms | Uses full SIO IRIs (`SIO_000008`, `SIO_000300`), CHEMINF classes |
| Wikidata | Working | ~125ms | Standard Wikidata property paths (`wdt:P31`, etc.) |
| OSM | Working | ~5.8s | Slower, uses `osmkey:` prefix namespace |

## Task Design

Six tasks in `tasks/phase7-catalog.json`. Three pure-external (answer comes entirely from QLever), three mixed (require combining local Oxigraph data with external QLever data).

### Pure external tasks (no local data needed)

1. **pubchem-molecular-formula**: "What is the molecular formula of aspirin (CID2244)?"
   - Target: QLever PubChem
   - Expected: `C9H8O4`
   - Tests: Agent discovers PubChem endpoint from catalog, adapts example query for CID2244, uses `sio:SIO_000008` → `CHEMINF_000042` → `sio:SIO_000300` pattern

2. **wikidata-potentiostat-manufacturer**: "Who manufactures potentiostats according to Wikidata?"
   - Target: QLever Wikidata
   - Expected: substring match on manufacturer names (e.g., "Metrohm", "Gamry")
   - Tests: Agent discovers Wikidata endpoint, adapts manufacturer example query

3. **osm-notre-dame-location**: "Find the University of Notre Dame in OpenStreetMap."
   - Target: QLever OSM
   - Expected: substring match on "Notre Dame"
   - Tests: Agent discovers OSM endpoint, uses `osmkey:name` FILTER pattern

### Mixed tasks (local data + external enrichment)

4. **obs-compound-formula**: "What is the molecular formula of the compound measured in observation obs-001?"
   - Local data: sosa:Observation with `sio:is-about` linking to a ChemicalEntity with `rdfs:label "aspirin"` and `dct:identifier "2244"`
   - Agent must: query local → extract CID → query PubChem for formula
   - Expected: `C9H8O4`

5. **obs-sensor-manufacturer**: "Who manufactured the sensor used in observation obs-002?"
   - Local data: sosa:Observation with `sosa:madeBySensor` → Sensor with `rdfs:label "potentiostat"` and `schema:manufacturer` with `schema:name "Metrohm Autolab"`
   - Agent must: query local → find sensor label → optionally verify via Wikidata
   - Expected: "Metrohm" (available locally, Wikidata enriches)

6. **obs-lab-location**: "Where is the laboratory associated with observation obs-003?"
   - Local data: sosa:Observation with `sosa:madeBySensor` → Sensor → `sosa:isHostedBy` Platform with `rdfs:label "Notre Dame Electrochemistry Lab"` and `schema:location "Notre Dame, IN"`
   - Agent must: query local → extract location → optionally verify via OSM
   - Expected: "Notre Dame"

### Scoring

All tasks use `substring_match_scorer` (same as phases 1-6). Expected answers are chosen to be unambiguous substrings.

### Setup data

Pure external tasks: no setup (data lives in QLever).
Mixed tasks: `setup.type = "sparql_insert"` with observation + entity data in `/graph/observations` and `/graph/entities`, same pattern as phase 5.

## Implementation Changes

### 1. `agents/fabric_discovery.py` — catalog parsing

Add `_parse_catalog()` function and new fields to `FabricEndpoint`:

- `external_services: list[ExternalService]` — parsed from `/graph/catalog` CONSTRUCT
- New dataclass `ExternalService`: `title`, `endpoint_url`, `description`, `vocabularies`, `examples: list[ExampleSummary]`
- `_parse_catalog(catalog_ttl)` uses rdflib to extract `dcat:DataService` entries with `dcat:endpointURL`, `spex:SparqlExample`, etc.
- `discover_endpoint()` gains optional `fetch_catalog=False` kwarg — when True, fetches `/.well-known/catalog` and parses external services
- `routing_plan` property extended: when `external_services` is non-empty, appends an "External SPARQL Services" section listing each service's URL, description, vocabularies, and example queries

### 2. `agents/fabric_query.py` — external query tool

Add `make_external_query_tool(ep)` factory:

- Returns `query_external_sparql(endpoint_url: str, query: str) -> str`
- Validates `endpoint_url` against `ep.external_services` URLs (safety gate — only catalog-listed endpoints allowed)
- Sends SPARQL via httpx POST with `-L` redirect following (QLever returns 308)
- Same truncation and error-surfacing pattern as `make_fabric_query_tool`
- No `reject_unbounded` — external endpoints handle their own query planning

### 3. `experiments/fabric_navigation/run_experiment.py` — phase7 wiring

Add `PHASE_FEATURES` entries:

```python
"phase7a-no-catalog": [
    "void-sd", "void-urispace", "void-graph-inventory",
    "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
    "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
    "tbox-graph-paths",
],
"phase7b-catalog": [
    "void-sd", "void-urispace", "void-graph-inventory",
    "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
    "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
    "tbox-graph-paths",
    "catalog-in-sd", "external-query-tool",
],
```

In `rlm_factory`: when `external-query-tool` in features, add `make_external_query_tool(ep)` to tools list.

In `kwarg_builder`: when `catalog-in-sd` in features, call `discover_endpoint()` with `fetch_catalog=True` (or re-fetch catalog separately) and use the extended routing plan.

### 4. `experiments/fabric_navigation/dspy_eval_harness.py` — metrics

Add `used_external_query: int` to `FabricMetrics` — counts calls to `query_external_sparql` in trajectory.

### 5. Fix template example queries

Correct `external-endpoints.ttl.template` PubChem examples to use full SIO IRIs:
- `sio:has-attribute` → works as-is (QLever resolves the prefix)
- Add note that QLever PubChem uses `CHEMINF_*` class IRIs, not shorthand names
- Verify all three endpoint examples actually return results

### 6. New task file

Create `experiments/fabric_navigation/tasks/phase7-catalog.json` with the 6 tasks above.

## Expected Outcomes

**phase7a (control)**: Pure external tasks should score 0.0 (agent has no way to know about or reach external endpoints). Mixed tasks score depends on whether the answer is available locally — obs-sensor-manufacturer and obs-lab-location may score 1.0 from local data alone; obs-compound-formula should score 0.0 (formula not in local data).

**phase7b (treatment)**: If catalog discovery works, all 6 tasks should score 1.0. Key metrics to watch:
- `used_external_query` count per task — confirms the tool was actually called
- Iteration count — how many REPL turns to discover and use external endpoints
- Whether the agent correctly selects the right external endpoint for each task

**Interesting failure modes**:
- Agent sees catalog but doesn't use the external query tool (same as phase 4 tool adoption problem)
- Agent queries wrong external endpoint (PubChem for location, OSM for chemistry)
- Agent constructs incorrect SPARQL for external endpoint (schema mismatch)
- QLever flakiness (OSM is slow at ~6s; occasional timeouts)

## Files to create/modify

| File | Action |
|------|--------|
| `agents/fabric_discovery.py` | MODIFY — add `ExternalService`, `_parse_catalog`, `fetch_catalog` kwarg |
| `agents/fabric_query.py` | MODIFY — add `make_external_query_tool` |
| `experiments/fabric_navigation/run_experiment.py` | MODIFY — add phase7a/7b features, wire catalog+tool |
| `experiments/fabric_navigation/dspy_eval_harness.py` | MODIFY — add `used_external_query` metric |
| `experiments/fabric_navigation/tasks/phase7-catalog.json` | CREATE — 6 tasks |
| `fabric/node/external-endpoints.ttl.template` | MODIFY — fix PubChem example queries |

## Verification

1. Unit tests: `_parse_catalog` extracts correct ExternalService entries from sample Turtle
2. Unit tests: `make_external_query_tool` validates URLs, handles redirects, truncates
3. Integration: `python run_experiment.py --phase phase7a --tasks tasks/phase7-catalog.json` completes
4. Integration: `python run_experiment.py --phase phase7b --tasks tasks/phase7-catalog.json` completes
5. Compare scores: phase7a vs phase7b — expect significant lift on external tasks
