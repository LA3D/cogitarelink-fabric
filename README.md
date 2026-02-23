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
- **Credo-TS sidecar** — DID/VC identity layer (did:webvh + W3C VC 2.0) for future trust and provenance work

### D9: Four-layer knowledge representation

The core architectural claim. Each fabric node exposes four layers of structured metadata, each serving a distinct navigation purpose:

| Layer | Standard | Endpoint | What it tells the agent |
|---|---|---|---|
| **L1** Service Description | VoID + PROF | `/.well-known/void`, `/.well-known/profile` | What vocabularies exist, what named graphs are available, what profile this node conforms to |
| **L2** TBox Ontologies | OWL/RDFS | `/ontology/{vocab}` named graphs | Class hierarchies, property domains/ranges, subclass relationships — the structural skeleton of each vocabulary |
| **L3** SHACL Shapes | SHACL 1.2 | `/.well-known/shacl` | Data constraints, expected property paths, `sh:agentInstruction` with concrete query templates |
| **L4** Query Examples | spex: (SIB pattern) | `/.well-known/sparql-examples` | Working SPARQL queries demonstrating common access patterns |

The agent reads L1 first (compact, orients), then drills into L2-L4 as needed. The `discover_endpoint()` function in `agents/fabric_discovery.py` loads all four layers into a `FabricEndpoint` object, which produces a `routing_plan` text that the RLM agent reads as its initial context.

### Agent substrate

Agents are [DSPy](https://github.com/stanfordnlp/dspy) RLM programs (Recursive Language Models). An RLM operates a Python REPL loop: the LLM writes code, executes it, reads the output, writes more code — iterating until it can produce an answer. Fabric tools (`sparql_query`, `analyze_rdfs_routes`) are injected into the REPL namespace so the agent can call them from generated code.

The agent substrate is separate from the fabric infrastructure. Agents connect externally via HTTP; the fabric node does not host agents.

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
| **4b** RDFS routes tool | Add `analyze_rdfs_routes()` callable tool | 1.000 | **100% tool adoption** (24/24 task-runs across 4 ensemble replications); tool called adaptively after initial SPARQL failure, not reflexively |

**Phase 3 is the central result**: for vocabularies outside pretraining, TBox path hints in the routing plan provide a measurable score lift. The structured metadata isn't just nice to have — it's necessary for correct query construction when the LLM can't fall back on memorized patterns.

**Phase 4 adds a second modality**: the TBox isn't only useful as static text in the routing plan — it can also be wrapped as a callable sub-agent tool (`analyze_rdfs_routes`) that performs RDFS/OWL routing analysis on demand. The tool is adopted when advertised in the agent's initial context (`endpoint_sd`) and used adaptively — called after an initial SPARQL attempt returns empty, providing semantic grounding (property direction, correct graph) rather than the answer itself.

### Methodological notes

- **Domain contamination audit**: The RDFS instructional patterns were originally copied with SOSA-specific examples. When run against SOSA endpoints, this leaked domain knowledge into the sub-agent prompt — a confound. All examples were replaced with fully abstract vocabulary (`:ClassX`, `:propA`). Clean reruns confirmed identical results, establishing that the tool works from ontology structure, not from domain-specific examples in the prompt.
- **Prompt caching trap**: Initial ensemble replications at `temperature=None` produced identical traces — Anthropic's server-side prompt caching was returning cached responses. Fixed by running at `temperature=0.7` with `cache=False`. Varying costs ($0.45–$0.59) and iteration counts confirm independence.
- **Endpoint SD gap**: The `obs-sio-measured-value` task revealed that the SHACL shape advertised `sosa:hasSimpleResult` as required, but the test data uses the SIO measurement chain. Agents succeeded via raw triple exploration (resilient) but this was an SD design issue, now fixed.

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
uv pip install -r requirements.txt
# Or install the dspy fork directly:
uv pip install "git+https://github.com/rawwerks/dspy.git@feat/rlm-media-types-protocol"
```

### Run the test suite

```bash
# Unit + integration tests (no Docker required for unit tests)
pytest tests/ -v

# Hurl HTTP conformance tests (requires running fabric stack)
cd tests && make test-hurl-p1
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

- **CLAUDE.md** — project context, architecture decisions (D1–D22), key commands
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
# 81 tests currently passing
pytest tests/ -v
```

## Repo structure

```
fabric/              Docker Compose + FastAPI gateway + node config
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
  hurl/phase1/       HTTP conformance tests (12 Hurl files)
  pytest/unit/       Agent tooling unit tests
  pytest/integration/ Full-stack integration tests
.claude/
  rules/             Decisions index, Python patterns, coding style
```

## Key decisions

Architectural decisions are tracked in `.claude/rules/decisions-index.md` (D1–D22). The most relevant:

| # | Decision | Why it matters |
|---|---------|----------------|
| D4 | Oxigraph Server (SPARQL 1.2) | Named graph support for TBox ontologies + observation data separation |
| D7 | PROF + VoID + SHACL + SPARQL examples at `.well-known/` | The self-description stack that agents actually read |
| D9 | Four-layer KR: SD → TBox → shapes → examples | The core architectural claim — progressive disclosure of endpoint knowledge |
| D20 | SDL instrument station use case | Phase 1 motivating scenario: electrochemical observation data with SOSA + SIO |
| D22 | Fabric ontology at `https://w3id.org/cogitarelink/fabric` | OWL 2 DL vocabulary for fabric concepts (nodes, roles, profiles) |

## Identity

**Owner**: Charles F. Vardeman II
**ORCID**: https://orcid.org/0000-0003-4091-6059
**Institution**: University of Notre Dame (https://ror.org/00mkhxb43)
**Lab**: Laboratory for Assured AI Applications Development (LA3D)
**License**: Apache-2.0
