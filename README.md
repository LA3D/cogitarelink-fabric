# cogitarelink-fabric

A research prototype testing whether semantic web self-description standards give LLM-based agents enough structure to navigate unfamiliar knowledge graphs correctly — without hand-tuned prompts or domain-specific training.

## The idea

The semantic web was designed for machine-readable self-description: endpoints that declare their vocabularies (VoID), constrain their data shapes (SHACL), and provide query templates (SPARQL examples). The machines that could actually use this were never built — until now. LLM-based agents can read structured metadata, reason about ontology relationships, and write SPARQL queries iteratively in a REPL loop. This project tests whether the original self-description stack, taken seriously, gives these agents a usable navigation substrate.

A **knowledge fabric** is a federation of self-describing SPARQL endpoints where each node publishes enough structured metadata that an agent encountering it for the first time can discover what data exists, how it's organized, and how to query it — progressively, without bulk retrieval. The agent doesn't need to know the endpoint in advance; the endpoint tells the agent what it needs to know, layer by layer.

**Progressive disclosure** is the retrieval pattern: instead of dumping all context into a prompt (RAG-style), the agent starts with a compact service description and drills into ontology structure, shapes, and examples only as needed. Each layer adds precision without overwhelming the context window.

## The hypothesis

Structured KR layers — VoID service descriptions, cached TBox ontologies, SHACL shapes with agent instructions, and SPARQL example catalogs — provide sufficient navigational scaffolding for RLM (Recursive Language Model) agents to query unfamiliar knowledge graphs correctly. The scaffolding should measurably outperform unstructured baselines, especially for vocabularies outside the LLM's pretraining distribution.

## Architecture

Three-container fabric node per endpoint:

- **FastAPI gateway** (`fabric/node/`) — `.well-known/` self-description endpoints, `/entity/` URI dereferencing, `/sparql` proxy with content negotiation
- **Oxigraph** — SPARQL 1.2 triplestore with named graph storage (TBox ontologies, observation data, entity graphs)
- **Credo-TS sidecar** (`fabric/credo/`) — DID/VC identity layer: creates node DID at startup, self-issues a FabricConformanceCredential binding the node's self-description artifacts to cryptographic hashes, serves DID resolution and VC verification endpoints

### D9: Four-layer knowledge representation

The core architectural claim. Each fabric node exposes four layers of structured metadata, each serving a distinct navigation purpose:

| Layer | Standard | Endpoint | What it tells the agent |
|---|---|---|---|
| **L1** Service Description | VoID + PROF | `/.well-known/void`, `/.well-known/profile` | What vocabularies exist, what named graphs are available, what profile this node conforms to |
| **L2** TBox Ontologies | OWL/RDFS | `/ontology/{vocab}` named graphs | Class hierarchies, property domains/ranges, subclass relationships — the structural skeleton of each vocabulary |
| **L3** SHACL Shapes | SHACL 1.2 | `/.well-known/shacl` | Data constraints, expected property paths, `sh:agentInstruction` with concrete query templates |
| **L4** Query Examples | spex: (SIB pattern) | `/.well-known/sparql-examples` | Working SPARQL queries demonstrating common access patterns |

The agent reads L1 first (compact, orients), then drills into L2-L4 as needed. The `discover_endpoint()` function in `agents/fabric_discovery.py` loads all four layers into a `FabricEndpoint` object, which produces a `routing_plan` text that the RLM agent reads as its initial context.

### Agent substrate: RLM as context engineering

Agents are [DSPy](https://github.com/stanfordnlp/dspy) RLM programs (Recursive Language Models). An RLM operates a Python REPL loop: the LLM writes code, executes it, reads the output, writes more code — iterating until it can produce an answer. Fabric tools (`sparql_query`, `analyze_rdfs_routes`) are injected into the REPL namespace so the agent can call them from generated code.

The agent substrate is separate from the fabric infrastructure. Agents connect externally via HTTP; the fabric node does not host agents.

**Why RLM and not RAG?** The core problem with knowledge graph navigation is that the relevant data far exceeds any context window. A SPARQL endpoint might hold millions of triples across dozens of named graphs. RAG's answer — embed everything, retrieve the top-k chunks — doesn't work here because the "relevant" triples depend on schema relationships the agent hasn't discovered yet. You can't embed your way to understanding that `sio:has-attribute` chains to `sio:has-value` via an intermediate `MeasuredValue` node; you have to read the ontology structure and follow it.

RLM solves this by separating two spaces:

- **Variable space** holds arbitrarily large artifacts. Full SPARQL result sets, parsed ontology graphs, and accumulated entity data live in Python variables across iterations. The agent can hold an entire TBox in a variable and query it locally without consuming context tokens.
- **Token space** holds bounded observations. Each iteration, the agent sees only a size-capped view of what its code produced — enough to reason about what to do next, not enough to overwhelm the context window.

This separation turns the agent into a context engineering system. Instead of stuffing everything into the prompt and hoping the LLM finds the needle, the agent actively constructs its own context: it writes code to fetch metadata, parses the response into variables, inspects the parts it needs, and builds progressively more targeted queries. Each REPL iteration narrows the search space rather than broadening the context.

### Scatter-gather and agentic search

A single fabric node is useful, but the architecture is designed for federation: multiple autonomous nodes, each self-describing, each queryable by the same agent using the same tools.

Navigating a federation is iterative scatter-gather. The agent fans out queries to multiple endpoints in parallel, reduces the results through semantic judgment (ontology alignment, entity resolution, conflict handling), and decides what to query next based on what it learned. This operates at two levels:

**TBox scatter-gather** (run once per fabric, cacheable): The agent queries each endpoint's `.well-known/` metadata — VoID descriptions, SHACL shapes, SPARQL examples. It assesses vocabulary quality, identifies shared and divergent terms, and builds a navigation map of what data exists where and how vocabularies relate. This phase is cheap (metadata is small) and produces the routing knowledge that makes data queries efficient.

**ABox scatter-gather** (per question, iterative): Using the navigation map, the agent dispatches data queries to the right endpoints with the right vocabulary. Results come back, the agent resolves entities across sources, handles conflicts, identifies gaps, and iterates. The reduce step requires semantic judgment — recognizing that `up:encodedBy` and `gene:expresses` describe the same biological relationship across two endpoints — which is exactly what LLMs are good at.

**How self-description reduces iterations.** Without self-describing metadata, an agent encountering an unfamiliar endpoint must explore by trial and error: guess at property names, issue broad queries, read the returned predicates, infer the schema post-hoc, and try again with better-informed queries. Our Phase 3 experiments measured this directly — against SIO (a vocabulary outside the LLM's pretraining), agents without TBox structural hints failed on schema reasoning tasks that required knowing property directions and range constraints.

With self-description, the agent reads the endpoint's VoID to learn what named graphs and vocabularies exist, reads the SHACL shapes to learn what properties connect which classes, and reads the SPARQL examples to see working query patterns. Each of these steps narrows the search space *before the first data query is issued*. The agent doesn't have to guess what the endpoint contains; the endpoint tells it. Our Phase 3b result — a 0.167 score lift from adding TBox path hints — quantifies the difference between grounded and ungrounded query construction for unfamiliar vocabularies.

This is also a response to the needle-in-a-haystack problem at a structural level. The traditional version of this problem asks whether an LLM can find a specific fact buried in a long context. The fabric version asks whether an agent can find the right triples across a federation of endpoints it has never seen before. Self-describing metadata converts this from a search problem (scan everything until you find it) into a navigation problem (follow the metadata to the right graph, the right shape, the right query pattern). Navigation scales; exhaustive search does not.

### Identity, credentials, and content integrity

The fabric uses W3C and Decentralized Identity Foundation (DIF) standards for node identity and trust. Every standard referenced here has an existing specification, multiple interoperable implementations, and an active community. We chose to adopt them rather than design custom authentication or integrity mechanisms for the same reason we use SHACL rather than inventing a constraint language: the problems are already solved, the edge cases are already discovered, and agents that learn to work with one fabric node can transfer that knowledge to any conformant node.

**Decentralized Identifiers (DIDs)** — Each fabric node has a [did:webvh](https://w3c-ccg.github.io/did-method-webvh/) identifier, a DID method that combines web discoverability with a cryptographically verifiable history log. The node's DID document advertises its verification keys and service endpoints (SPARQL, SHACL, VoID, LDN inbox). Agents resolve DIDs via the W3C DID Resolution HTTP API to discover what a node offers before interacting with it.

Why DIDs and not API keys or OAuth? Because the trust relationship is peer-to-peer, not client-server. A fabric is a federation of autonomous nodes. No central authority issues tokens. Each node proves its identity through its own key material, and any node can verify any other node's claims by resolving its DID and checking signatures. This is the same trust model that the web itself uses (DNS + TLS), extended to machine-readable identity documents.

**Verifiable Credentials (VCs)** — At bootstrap, each node self-issues a `FabricConformanceCredential` following the [W3C Verifiable Credentials Data Model 2.0](https://www.w3.org/TR/vc-data-model-2.0/). This credential attests that the node conforms to `fabric:CoreProfile` and includes a service directory pointing to the node's endpoints. The credential is signed with an [eddsa-jcs-2022](https://www.w3.org/TR/vc-di-eddsa/) Data Integrity proof — JSON Canonicalization Scheme (JCS) + Ed25519, no JSON-LD processing required.

The VC structure matters because it separates the claim ("this node serves SOSA observation data at these endpoints") from the proof ("signed by the node's Ed25519 key at this timestamp"). Agents can verify the signature without trusting the transport layer. When bootstrap-attested credentials arrive (Phase 3), the same VC structure supports multi-proof chaining: the node signs first, then a bootstrap witness co-signs, creating a chain of attestation with no new machinery.

**Content integrity** (D26) — The conformance credential includes a `relatedResource` array (VC Data Model 2.0 §5.3) binding each self-description artifact to its SHA-256 hash:

```json
"relatedResource": [
  {
    "id": "http://localhost:8080/.well-known/void",
    "digestMultibase": "zBKaAuRCu9dMruLbstDUm4WPaRsGggUC8Ei3H47d7B9Sw",
    "digestSRI": "sha256-mVbUgqHTiCiUO3T2jkbHjW2VqvTGrPoFinSPStFcknA=",
    "mediaType": "text/turtle"
  }
]
```

This lets an agent verify that the VoID, SHACL shapes, and SPARQL examples it fetches haven't changed since the credential was issued. The `digestMultibase` format (multibase base58btc prefix `z` + raw SHA-256) follows the conventions used across the DID and VC ecosystem. The `digestSRI` format (Subresource Integrity) follows the W3C SRI specification for browser-compatible verification. Both are computed from the same hash; agents can use whichever format their toolchain supports.

**Linked Data Notifications (LDN)** — Every DID (agent, human, node) advertises an [LDN inbox](https://www.w3.org/TR/ldn/) as a service endpoint. Nodes use `POST /inbox` to deliver JSON-LD notifications (trust gap alerts, catalog updates, delegation requests). The inbox is discoverable via a `Link` header on the DID document, following the LDN specification's discovery mechanism. This replaces custom webhook endpoints with a standard protocol that any LDN-aware client can use.

**Why standards over custom protocols?** Three practical reasons:

1. **Agent transferability.** An agent that learns to resolve a DID, verify a VC signature, and check a `digestMultibase` hash against one fabric node can do the same against any node — or any system outside this project that uses the same standards. Custom protocols create vendor lock-in for agents, not just humans.

2. **Composability.** VC multi-proof chaining, LDN notification delivery, and DID-based service discovery all compose without glue code because they were designed to work together. Adding human-in-the-loop approval (D19) requires no new protocol — it's a second proof on the same credential, delivered via the same inbox.

3. **Edge cases already handled.** DID resolution has defined error codes. VC validation has defined processing rules. Content integrity via `digestMultibase` has defined canonicalization paths (raw bytes now, RDFC-1.0 later). Custom protocols tend to discover these edge cases in production.

## Experimental results

Experiments use a 6-task SIO (Semanticscience Integrated Ontology) benchmark run against a local fabric node. SIO is outside the LLM's pretraining distribution, making it a fair test of whether structured metadata actually helps navigation. Each experiment phase adds or removes a KR layer to measure its contribution.

The experiment runner (`experiments/fabric_navigation/run_experiment.py`) manages task setup/teardown, configures phase-specific features, and produces JSON result files with per-task scores, iteration counts, and cost estimates.

### Phase summary

| Phase | What changed | Score | Key finding |
|---|---|---|---|
| **1.5** Baseline | VoID + SHACL + examples | 1.000 | SOSA tasks too easy — agents copy from SPARQL examples |
| **2a** No TBox paths | Full SD, no TBox path hints | 1.000 | SOSA is in pretraining; structured metadata adds no lift |
| **2b** TBox paths | Add `/ontology/sosa` path hints to routing plan | 1.000 | Agent queries TBox graph (+0.7 iterations overhead) — curious but not harmful |
| **3a** No TBox paths (SIO) | Switch to SIO tasks, no TBox hints | 0.833 | SIO is *not* in pretraining; `sio-measured-value-range` fails without structural guidance |
| **3b** TBox paths (SIO) | Add `/ontology/sio` path hints | 1.000 | **+0.167 score lift** — TBox paths recover the failing task |
| **4a** Control | Phase 3b features, no RDFS tool | 1.000 | Baseline for tool comparison |
| **4b** RDFS routes tool | Add `analyze_rdfs_routes()` callable tool | 1.000 | Tool adopted selectively: 2/6 tasks per run (schema introspection only); 8-run ensemble |
| **5a** Cross-graph, no tool | Cross-graph joins (observations ↔ entities) | 1.000 | 4.0 iterations, 3.0 SPARQL queries, 0.4 recoveries per task |
| **5b** Cross-graph, with tool | Same tasks + `analyze_rdfs_routes` available | 1.000 | Tool never invoked (0/5 tasks); implicit reasoning in chain of thought suffices |
| **6a** Escape hatch closed, no tool | Entity lookup example removed + unbounded query guardrail | 1.000 | No effect — agent never relied on `?p ?o` scanning |
| **6b** Escape hatch closed, with tool | Same + `analyze_rdfs_routes` available | 1.000 | Tool never invoked; 2 guardrail hits (attempted scans correctly blocked) |

**Phase 3 is the central result**: for vocabularies outside pretraining, TBox path hints in the routing plan provide a measurable score lift. The structured metadata isn't just nice to have — it's necessary for correct query construction when the LLM can't fall back on memorized patterns.

**Phase 4 reveals selective tool adoption**: Detailed trace analysis across 8 ensemble runs corrected an initial claim of uniform tool usage. The `analyze_rdfs_routes` tool is called only for schema introspection tasks where no data exists to explore (e.g., `owl:inverseOf` lookup, `rdfs:range` queries). For data tasks where raw triples provide sufficient grounding, the agent never calls the tool. The tool shifts reasoning mode from exploratory (bottom-up: read data, infer schema) to confirmatory (top-down: tool provides hypothesis, SPARQL verifies) — it's a guardrail, not a new capability.

**Phases 5–6 test structural resilience**: Phase 5 added cross-graph join tasks requiring the agent to navigate between `/graph/observations` and `/graph/entities`. Phase 6 closed the "entity lookup escape hatch" — the `SELECT ?p ?o WHERE { <iri> ?p ?o }` pattern that lets agents discover schema post-hoc by reading returned predicates. Neither change affected scores. The agent constructs targeted SPARQL queries directly from SHACL shapes, SPARQL examples, and pretraining knowledge, without falling back to blind triple scanning. This validates the D9 four-layer KR design: the self-description stack is load-bearing, and agents use it as intended.

**The score ceiling**: All phases from 3b onward score 1.000. This is a limitation of the current benchmark — tasks are solvable once the right structural hints are present. The untested claim is that for genuinely unfamiliar vocabularies (outside pretraining entirely), the self-description alone would be insufficient and the RDFS routes tool would become essential. Testing this requires custom or obscure vocabularies, which is the right next experiment.

### What the traces reveal about agent reasoning

The RLM REPL loop produces full chain-of-thought traces: every iteration records the agent's reasoning text, the Python code it writes, and the SPARQL results it reads. Across 8 ensemble runs of Phase 4b and the Phase 5–6 experiments, these traces show how agents actually navigate the fabric — and where structured metadata shapes their reasoning.

**Two reasoning modes.** The clearest pattern in the traces is a split between exploratory and confirmatory reasoning, depending on whether the agent has data to inspect.

On data tasks (retrieving measurements, finding units, identifying chemical entities), agents reason bottom-up. They issue a SPARQL query based on the SHACL shapes and agent instructions, read the returned triples, and adjust. A typical trace reads: "Let me see what predicates exist in this graph" → issues a query → reads `sio:has-attribute`, `sio:has-value` in the results → constructs a targeted multi-hop query. The agent discovers schema from data. It never calls the RDFS routes tool for these tasks (0/8 runs across all data tasks).

On schema introspection tasks (finding inverse properties, determining range constraints), no data exists to explore — the question is about ontology axioms, not stored triples. Here the agent shifts to top-down reasoning. It calls `analyze_rdfs_routes("What is the inverse of sio:has-attribute?")`, reads the structured analysis, and its subsequent reasoning shifts register: "The analysis **confirms** that `sio:is-attribute-of` is the inverse." The tool provides a hypothesis; the agent verifies it with SPARQL. This confirmatory mode appeared in 7/8 runs for `sio-attribute-inverse` and 8/8 runs for `sio-measured-value-range`.

**Tool use is adaptive, not reflexive.** Agents don't call the tool as a first step. The consistent pattern: read the service description → write an initial SPARQL query → get empty or partial results → *then* call the tool for guidance → write a corrected query. The tool hint in the service description says "call before querying unfamiliar vocabularies or multi-hop properties," and agents appear to heed the "unfamiliar" qualifier — they try the direct approach first and consult the tool only when that fails. This is the right behavior: targeted guidance when stuck, not a pre-query ceremony.

**Implicit RDFS reasoning.** Phase 5 traces show agents performing ontological reasoning in their chain-of-thought text without the tool. For a cross-graph join task, one agent wrote: "I need to find the sensor IRI from the observation using `sosa:madeBySensor`, then get the sensor's label from the entities graph" — correctly inferring the domain/range of `madeBySensor` and knowing that `rdfs:label` lives on the entity, not the observation. For a property-direction task, agents went straight to `sosa:observes` on the Sensor entity in `/graph/entities` rather than trying `sosa:observedProperty` on the Observation — a distinction that requires knowing which class each property attaches to. None of these agents called the tool. They reasoned from SHACL shapes, SPARQL examples, agent instruction hints, and pretraining knowledge of SOSA/SSN vocabulary.

**The tool as guardrail.** This implicit reasoning raises the question: if agents can do RDFS reasoning without the tool, what does the tool actually provide? The trace evidence supports a guardrail interpretation rather than a capability interpretation. The tool doesn't enable reasoning the agent can't do — it externalizes and verifies reasoning the agent does implicitly. An agent that says "the ontology confirms `sio:is-attribute-of` is the inverse of `sio:has-attribute`" is making an auditable, reproducible claim grounded in the TBox. An agent that infers the same relationship from returned triples is making an empirical generalization from a sample. Both reach the correct answer at current task difficulty, but the guardrail version is more trustworthy — and would be easier to debug when the agent gets it wrong.

**Where the tool has unique value.** The selective adoption pattern (2/6 tasks) identifies the tool's niche precisely: schema-only questions where no instance data exists to ground reasoning. When the agent needs to know whether `sio:has-attribute` has an inverse, or what the range of `sio:has-value` is, there are no triples in `/graph/observations` that would reveal this — the axioms live in the TBox ontology graph, which isn't directly queryable via the agent's SPARQL tool. The RDFS routes tool bridges this gap. For data tasks, raw triples provide the same grounding more directly.

**The open question: pretraining saturation.** All six experiment phases used vocabularies at least partially present in the LLM's pretraining corpus (SOSA, SSN, SIO, Dublin Core). The implicit RDFS reasoning we observe could be the agent recalling memorized ontology structure rather than reasoning from the self-description metadata. The untested hypothesis: for a vocabulary genuinely absent from pretraining — one where the agent has no implicit model of property directions, domain/range constraints, or class hierarchies — the self-description signals alone would be insufficient, and the RDFS routes tool would shift from guardrail to genuine capability. Testing this requires custom or obscure vocabularies with plausible but misleading property names, where the only way to disambiguate is to consult the ontology structure. This is the right next experiment.

### Methodological notes

- **Domain contamination audit**: The RDFS instructional patterns were originally copied with SOSA-specific examples. When run against SOSA endpoints, this leaked domain knowledge into the sub-agent prompt — a confound. All examples were replaced with fully abstract vocabulary (`:ClassX`, `:propA`). Clean reruns confirmed identical results, establishing that the tool works from ontology structure, not from domain-specific examples in the prompt.
- **Prompt caching trap**: Initial ensemble replications at `temperature=None` produced identical traces — Anthropic's server-side prompt caching was returning cached responses. Fixed by running at `temperature=0.7` with `cache=False`. Varying costs ($0.45–$0.59) and iteration counts confirm independence.
- **Endpoint SD gap**: The `obs-sio-measured-value` task revealed that the SHACL shape advertised `sosa:hasSimpleResult` as required, but the test data uses the SIO measurement chain. Fixed in Phase 5 by adding `sio:has-attribute` to the ObservationShape + SIO-specific SPARQL examples + cross-graph agent instruction hints.
- **Phase 4b correction**: Initial analysis claimed 6/6 tool adoption per run. Detailed trace analysis across 8 ensemble runs revealed the actual rate was 2/6 — selective to schema introspection tasks (`sio-attribute-inverse`: 7/8 runs, `sio-measured-value-range`: 8/8 runs) with zero calls on data tasks. The corrected finding strengthens the interpretation: the tool is adopted where it has unique value (schema-only tasks), not reflexively.

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

# Inspect the self-description
curl -s http://localhost:8080/.well-known/void | head -20
```

### Install Python dependencies

```bash
# Install the project and all dependencies (includes dspy fork)
uv pip install -e ".[test]"
```

### Run the test suite

```bash
# Unit + integration tests (no Docker required for unit tests)
pytest tests/ -v

# Hurl HTTP conformance tests (requires running fabric stack)
cd tests && make test-hurl-p1    # Phase 1: self-description + SPARQL
cd tests && make test-hurl-p2    # Phase 2: DID resolution, VCs, LDN, content integrity
```

### Run an experiment

```bash
# Phase 3b: SIO tasks with TBox path hints
python experiments/fabric_navigation/run_experiment.py \
    --tasks experiments/fabric_navigation/tasks/phase3-sio-tbox.json \
    --phase phase3b-tbox-paths \
    --output experiments/fabric_navigation/results/ \
    --model anthropic/claude-sonnet-4-6 \
    --verbose

# Ensemble replication (4 runs, temperature=0.7 to defeat prompt caching)
for i in 1 2 3 4; do
    python experiments/fabric_navigation/run_experiment.py \
        --tasks experiments/fabric_navigation/tasks/phase3-sio-tbox.json \
        --phase phase4b-rdfs-routes \
        --output experiments/fabric-navigation/results/ \
        --model anthropic/claude-sonnet-4-6 \
        --temperature 0.7 --no-cache
done
```

## Exploring with Claude Code

This repo is designed to be explored and developed with [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Claude Code serves as the research assistant — running experiments, building infrastructure test-first, and managing code.

```bash
# Launch Claude Code in this repo
claude

# Or with the Obsidian vault for full research context (owner only)
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ~/Obsidian/obsidian
```

### What Claude Code has access to

- **CLAUDE.md** — project context, architecture decisions (D1–D26), key commands
- **`.claude/rules/`** — decisions index (always loaded), Python patterns, coding conventions
- **`.claude/skills/`** — workflow skills (`/fabric-discover`, `/fabric-test`, `/fabric-status`)

### Development methodology

Infrastructure is built test-first using two testing layers:

**Hurl tests** (`tests/hurl/phase1/`) — HTTP-level conformance tests for the fabric node. Each test file corresponds to a TDD cycle (numbered `01`–`12`), written RED before the feature exists and turned GREEN by implementation. These verify that `.well-known/` endpoints serve correct content, SPARQL queries return expected results, and TBox named graphs are loaded at startup.

```bash
# Run all Phase 1 conformance tests
cd tests && make test-hurl-p1
```

**pytest** (`tests/pytest/`) — unit tests for agent tooling (`fabric_discovery`, `fabric_rdfs_routes`, `fabric_validate`, trajectory logging) and integration tests that exercise the full agent→gateway→Oxigraph pipeline.

```bash
# 127 unit tests currently passing
pytest tests/ -v
```

## Repo structure

```
fabric/
  node/                FastAPI gateway + self-description + DID resolution
  credo/               Credo-TS sidecar (DID/VC identity layer)
agents/              DSPy/RLM agent implementations
  fabric_discovery.py   Four-layer endpoint discovery (D9)
  fabric_agent.py       FabricQuery signature + result types
  fabric_query.py       SPARQL query tool for RLM REPL
  fabric_rdfs_routes.py RDFS/OWL routing analysis tool
  fabric_validate.py    SHACL validation tool
ontology/            TBox cache: SOSA, SIO, OWL-Time, PROV-O, Fabric
shapes/              SHACL shapes (endpoint-specific constraints)
sparql/              SPARQL examples catalog (SIB spex: pattern)
experiments/
  fabric_navigation/    Experiment runner, eval harness, task definitions
    tasks/              Task JSON files (baseline, phase2, phase3-sio)
    results/            JSON result files per phase+timestamp
    trajectories/       JSONL trajectory logs per task-run
scripts/             CLI tools (sparql_query, shacl_validate)
credentials/         Mock VCs (Phase 1)
provenance/          SPDX SBOM + PROV-O activity records
tests/
  hurl/phase1/       HTTP conformance tests (13 Hurl files)
  hurl/phase2/       Identity + trust integration tests (18 Hurl files)
  pytest/unit/       Agent tooling + identity unit tests (127 tests)
  pytest/integration/ Full-stack integration tests
.claude/
  rules/             Decisions index, Python patterns, coding style
```

## Key decisions

Architectural decisions are tracked in `.claude/rules/decisions-index.md` (D1–D26). The most relevant:

| # | Decision | Why it matters |
|---|---------|----------------|
| D3 | Credo-TS + did:webvh for identity | Decentralized node identity with verifiable history; no central authority |
| D4 | Oxigraph Server (SPARQL 1.2) | Named graph support for TBox ontologies + observation data separation |
| D5 | did:webvh + digestMultibase content integrity | Cryptographic binding between node identity and artifact content |
| D7 | PROF + VoID + SHACL + SPARQL examples at `.well-known/` | The self-description stack that agents actually read |
| D9 | Four-layer KR: SD → TBox → shapes → examples | The core architectural claim — progressive disclosure of endpoint knowledge |
| D12 | Bootstrap admission via FabricConformanceCredential | Self-issued VC attesting profile conformance + service directory |
| D20 | SDL instrument station use case | Phase 1 motivating scenario: electrochemical observation data with SOSA + SIO |
| D22 | Fabric ontology at `https://w3id.org/cogitarelink/fabric` | OWL 2 DL vocabulary for fabric concepts (nodes, roles, profiles) |
| D25 | Linked Data Notifications for actor-to-actor messaging | W3C LDN replaces custom endpoints; every DID advertises an inbox |
| D26 | Content integrity via relatedResource + digestMultibase | SHA-256 hashes in conformance VC bind artifacts to credential issuance time |

## Identity

**Owner**: Charles F. Vardeman II
**ORCID**: https://orcid.org/0000-0003-4091-6059
**Institution**: University of Notre Dame (https://ror.org/00mkhxb43)
**Lab**: Laboratory for Assured AI Applications Development (LA3D)
**License**: Apache-2.0
