# README Restructure Design

**Date**: 2026-03-12
**Status**: Approved
**Goal**: Restructure the 554-line README into a ~250-line narrative README with six companion docs in `docs/`.

## Problem

The current README is essentially a research paper. It contains strong argumentative writing but:
1. At 554 lines, most readers will not finish it
2. It doesn't frame the project in the data mesh / agentic mesh / knowledge fabric genealogy
3. It doesn't describe the meta-experiment: a human researcher provides W3C specs, a software engineering agent (Claude Code) implements them TDD-style, and the human curates specifications rather than writing code
4. It doesn't describe the inner experiment loop: operational agents navigate the fabric, their performance reveals what the fabric needs, the fabric evolves
5. The deep essays (FAIR history, research integrity, identifier persistence, credential architecture, trace analysis) are paper material living in a README

## Approach: Narrative README + companion docs

The README tells a story in three acts (mesh genealogy, two-level experiment, architecture + results). Current essays move to `docs/` as standalone pieces that can later become paper sections.

## README Structure (~230 lines)

### Section 1: Title + badges + one-liner (~5 lines)

Keep CodeMeta and WIP badges. Replace the one-liner:

> A research prototype exploring what happens when you build the knowledge substrate that agentic meshes assume exists — using W3C standards, FAIR principles, and decentralized identity — and then test whether LLM agents can actually navigate it.

### Section 2: "From data mesh to knowledge fabric" (~30 lines)

New section. The intellectual genealogy in three moves:

**Move 1 — The mesh lineage.** Service meshes solved microservice communication. Data meshes (Dehghani 2019) solved organizational data ownership with four principles: domain-oriented ownership, data as a product, self-serve infrastructure, federated computational governance. Agentic meshes extend the same pattern to autonomous agent ecosystems — agents need to be discoverable, observable, governable, and trustworthy at scale.

**Move 2 — The missing layer.** The agentic mesh describes the operational infrastructure — how agents find each other, collaborate, and are governed. But it assumes a knowledge substrate exists beneath it: self-describing data sources that agents can actually discover, query, and curate. Without that substrate, agents in the mesh have nothing meaningful to operate on. The mesh needs a fabric.

**Move 3 — The knowledge fabric as W3C realization.** This project builds that substrate using W3C standards. Each mesh concern maps to existing standards: registry → VoID + DCAT catalogs, trust framework → SHACL shapes + DID/VC credentials, patterns & protocols → SPARQL federation + LDN messaging, governance → federated computational governance via SHACL-gated writes. The contribution isn't inventing new standards — it's showing that the standards stack already provides what the agentic mesh needs.

Include a compressed mapping table (mesh component → W3C standard equivalent).

Cite Dehghani's data mesh paper/book. Reference the service mesh → data mesh → agentic mesh trajectory without citing Broda by name.

### Section 2.5: "Why a knowledge fabric" (~20 lines)

New section. The context engineering argument:

**The context engineering argument.** The dominant pattern for giving LLMs access to knowledge is RAG — embed everything, retrieve top-k chunks, stuff into prompt. This breaks at scale: (1) relevant information depends on schema relationships the agent hasn't discovered yet, (2) stuffing context forecloses navigation — following leads from one piece of information to the next, (3) no interoperability — every system has its own markdown, its own vector store, its own conventions.

**Progressive disclosure as context management.** A self-describing knowledge fabric inverts this. The agent starts with a compact service description and drills into ontology structure, shapes, and examples only as needed. Each layer adds precision without overwhelming the context window. The RLM REPL makes this practical — SPARQL results live in Python variables (unbounded), while the LLM sees only a size-capped view per iteration. The agent actively constructs its own context by navigating structured metadata. Knowledge graphs are useful for agents not because they store triples, but because their structure enables agents to manage their own attention.

**The scalability and interoperability argument.** Markdown files don't federate. Vector stores don't self-describe. An agent that learns to navigate one fabric node can navigate any conformant node. The same progressive disclosure pattern works across endpoints, across institutions, across vocabularies. Federation is iterative map-reduce: TBox map-reduce (once, cacheable) for routing, ABox map-reduce (per question, iterative) for data. Full treatment in `docs/architecture.md`.

### Section 3: "The two-level experiment" (~40 lines)

New section. The methodological contribution:

**The meta-experiment (construction agents).** This repository is itself an experiment in agentic software engineering. A human researcher provides W3C specifications and architectural decisions. A software engineering agent (Claude Code) implements them test-first — writing HURL conformance tests encoding specific spec requirements before the implementation exists, then writing code to make them pass. The human doesn't dictate code; they curate specifications and approve designs. The agent is constrained by a skills framework (Superpowers) that enforces brainstorming → planning → TDD → code review → verification gates. The git history records every RED→GREEN transition; `[Agent: Claude]` commit prefix makes agent-authored work auditable.

**The inner experiment (operational agents).** The infrastructure built by the construction agent becomes the test environment for operational agents — RLM programs that navigate the fabric's self-describing SPARQL endpoints. Experiments measure whether the four-layer KR stack (VoID → TBox → SHACL → SPARQL examples) provides sufficient scaffolding for agents to query unfamiliar knowledge graphs correctly. Each phase adds or removes a KR layer to isolate its contribution.

**The feedback loop.** Operational agents' performance reveals what the infrastructure needs. Phase 3: TBox path hints necessary for unfamiliar vocabularies. Phase 4: tool advertisement in service description required for adoption. Phase 7: catalog discovery changes agent behavior even when scores are unchanged. Each finding feeds back into the next infrastructure iteration — the construction agent implements the fix, the operational agents are re-tested. The two levels are a co-evolutionary loop.

**Governance symmetry.** Both levels face the same structural problem: specification → validation → identity → provenance → human accountability. Full treatment with comparison table in `docs/governance-model.md`.

### Section 4: "Architecture" (~40 lines)

Compressed from current ~120 lines.

**Container diagram** — three-container description (FastAPI + Oxigraph + Credo-TS). 3 lines.

**D9 four-layer table** — keep exactly as-is. The L1→L2→L3→L4 table is the core architectural claim.

**Self-description as linked contracts** — compress to ~8 lines. Keep the ASCII diagram showing CoreProfile → VoID → dct:conformsTo → SHACL threading. Drop paragraph-length explanations of read/write/vocabulary contracts → `docs/architecture.md`.

**Agent substrate** — 3-4 sentences on RLM (REPL loop, variable space vs token space, tools injected into namespace). Drop full Zhang et al. exegesis → `docs/`.

**One-sentence pointers** to moved material:
- Identity, credentials, content integrity → `docs/architecture.md`
- Research integrity and responsibility chain → `docs/research-integrity.md`
- Identifier persistence → `docs/identifier-persistence.md`

### Section 5: "Experimental results" (~30 lines)

**Phase summary table** — keep all rows, shorten findings to fragments.

**Phase 3 headline** — 3-4 sentences: for unfamiliar vocabularies, TBox hints provide measurable lift.

**Key findings** — 2-3 sentences on selective tool adoption (Phase 4), implicit reasoning (Phase 5), score ceiling limitation.

**Pointer**: "Detailed trace analysis, protoknowledge theory connections, and methodological notes in `docs/experimental-results.md`."

Optionally include Phase 2.5b JS harness rows for the JSON-LD boundary finding.

### Section 6: "Getting started" (~40 lines)

Keep roughly as-is:
- Prerequisites (Docker, Python, uv, Hurl)
- Start the fabric stack (3-line code block)
- Install Python dependencies
- Run the test suite (pytest + HURL)
- Run an experiment (one example, drop ensemble loop)

### Section 7: "Repo structure" (~20 lines)

Keep the current tree diagram. Add `docs/` directory.

### Section 8: "Key decisions" (~15 lines)

Trim from 14 rows to 6-8 most important: D4 (Oxigraph), D7 (self-description stack), D9 (four-layer KR), D13 (VP-gated SPARQL), D22 (fabric ontology), D25 (LDN), D30 (HTTPS). Link to full decisions index.

### Section 9: "References + Identity" (~15 lines)

Keep as-is. Add Dehghani's data mesh book/paper to references.

## Disposition of current README sections not yet mapped

These sections from the current README need explicit handling:

**"What this is" + "The hypothesis" + "Key concepts" (lines 8-31):** Subsumed by Sections 2, 2.5, and 3. The hypothesis framing (infrastructure claim + agent claim) is captured by the two-level experiment section. The "key concepts" definitions (knowledge fabric, progressive disclosure) are captured by Section 2.5. Delete — do not move to docs.

**"The cyberinfrastructure problem" (lines 48-59):** The argument that agentic software engineering makes infrastructure cheap, shifting the bottleneck to interoperability. This is thematically part of Section 2 (mesh genealogy). Fold 2-3 sentences of this into Move 3 of Section 2 to motivate why standards matter. The rest is subsumed. Do not move to docs separately.

**"Exploring with Claude Code" + Superpowers pipeline + vault-as-planning (lines 397-461, ~65 lines):** Compress to ~5 lines in Section 3 (two-level experiment) — the construction agent paragraph already describes the skills framework gates. The detailed pipeline diagram, hard-gates table, and vault-as-planning discussion move to `docs/governance-model.md` alongside the "Two kinds of agents" essay. Update the governance-model.md source description below.

**"Test infrastructure" (lines 462-481):** Fold into Section 6 (Getting started) which already covers running the test suite. The HURL/pytest distinction is already there. Drop the "TDD cycle" narrative framing — that's covered in Section 3.

## Companion docs (`docs/`)

Six essays extracted from the current README, each standalone:

| File | Source sections | Approx lines |
|---|---|---|
| `docs/fair-and-agents.md` | "FAIR was always about agents" | ~50 |
| `docs/governance-model.md` | "Two kinds of agents, one governance problem" + Superpowers pipeline + vault-as-planning | ~100 |
| `docs/architecture.md` | Self-description contracts, identity/credentials/integrity, map-reduce, standards rationale | ~120 |
| `docs/experimental-results.md` | Trace analysis, protoknowledge, Allemang/Sequeda, methodology | ~100 |
| `docs/identifier-persistence.md` | Identifier rot, did:webvh persistence, SSSOM dedup | ~40 |
| `docs/research-integrity.md` | NSF policy, responsibility chain, credential architecture | ~60 |

Each doc:
- Starts with a one-paragraph summary
- Contains the full argumentative text from the current README (lightly edited for standalone readability)
- Links back to the README for context
- Is positioned as a future paper section

## What changes vs current README

**New content (must be written):**
- Section 2: mesh genealogy (~30 lines)
- Section 2.5: context engineering argument (~20 lines)
- Section 3: two-level experiment framing (~40 lines)

**Kept with compression:**
- Section 1: one-liner (rewritten)
- Section 4: architecture (compressed from ~120 to ~40 lines)
- Section 5: experimental results (compressed from ~130 to ~30 lines)
- Sections 6-9: getting started, repo structure, decisions, references (minor tightening)

**Moved to `docs/`:**
- FAIR was always about agents
- Two kinds of agents, one governance problem
- Identifier rot and the persistence problem
- Research integrity and the responsibility chain
- Self-description contracts (detailed), identity/credentials, map-reduce (detailed)
- Trace analysis, protoknowledge, methodology

## Implementation notes

- The `docs/` files should preserve the current README text with minimal editing — the writing is strong, it just doesn't belong in a README
- The codemeta.json description should be updated to match the new one-liner
- The "Exploring with Claude Code" section (Superpowers, vault-as-planning) compresses to ~5 lines in the README, with a pointer to `docs/governance-model.md` where the construction-agent governance detail lives
