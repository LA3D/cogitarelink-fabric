# cogitarelink-fabric

[![CodeMeta](https://img.shields.io/badge/CodeMeta-3.1-blue.svg)](https://w3id.org/codemeta/3.1)
[![Project Status: WIP](https://www.repostatus.org/badges/latest/wip.svg)](https://www.repostatus.org/#wip)

A research prototype exploring what happens when you build the knowledge substrate that agentic meshes assume exists — using W3C standards, FAIR principles, and decentralized identity — and then test whether LLM agents can actually navigate it.

## From data mesh to knowledge fabric

Three generations of mesh architecture have each added a layer to distributed systems.

**Service meshes** (Istio, Linkerd) solved microservice communication — sidecar proxies handling routing, observability, and mTLS between services so application code doesn't have to. **Data meshes** (Dehghani, 2019) solved organizational data ownership by applying four principles: domain-oriented decentralization, data as a product, self-serve infrastructure, and federated computational governance. Each domain owns its analytical data and publishes it as a discoverable, trustworthy, self-describing product. **Agentic meshes** extend the same pattern to autonomous agent ecosystems — the operational infrastructure where agents discover each other, collaborate on tasks, transact with governance, and operate with trust.

Each generation assumes the previous one exists. An agentic mesh assumes agents have something to discover, query, and curate — a knowledge substrate of self-describing data sources with machine-readable metadata, identity, and governance. Without that substrate, the mesh is infrastructure with nothing to operate on.

This project builds that substrate. A **knowledge fabric** is a federation of self-describing SPARQL endpoints where each node publishes enough structured metadata that an agent encountering it for the first time can discover what data exists, how it's organized, and how to query it — progressively, without bulk retrieval. The W3C standards stack already provides the components the agentic mesh needs:

| Mesh concern | W3C/standards realization |
|---|---|
| **Registry** (agent/data discovery) | VoID service descriptions + DCAT catalogs + PROF profiles |
| **Trust framework** (behavioral contracts) | SHACL shapes + DID/VC credentials |
| **Patterns & protocols** (interoperability) | SPARQL federation + LDN messaging + JSON-LD |
| **Governance** (federated rules) | SHACL-gated writes + shape-bound minting |
| **Monitor** (observability) | PROV-O provenance chains + named graph audit trails |
| **Identity** (zero-trust) | `did:webvh` + Verifiable Credentials (eddsa-jcs-2022) |

The contribution isn't inventing new standards. It's showing that the standards stack, taken seriously as engineering specification, provides what the agentic mesh assumes exists. Agentic software engineering tools make infrastructure cheap to build — any research group with a clear specification and an agentic coding assistant can stand up a working system in days. The remaining hard problem is interoperability: ensuring that what gets built can exchange data with what others build. Standards are the shared contracts. FAIR principles are the institutional framework for deciding which standards to adopt.

## Why a knowledge fabric

The dominant pattern for giving LLMs access to knowledge is retrieval-augmented generation: embed everything, retrieve the top-k chunks, stuff them into the prompt. This works for simple lookup but breaks in three ways at scale. First, the relevant information depends on schema relationships the agent hasn't discovered yet — you can't embed your way to understanding that `sio:has-attribute` chains to `sio:has-value` via an intermediate node. Second, stuffing a context window with pre-fetched chunks forecloses navigation — the ability to follow a lead from one piece of information to the next. Third, there is no interoperability — every system has its own markdown files, its own vector store, its own conventions.

A self-describing knowledge fabric inverts this. Instead of dumping context, the agent starts with a compact service description and drills into ontology structure, shapes, and query examples only as needed. Each layer adds precision without overwhelming the context window. The RLM (Recursive Language Model) REPL makes this practical: SPARQL results live in Python variables — unbounded — while the LLM sees only a size-capped observation per iteration. The agent doesn't receive pre-built context; it actively constructs its own context by navigating structured metadata. This is what makes knowledge graphs useful for agents — not that they store triples, but that their structure enables agents to manage their own attention.

This is also the interoperability argument. Markdown files don't federate. Vector stores don't self-describe. An agent that learns to navigate one fabric node — reading VoID, following SHACL shapes, writing SPARQL — can navigate any conformant node. The same progressive disclosure pattern works across endpoints, across institutions, across vocabularies. At federation scale, navigation becomes iterative map-reduce: a TBox pass (once, cacheable) builds a routing map of what data exists where, then an ABox pass (per question, iterative) dispatches targeted queries to the right endpoints with the right vocabulary. Details in [docs/architecture.md](docs/architecture.md).

## The two-level experiment

This repository is two experiments running simultaneously, each informing the other.

### Construction agents: spec-driven agentic software engineering

The infrastructure in this repository was built by [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — a software engineering agent — working from W3C specifications and architectural decisions provided by a human researcher. The human doesn't dictate code. They curate specifications (SPARQL 1.2 Protocol, W3C DID Resolution, VC Data Model 2.0, LDN, SHACL) and approve designs. The agent writes [Hurl](https://hurl.dev/) conformance tests encoding specific spec requirements *before* the implementation exists, then writes code to make them pass.

The development process is constrained by [Superpowers](https://github.com/obra/superpowers) — an agentic skills framework that enforces hard gates: brainstorming (no code until design approved) → planning (tasks decomposed with verification steps) → TDD (no production code without a failing test) → code review (spec compliance before merge) → verification (no success claims without fresh evidence). The git history records every RED→GREEN transition. The `[Agent: Claude]` commit prefix makes agent-authored work auditable. The result is a 309-test conformance suite (242 unit + 20 integration + 47 HTTP) built against W3C specifications by an agent that reads the specs, not by a human who hand-translates them.

### Operational agents: navigating self-describing endpoints

The infrastructure built by the construction agent becomes the test environment for operational agents — [DSPy](https://github.com/stanfordnlp/dspy) RLM programs that navigate the fabric's self-describing SPARQL endpoints. Each experiment phase adds or removes a knowledge representation layer to measure its contribution. A 6-task SIO (Semanticscience Integrated Ontology) benchmark tests whether the four-layer KR stack provides sufficient scaffolding for agents to query unfamiliar knowledge graphs correctly.

### The feedback loop

The operational agents' performance reveals what the infrastructure needs. Phase 3 showed that TBox path hints are necessary for unfamiliar vocabularies (+0.167 score lift). Phase 4 showed that tool advertisement in the service description is required for agent adoption (0/6 usage without it, 2/6 with it). Phase 7 showed that catalog discovery changes agent behavior — grounded SPARQL answers versus pretraining recall — even when scores are identical. Each finding feeds back into the next infrastructure iteration: the construction agent implements the fix, the operational agents are re-tested. The two levels are a co-evolutionary loop.

Both levels face the same structural problem: specification → validation → identity → provenance → human accountability. The governance model is described in [docs/governance-model.md](docs/governance-model.md).

## Architecture

Three-container fabric node per endpoint:

- **FastAPI gateway** (`fabric/node/`) — `.well-known/` self-description, `/entity/` URI dereferencing, `/sparql` proxy with content negotiation, VP-gated access control
- **Oxigraph** — SPARQL 1.2 triplestore with named graph storage
- **Credo-TS sidecar** (`fabric/credo/`) — DID/VC identity layer: `did:webvh` node identity, `FabricConformanceCredential` issuance, VP creation/verification

### D9: Four-layer knowledge representation

The core architectural claim. Each fabric node exposes four layers of structured metadata:

| Layer | Standard | Endpoint | What it tells the agent |
|---|---|---|---|
| **L1** Service Description | VoID + PROF | `/.well-known/void`, `/.well-known/profile` | What vocabularies exist, what named graphs are available, what profile this node conforms to |
| **L2** TBox Ontologies | OWL/RDFS | `/ontology/{vocab}` named graphs | Class hierarchies, property domains/ranges, subclass relationships |
| **L3** SHACL Shapes | SHACL 1.2 | `/.well-known/shacl` | Data constraints, expected property paths, `sh:agentInstruction` with query templates |
| **L4** Query Examples | spex: (SIB pattern) | `/.well-known/sparql-examples` | Working SPARQL queries demonstrating common access patterns |

The agent reads L1 first (compact, orients), then drills into L2–L4 as needed. The `discover_endpoint()` function loads all four layers into a `FabricEndpoint` object that produces a `routing_plan` the RLM agent reads as initial context.

### Self-description as linked contracts

The four layers are linked through shared IRIs. The PROF profile (`fabric:CoreProfile`) declares what a conforming node must provide. Each named graph declares its governing SHACL shape via `dct:conformsTo`. That shape IRI threads through VoID, the Service Description, and the SHACL document — creating a verifiable chain from profile to shape to data:

```
fabric:CoreProfile (PROF)
  ├── role:schema      → SOSA, SIO, OWL-Time, PROV-O (TBox ontologies)
  ├── role:constraints → fabric:ObservationShape, fabric:EntityShape (SHACL)
  ├── role:example     → SPARQL examples catalog
  └── role:guidance    → progressive disclosure instructions

VoID root dataset
  dct:conformsTo → fabric:CoreProfile
  void:subset /graph/observations
    dct:conformsTo → fabric:ObservationShape  ←── same IRI
```

Read contracts (agents verify what a graph contains before querying), write contracts (SHACL validation gates data writes), and vocabulary contracts (Five Stars criteria as SHACL admission shapes) are detailed in [docs/architecture.md](docs/architecture.md).

### Agent substrate

Agents are DSPy RLM programs — Recursive Language Models (Zhang, Kraska, & Khattab, 2025). An RLM operates a Python REPL loop: the LLM writes code, executes it, reads the output, writes more code — iterating until it can produce an answer. Fabric tools (`sparql_query`, `analyze_rdfs_routes`, `query_external_sparql`) are injected into the REPL namespace. SPARQL results live in Python variables (variable space, unbounded); the LLM sees only size-capped observations per iteration (token space, bounded). The agent substrate is separate from the fabric infrastructure — agents connect externally via HTTP.

For the full treatment of identity, credentials, content integrity, and the map-reduce federation pattern, see [docs/architecture.md](docs/architecture.md). For identifier persistence and the `did:webvh` trust model, see [docs/identifier-persistence.md](docs/identifier-persistence.md). For the research integrity argument and NSF policy context, see [docs/research-integrity.md](docs/research-integrity.md). For FAIR principles as the design philosophy, see [docs/fair-and-agents.md](docs/fair-and-agents.md).

## Experimental results

Experiments use a 6-task SIO benchmark run against a local fabric node. SIO is outside the LLM's pretraining distribution, making it a fair test of whether structured metadata actually helps.

| Phase | What changed | Score | Key finding |
|---|---|---|---|
| **1.5** Baseline | VoID + SHACL + examples | 1.000 | SOSA tasks too easy — copy from examples |
| **2a/2b** TBox paths | ± `/ontology/sosa` hints | 1.000 | SOSA in pretraining; no lift |
| **3a** No TBox (SIO) | SIO tasks, no hints | 0.833 | SIO not in pretraining; range query fails |
| **3b** TBox paths (SIO) | Add `/ontology/sio` hints | 1.000 | **+0.167 lift** — TBox recovers failing task |
| **4b** RDFS routes tool | `analyze_rdfs_routes()` | 1.000 | 2/6 adoption (schema tasks only); 8-run ensemble |
| **5a/5b** Cross-graph | Observations ↔ entities joins | 1.000 | Tool never invoked; implicit reasoning suffices |
| **6a/6b** Escape hatch | Entity lookup removed + guardrail | 1.000 | No effect — agent uses shapes, not scanning |
| **7a** No catalog | Control (local only) | 1.000 | Agent falls back to pretraining recall |
| **7b** Catalog + external | QLever PubChem/Wikidata/OSM | 1.000 | Grounded SPARQL answers vs recall; 1.7 ext queries/task |

**Phase 3 is the central result**: for vocabularies outside pretraining, TBox structural hints provide a measurable score lift. The structured metadata isn't decorative — it's necessary for correct query construction when the LLM can't fall back on memorized patterns.

**Phase 4 reveals selective tool adoption**: the `analyze_rdfs_routes` tool is called only for schema introspection tasks (inverse properties, range constraints) where no instance data exists to explore. For data tasks, raw triples provide sufficient grounding. The tool shifts reasoning mode from exploratory to confirmatory — it's a guardrail, not a new capability.

**Phases 5–7 validate the D9 design**: agents construct targeted SPARQL from SHACL shapes and examples without falling back to blind triple scanning, even when the escape hatch is closed. Catalog discovery changes agent behavior (grounded answers vs pretraining recall) even when scores are identical — a distinction that matters for scientific applications.

Detailed trace analysis, protoknowledge theory connections (Ranaldi et al., 2025), and methodological notes are in [docs/experimental-results.md](docs/experimental-results.md).

## Getting started

### Prerequisites

- Docker + Docker Compose
- Python 3.12+ with [uv](https://github.com/astral-sh/uv)
- [Hurl](https://hurl.dev/) (for HTTP integration tests)

### Start the fabric stack

```bash
docker compose up -d

# Verify all three containers are healthy
docker compose ps

# Inspect the self-description (requires caddy-root.crt — see tests/Makefile)
curl -s --cacert caddy-root.crt https://bootstrap.cogitarelink.ai/.well-known/void | head -20
```

### Install Python dependencies

```bash
uv pip install -e ".[test]"
```

### Run the test suite

```bash
# Unit + integration tests
SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem \
  FABRIC_GATEWAY=https://bootstrap.cogitarelink.ai \
  pytest tests/ -v

# Hurl HTTP conformance tests (requires running fabric stack)
cd tests && make test-hurl-p1    # Phase 1: self-description + SPARQL + content negotiation
cd tests && make test-hurl-p2    # Phase 2: DID resolution, VCs, LDN, content integrity
```

### Run an experiment

```bash
python experiments/fabric_navigation/run_experiment.py \
    --tasks experiments/fabric_navigation/tasks/phase3-sio-tbox.json \
    --phase phase3b-tbox-paths \
    --output experiments/fabric_navigation/results/ \
    --model anthropic/claude-sonnet-4-6 \
    --verbose
```

## Repo structure

```
fabric/
  node/                FastAPI gateway + self-description + DID resolution
  credo/               Credo-TS sidecar (DID/VC identity layer)
  caddy/               TLS-terminating reverse proxy
agents/              DSPy/RLM agent implementations
  fabric_discovery.py   Four-layer endpoint discovery (D9)
  fabric_agent.py       FabricQuery signature + result types
  fabric_query.py       SPARQL query tool for RLM REPL
  fabric_rdfs_routes.py RDFS/OWL routing analysis tool
  fabric_validate.py    SHACL validation tool
  fabric_write.py       Write-side tools (discover, write, validate, commit)
ontology/            TBox cache: SOSA, SSN, SIO, OWL-Time, PROV-O, DCAT, ODRL, Fabric
shapes/              SHACL shapes (endpoint-specific constraints)
sparql/              SPARQL examples catalog (SIB spex: pattern)
experiments/
  fabric_navigation/    Python experiment runner + eval harness
  node-rlm-fabric/      JS/TypeScript experiment runner (Comunica + node-rlm)
docs/                Deep-dive essays (architecture, governance, experimental analysis)
scripts/             CLI tools (sparql_query, shacl_validate)
credentials/         Mock VCs (Phase 1)
provenance/          SPDX SBOM + PROV-O activity records
tests/
  hurl/phase1/       HTTP conformance tests (15 Hurl files)
  hurl/phase2/       Identity + trust integration tests (27 Hurl files + 5 utility)
  pytest/unit/       Agent tooling + identity unit tests
  pytest/integration/ Full-stack integration tests
.claude/
  rules/             Decisions index, Python patterns, coding style
```

## Key decisions

Architectural decisions are tracked in `.claude/rules/decisions-index.md` (D1–D30). The most relevant:

| # | Decision | Why it matters |
|---|---------|----------------|
| D7 | PROF + VoID + SHACL + SPARQL examples at `.well-known/` | The self-description stack that agents read |
| D9 | Four-layer KR: SD → TBox → shapes → examples | Progressive disclosure of endpoint knowledge |
| D13 | VP-gated SPARQL via Verifiable Presentations | Agent identity + authorization on every query |
| D22 | Fabric ontology at `https://w3id.org/cogitarelink/fabric` | OWL 2 DL vocabulary for fabric concepts |
| D25 | Linked Data Notifications for actor-to-actor messaging | W3C LDN; every DID advertises an inbox |
| D27 | SHACL-gated vocabulary admission | TBox ontologies must pass metadata shapes |
| D30 | HTTPS-first via Caddy + `bootstrap.cogitarelink.ai` | Restores full did:webvh trust chain |

## References

- Dehghani, Z. (2022). *Data Mesh: Delivering Data-Driven Value at Scale*. O'Reilly Media.
- Wilkinson, M. D., et al. (2016). The FAIR Guiding Principles for scientific data management and stewardship. *Scientific Data*, 3, 160018. https://doi.org/10.1038/sdata.2016.18
- Janowicz, K., Hitzler, P., Adams, B., Kolas, D., & Vardeman II, C. (2014). Five Stars of Linked Data Vocabulary Use. *Semantic Web*, 5(3), 173–176. https://doi.org/10.3233/SW-130175
- Cox, S. J. D., et al. (2021). Ten Simple Rules for Making a Vocabulary FAIR. *PLOS Computational Biology*, 17(6), e1009041. https://doi.org/10.1371/journal.pcbi.1009041
- Zhang, A. L., Kraska, T., & Khattab, O. (2025). Recursive Language Models. arXiv:2512.24601v2. https://arxiv.org/abs/2512.24601
- Ranaldi, F., et al. (2025). Protoknowledge shapes behaviour of LLMs in downstream tasks. arXiv:2505.15501. https://arxiv.org/abs/2505.15501
- Allemang, D. & Sequeda, J. (2024). Increasing the LLM Accuracy for Question Answering: Ontologies to the Rescue! *ESWC* (LNCS, pp. 324–339). https://arxiv.org/abs/2405.11706

## Identity

**Owner**: Charles F. Vardeman II
**ORCID**: https://orcid.org/0000-0003-4091-6059
**Institution**: University of Notre Dame (https://ror.org/00mkhxb43)
**Lab**: Laboratory for Assured AI Applications Development (LA3D)
**License**: Apache-2.0
