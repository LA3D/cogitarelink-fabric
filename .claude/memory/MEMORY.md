# cogitarelink-fabric — Session Memory

## Project State (as of 2026-03-01)

**Repo**: `~/dev/git/LA3D/agents/cogitarelink-fabric`
**Branch**: main (all work merged)
**Tests**: 205 unit + 42 HURL (15 phase1 + 27 phase2) — all passing
**Endpoint**: `https://bootstrap.cogitarelink.ai` (Caddy TLS, D30 complete)

## Completed Work

- **Phase 1 gap closure**: iteration tracking, L2 TBox loading, SHACL validation
- **Phase 2 TBox lift**: phase2a/2b — SOSA saturated (pretraining), TBox paths add overhead not lift
- **Phase 3 SIO TBox lift**: phase3a/3b — SIO outside pretraining, +0.167 score lift confirmed
- **Phase 4 analyze_rdfs_routes tool**: `make_rdfs_routes_tool(ep)` factory backed by `ep.tbox_graph`
- **RDFS infrastructure refactor** (commit `286278f`): removed SOSA domain contamination from patterns; restored 5 missing extractors; dynamic prefix map
- **Phase 5 cross-graph navigation**: phase5a/5b — cross-graph joins between /graph/observations and /graph/entities; both scored 1.000; tool never invoked (0/5 tasks)
- **Phase 6 escape hatch closure** (commits `94f8b09`, `d7596dc`): three mechanisms — unbounded query guardrail, entity lookup stripping, noise predicates. Result: no effect — agent never used the escape hatch. Tool still 0/5 calls. Guardrail had false-positive bug (matching across semicolons + SELECT clause), fixed in `d7596dc`.
- **Phase 2 bootstrap** (commit `f5a5327`): did:webvh + VC issuance via Credo 0.6.x sidecar; shared Docker volume
- **Phase 2 DID integration** (commits `4eda91c`–`2422669`): W3C DID Resolution HTTP API, LDN inbox (POST/GET), enriched conformance VC, Link header discovery, DID resolver helper module, SPARQL injection prevention
- **D29 External endpoint attestation** (commit `cb8a69a`): QLever PubChem/Wikidata/OSM as dcat:DataService in /graph/catalog with fabric:vouchedBy + spex:SparqlExample; POST Graph Store Protocol for append
- **D30 HTTPS migration** (commits `b91573e`–`d51638f`): Caddy TLS-terminating reverse proxy; NODE_BASE → `https://bootstrap.cogitarelink.ai`; tls internal CA; all 247 tests passing

## Key Architecture Patterns

- `ep.tbox_graph`: `rdflib.Graph | None` on `FabricEndpoint`, merged in-process ontology triples
- `make_rdfs_routes_tool(ep)`: pre-computes `extract_ontology_structure(ep.tbox_graph)` at factory time; lazy `import dspy` in closure; calls `dspy.settings.lm` as sub-agent
- `_RDFS_TOOL_HINT`: injected into `endpoint_sd` via `kwarg_builder` in `run_experiment.py`
- `_build_compact_map(prefix_declarations)`: dynamic IRI compaction from endpoint SHACL `sh:declare` + W3C fallbacks
- `_build_sensor_insert()`: Phase 5 — builds INSERT DATA for sosa:Sensor entities in /graph/entities; Phase 6 adds `noise_predicates` iteration
- `_is_unbounded_scan()`: regex detector in `fabric_query.py` — catches `<iri> ?p ?o` and `?s ?p ?o` patterns
- `_strip_entity_lookup()`: regex post-processor in `run_experiment.py` — removes "Entity lookup by IRI" example from SD
- Phase 6 feature flags: `no-entity-lookup` (strips example), `no-unbounded-scan` (guardrail on sparql_query tool)
- `setup_task_data` graph override fix: per-record `graph` key preserved, setup-level default only applies when absent
- `teardown_task_data` multi-graph: reads `setup.extra_graphs` list, drops each in addition to primary

### Phase 2 DID Integration Patterns

- `fabric/node/did_resolver.py`: pure Python helpers (no FastAPI dep) — same pattern as `void_templates.py`; imported by both `main.py` (Docker) and unit tests (local)
- `decode_webvh_domain(did)`: splits on `:`, takes `parts[3:]` as encoded domain; iterative `urllib.parse.unquote` handles double-encoding
- `_fully_decode(s)`: iterative percent-decode until stable — used for normalized DID comparison in `parse_did_log`
- `sparql_escape(s)`: escapes `\`, `"`, `\n`, `\r`, `\t` for SPARQL string literal interpolation; **must** be used on all user-supplied values
- `is_valid_uuid(s)`: regex gate before interpolating path params into SPARQL IRIs — prevents injection
- `uuid7()`: inline RFC 9562 UUIDv7 — timestamp-sortable, no external deps; used for notification IDs
- Credo did:webvh format: `did:webvh:{scid}:{domain}` — scid first, domain last; domain double-percent-encoded (`%253A` not `%3A`)
- FastAPI URL-decodes path params: `%253A` → `%3A` (one level stripped); stored DID still has `%253A`; comparison must normalize both sides
- LDN inbox graph: `/graph/inbox` — notifications stored as `ldp:Resource` with `dct:created`, `fabric:actor`, `fabric:notificationContent` (escaped JSON string)
- Link header: `_LDN_LINK = f'<{NODE_BASE}/inbox>; rel="http://www.w3.org/ns/ldp#inbox"'` — added to `/.well-known/did.json` and local DID resolution responses
- HURL JSONPath: `@` is reserved; use bracket notation `$['@context']` not `$.@context`
- Conformance VC service directory fields: `voidEndpoint`, `sparqlExamplesEndpoint`, `resolverEndpoint`, `ldnInbox`
- Shared Docker volume (`did-data`): Credo writes `did.jsonl` + `conformance-vc.json`; FastAPI reads with 404 fallback (eventual consistency)

## Critical Findings

**Tool advertisement is required**: Tool in REPL namespace ≠ agent-discoverable. Must be advertised in `endpoint_sd` (the input field the LLM reads to generate REPL code). Without `_RDFS_TOOL_HINT`, phase4b tool was called 0/6 times.

**CORRECTED — Tool adoption is task-selective, not uniform**: Detailed trace analysis across 8 phase4b ensemble runs reveals the tool is called only for **schema introspection tasks** (2/6 per run), never for data tasks (0/6 per run):

| Task type | Tool calls (8 runs) | Pattern |
|---|---|---|
| `sio-attribute-inverse` | 7/8 runs | Schema: owl:inverseOf lookup |
| `sio-measured-value-range` | 8/8 runs (one had 2 calls) | Schema: rdfs:range lookup |
| `sio-has-value-type` | 1/8 runs | Schema: rarely needed |
| `obs-sio-measured-value` | 0/8 runs | Data: raw triple exploration suffices |
| `obs-sio-unit` | 0/8 runs | Data: raw triple exploration suffices |
| `obs-sio-chemical-entity` | 0/8 runs | Data: raw triple exploration suffices |

Previous claim of "6/6 tool usage" was wrong — it was 2/6 per run, selectively on schema tasks.

**Tool switches reasoning mode, not reasoning capability**: Trace analysis shows the tool's primary effect is shifting the agent from **exploratory** (bottom-up: read data → infer schema) to **confirmatory** (top-down: tool provides hypothesis → SPARQL verifies). For data tasks, raw triples provide the same grounding. For schema-only tasks (no data to explore), the tool is essential — it bridges the in-process/SPARQL gap for ontology axioms.

**Implicit RDFS reasoning materializes in chain of thought**: Phase 5 traces show agents performing domain/range reasoning, property direction analysis, and cross-graph navigation planning in their reasoning text — without calling the tool. The agent's pretraining knowledge of SOSA + SD structural hints (graph inventory, agent instruction, entity lookup example) produce equivalent reasoning to what the tool would provide.

**Entity lookup is a degenerate RDFS reasoner**: The `SELECT ?p ?o WHERE { GRAPH ?g { <iri> ?p ?o } }` example in SPARQL examples functions as a universal escape hatch — agents use it to discover schema post-hoc from returned predicates, bypassing the need for a priori ontological reasoning.

**Endpoint SD gap (obs-sio-measured-value)**: `shapes/endpoint-sosa.ttl` ObservationShape declares `sosa:hasSimpleResult` as required but test data uses `sio:has-attribute → MeasuredValue → sio:has-value`. Fixed in Phase 5 by adding `sio:has-attribute` property to ObservationShape + SIO examples + cross-graph agent instruction hint.

**In-process vs SPARQL gap**: Direct SPARQL against default graph returns empty for ontology schema triples (they're in named graphs like `/ontology/sio`). `ep.tbox_graph` bridges this — all ontology named graphs merged in-process via SPARQL CONSTRUCT at `discover_endpoint()` time.

**D9 L2 bridge pattern**: The `analyze_rdfs_routes` tool makes TBox knowledge callable, not just descriptive. Pattern: L2 TBox loaded in-process → tool wraps sub-agent LLM call → returns routing analysis → agent acts.

## Key Files

| File | Purpose |
|---|---|
| `agents/fabric_rdfs_routes.py` | `make_rdfs_routes_tool`, `RDFS_INSTRUCT_PATTERNS`, `extract_ontology_structure` |
| `agents/fabric_discovery.py` | `FabricEndpoint.tbox_graph`, `_resolve_vocab_graphs`, `_load_tbox` |
| `agents/fabric_agent.py` | `FabricQueryResult` with `iterations`, `converged` |
| `agents/fabric_validate.py` | `validate_result`, `make_validate_tool` |
| `agents/__init__.py` | Public API exports |
| `experiments/fabric_navigation/run_experiment.py` | Phase feature map, `kwarg_builder` with `_RDFS_TOOL_HINT` |
| `experiments/fabric_navigation/dspy_eval_harness.py` | `FabricNavHarness`, `FabricMetrics`, trajectory logging |
| `fabric/node/registry.py` | SPARQL builders for `/graph/registry` + `/graph/agents` (D12, D13, D14) |
| `fabric/node/catalog.py` | rdflib-based VoID→DCAT extraction (D23) |
| `fabric/node/integrity.py` | D26 content integrity — b58, SHA-256, `verify_related_resources` |
| `fabric/node/bootstrap.py` | TBox loading + registry self-entry + catalog population |

## Experiment Phase Map

| Phase | Features | Score | Notes |
|---|---|---|---|
| phase1.5 | baseline | 1.0 | Tasks too simple, copy from examples |
| phase2a | no-tbox-paths | 1.0 | SOSA pretraining saturates |
| phase2b | tbox-paths | 1.0 | +0.7 iter overhead (agent queries /ontology/sosa) |
| phase3a | no-tbox-paths | 0.833 | SIO range query fails without path hint |
| phase3b | tbox-paths | 1.000 | +0.167 lift for unfamiliar vocabulary |
| phase4a | no-rdfs-routes (control) | 1.000 | Same as phase3b |
| phase4b-r1 | rdfs-routes, no hint | 1.000 | 0/6 tool usage (tool not advertised in SD) |
| phase4b-r2+ | rdfs-routes + hint | 1.000 | 2/6 tool usage per run (schema tasks only); 8-run ensemble |
| phase5a | no-rdfs-routes, cross-graph | 1.000 | 4.0 iter, 3.0 SPARQL, 0.4 recoveries |
| phase5b | rdfs-routes, cross-graph | 1.000 | 4.0 iter, 3.0 SPARQL, 0.4 recoveries; 0/5 tool calls |
| phase6a | no-rdfs-routes, escape hatch closed | 1.000 | 4.0 iter, 3.0 SPARQL, 0 guardrail hits, 0.2 recoveries |
| phase6b | rdfs-routes, escape hatch closed | 1.000 | 4.0 iter, 3.0 SPARQL, 2 guardrail hits, 0/5 tool calls |

## Docker Stack

```bash
docker compose up -d    # from ~/dev/git/LA3D/agents/cogitarelink-fabric
# fabric-node: FastAPI :8080 (internal), Oxigraph :7878
# caddy: :80/:443 → fabric-node:8080
# endpoint: https://bootstrap.cogitarelink.ai (D30)
# /etc/hosts: 127.0.0.1 bootstrap.cogitarelink.ai (required on dev machine)
```

Run tests with:
```bash
SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem FABRIC_GATEWAY=https://bootstrap.cogitarelink.ai ~/uvws/.venv/bin/python -m pytest tests/ -v
cd tests && make test-all    # HURL (uses --cacert ../caddy-root.crt)
```

## Open Questions

- **When does the tool add value?** Only for schema introspection where no data exists to ground reasoning. For data tasks, raw triple exploration is equally effective. This may change with truly unfamiliar vocabularies outside pretraining.
- **Is the tool a guardrail or a capability?** Evidence suggests guardrail (confirmatory mode) rather than capability (new reasoning). The agent does implicit RDFS reasoning regardless — the tool externalizes and verifies it.
- **Pretraining saturation is the real variable**: Phases 1-6 all use vocabularies partially/fully in pretraining (SOSA, SSN, SIO, DCT). The untested claim: for genuinely unfamiliar vocabularies, the SD alone would be insufficient and the RDFS routes tool would become essential. This is the right next experiment but requires custom/obscure vocabulary.
- **D9 four-layer KR is validated**: SHACL shapes + SPARQL examples + agent hints + pretraining = sufficient for correct SPARQL construction against self-describing endpoints with known vocabularies.

## Findings Docs

- `~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/2026-02-23-phase4-rdfs-routes-findings.md`
- `~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/2026-02-24-phase5-cross-graph-findings.md`
- `~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/2026-02-24-phase6-escape-hatch-findings.md`

### D12/D13/D14/D23 Bootstrap Admission Patterns (2026-02-25)

**New routes** (6 added to `fabric/node/main.py`):
- `GET /fabric/registry` — CONSTRUCT from `/graph/registry`, content-negotiated
- `POST /fabric/admission` — full admission flow with D26 verification + witness co-signing
- `POST /agents/register` — proxy to Credo, INSERT into `/graph/agents`
- `GET /agents` — CONSTRUCT from `/graph/agents`
- `GET /agents/{agent_id}` — single agent CONSTRUCT
- `GET /.well-known/catalog` — CONSTRUCT from `/graph/catalog`

**Credo routes** (2 added to `fabric/credo/src/index.ts`):
- `POST /credentials/cosign` — witness co-signing with `previousProof` chain
- `POST /agents/register` — issues `AgentAuthorizationCredential`

**Bootstrap sequencing**: `start.sh` runs uvicorn in background first, polls healthcheck, then runs `bootstrap.py`. Fixes circular dependency: Credo's `waitForGateway()` needs gateway up → gateway needs bootstrap → bootstrap needs Credo VC.

**Self-admission deadlock**: Sync `httpx.get()` in `verify_related_resources` blocks event loop on self-request. Fix: `await asyncio.to_thread(verify_related_resources, remote_vc, fetcher)`.

**rdflib VOID namespace**: `rdflib.namespace.VOID` is a ClosedNamespace lacking `sparqlGraphEndpoint`. Use `VOID = Namespace("http://rdfs.org/ns/void#")` (open) instead.

**HURL patterns**: Use `header "Content-Type" contains "text/turtle"` (Oxigraph adds `; charset=utf-8`). Use `contains` not deprecated `includes`. Oxigraph Turtle uses full URIs — match `dcat#Dataset` not `dcat:Dataset`.

**Test counts**: 15 phase1 HURL + 27 phase2 HURL + 205 unit tests (36 registry + 16 catalog + 12 external endpoints + 14 integrity + 32 DID resolver + 84 existing + 11 integration)

### D30 Caddy HTTPS Migration Patterns (2026-03-01)

**Key files**:
- `fabric/caddy/Caddyfile`: `bootstrap.cogitarelink.ai { tls internal; reverse_proxy fabric-node:8080 }`
- `caddy-root.crt` (repo root, gitignored): Caddy's internal CA cert — export with `docker compose exec caddy caddy trust` or via volume
- `fabric/node/start.sh`: builds `/tmp/cogitarelink-ca-bundle.pem` = Caddy CA + `/etc/ssl/cert.pem` for container HTTPS self-calls

**NODE_BASE change requires volume reset**: DID is minted at first boot with the domain baked in. Changing `NODE_BASE` in `docker-compose.yml` requires `docker compose down -v` to wipe `did-data` volume and re-mint.

**Docker DNS for container self-calls**: `caddy` service needs `networks.default.aliases: [bootstrap.cogitarelink.ai]` so the fabric-node container can resolve the hostname to Caddy (not loopback). Without this, self-admission HTTP calls fail.

**pytest CA bundle**: `SSL_CERT_FILE=./caddy-root.crt` replaces the entire system CA bundle — Anthropic API calls via httpx then fail. Fix: create `/tmp/cogitarelink-ca-bundle.pem` = `cat caddy-root.crt /etc/ssl/cert.pem`. The Makefile does this automatically.

**HURL**: add `--cacert $(CA_CERT)` in `tests/Makefile`; CA_CERT := `../caddy-root.crt`

**macOS trust**: `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain caddy-root.crt`

**Domain convention**: `bootstrap.cogitarelink.ai` (prototype bootstrap node); future: `{unit}.{org}.cogitarelink.ai` (e.g. `crc.nd.cogitarelink.ai`)

**Production path**: Same Caddyfile without `tls internal` → automatic Let's Encrypt. No Caddyfile changes needed for production.

### D29 External Endpoint Attestation Patterns (2026-02-26)

**Turtle template substitution**: `external-endpoints.ttl.template` uses `{base}` and `{node_did}` placeholders, substituted by `load_external_endpoints_ttl()`. Same pattern as `void_templates.py`.

**POST vs PUT for Graph Store Protocol**: `PUT /store?graph=<uri>` replaces entire graph; `POST /store?graph=<uri>` appends to existing graph. External endpoints use POST (append to `/graph/catalog` alongside existing `dcat:Dataset` entries from VoID extraction).

**Turtle @prefix invalid in SPARQL INSERT DATA**: `@prefix` is Turtle-only syntax; SPARQL uses `PREFIX` (no `@`, no trailing `.`). Never embed raw Turtle inside `INSERT DATA {}` blocks. Use Graph Store Protocol POST with `Content-Type: text/turtle` instead.

**Catalog CONSTRUCT broadened**: `build_catalog_construct()` changed from `?ds a dcat:Dataset` filter to `?s ?p ?o` to return both Dataset and DataService entries from `/graph/catalog`.

**fabric:vouchedBy**: New OWL ObjectProperty (fabric.ttl v0.2.0). Domain: dcat:DataService, Range: fabric:FabricNode. Attests that a fabric node vouches for an external SPARQL endpoint's trustworthiness.

**New files**:
- `fabric/node/external-endpoints.ttl.template`: Three QLever entries with example SPARQL queries
- `fabric/node/external_endpoints.py`: Template loader (pure Python, same pattern as catalog.py/registry.py)
- `tests/hurl/phase2/48-external-endpoints-catalog.hurl`: Integration test
- `tests/pytest/unit/test_external_endpoints.py`: 12 unit tests including rdflib Turtle parsing validation
