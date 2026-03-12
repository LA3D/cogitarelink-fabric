# Governance model: construction and operational agents

*This essay is part of the [cogitarelink-fabric](../README.md) project documentation.*

**Summary.** This repository has two kinds of agents — construction agents (Claude Code) that build the infrastructure, and operational agents (RLM programs) that navigate it — and both face the same structural governance problem: specification → validation → identity → provenance → human accountability. This document describes the unified governance model, the structurally parallel mechanisms, and the skills framework that enforces process governance on the construction side.

---

## Two kinds of agents, one governance problem

This repository has two kinds of agents, and both face the same structural problem.

**Construction agents** — software engineering agents like Claude Code — build the infrastructure. They write the FastAPI routes, the SHACL shapes, the SPARQL proxy, the DID resolution endpoints. They operate in a code repository, producing git commits.

**Operational agents** — RLM programs like the IngestCurator and Q&A agents — operate within the infrastructure once built. They navigate SPARQL endpoints, write observation data, resolve entity identifiers. They operate in a knowledge fabric, producing triples.

The insight is that both need the same kinds of governance. An operational agent writing triples to `/graph/observations` needs: a specification to conform to (SHACL shapes), validation before its writes are accepted (`commit_graph` gate), credentials identifying who authorized it (AgentAuthorizationCredential), and provenance recording what it did (PROV-O). A construction agent writing code to `fabric/node/main.py` needs the same things: a specification to conform to (W3C standards), validation before its implementation is accepted (test suite), identification of who it is and who authorized it (agent DID, SPDX SBOM), and provenance recording what it built (git commits with `[Agent: Claude]` prefix).

Without governance, construction agents produce the same interoperability failure that ungoverned operational agents would produce: systems that work internally but can't talk to anything else. The difference is that the failure manifests at a different layer. An ungoverned operational agent writes malformed triples that violate SHACL shapes. An ungoverned construction agent writes a custom query API that violates the SPARQL protocol. Both produce artifacts that are internally consistent but externally incompatible.

The governance mechanisms are structurally parallel:

| Need | Operational agent | Construction agent |
|---|---|---|
| **Specification** | SHACL shapes declare required properties | W3C specs declare required protocol behavior |
| **Validation** | `commit_graph` runs SHACL before accepting triples | Test suite runs HURL/pytest before accepting code |
| **Identity** | Agent DID + AgentAuthorizationCredential | Agent DID + SPDX SBOM + `[Agent: Claude]` commits |
| **Authorization** | Delegation VC from human researcher | Skills framework enforces brainstorming → plan → approval pipeline |
| **Provenance** | PROV-O `prov:wasAssociatedWith` on every write | Git history + PROV-O activity records + EARL conformance reports |
| **Process governance** | SHACL shapes constrain what data can enter | [Superpowers](https://github.com/obra/superpowers) skills constrain how code is written (TDD, code review, verification) |
| **Trust gaps** | `fabric:PendingTask` surfaces to human inbox via LDN | Failing tests, code review findings surface to human developer |

The last row is key. Both systems implement human-in-the-loop as a structural property, not an afterthought. The operational agent's trust gaps — missing credentials, ambiguous entity deduplication, shape version conflicts — surface to the responsible researcher's LDN inbox. The construction agent's trust gaps — design decisions, implementation tradeoffs, conformance claims — surface through the skills framework's hard gates: brainstorming requires design approval before code, TDD requires failing tests before implementation, code review requires passing spec compliance before merge. In both cases, the human remains in the responsibility chain not by monitoring every action, but by structuring the process so that the right decisions require human judgment and the routine execution can proceed autonomously.

This symmetry is not accidental. Research cyberinfrastructure that is agentically constructed and agentically operated needs a unified governance model. The construction agent that builds a SPARQL endpoint to spec, tests it against W3C conformance suites, and records its work as EARL results linked to PROV-O provenance is doing the same thing — structurally — as the operational agent that writes observation triples to spec, validates them against SHACL shapes, and records its work as PROV-O activities linked to delegation credentials. The standards are different (W3C test suites vs. SHACL shapes), the artifacts are different (code vs. triples), but the governance pattern is the same: specification → validation → identity → provenance → human accountability.

The argument this repository makes by example: agentic software engineering tools will make research software cheap to build. The remaining hard problem is ensuring that what gets built remains interoperable — across institutions, across domains, across time. Standards provide the shared contracts. SHACL shapes provide the data governance. Skills frameworks provide the process governance. Tests provide the verification. And FAIR principles provide the institutional framework for deciding which standards to adopt, which shapes to require, and which tests to mandate. Without that governance layer — for both the construction agents and the operational agents — the ease of building becomes the ease of building silos.

## Development methodology: skills as process governance

The fabric uses SHACL shapes to govern data writes. It uses PROF profiles to govern node conformance. And it uses [Superpowers](https://github.com/obra/superpowers) — an agentic skills framework — to govern the development process itself.

Superpowers provides composable skills that auto-trigger based on context: brainstorming, planning, test-driven development, code review, and verification. Each skill enforces hard gates — constraints that cannot be bypassed without explicit human override. The skills don't suggest a workflow; they enforce one. The parallel to SHACL is deliberate: just as a `fabric:ObservationShape` prevents malformed data from entering `/graph/observations`, the TDD skill prevents production code from being written without a failing test, and the verification skill prevents success claims without fresh evidence.

The enforced pipeline:

```
Brainstorming (design)
    ↓ HARD GATE: no code until design approved
Writing Plans (implementation plan)
    ↓ tasks decomposed to 2-5 minute granularity
Test-Driven Development (RED → GREEN → REFACTOR)
    ↓ IRON LAW: no production code without failing test first
Code Review (spec compliance, then code quality)
    ↓ critical issues block progress
Verification Before Completion
    ↓ IRON LAW: no success claims without fresh evidence
Branch Completion (merge/PR/discard with test verification)
```

Each stage has an explicit hard gate:

| Skill | Hard gate | Fabric analogy |
|---|---|---|
| **Brainstorming** | No code until design approved | PROF profile declares what a node must provide before admission |
| **Writing Plans** | Each task = one action with exact file paths and verification steps | SHACL shapes declare required properties with cardinalities |
| **TDD** | No production code without a failing test first | `commit_graph` rejects writes that fail SHACL validation |
| **Verification** | No completion claims without fresh evidence | D26 `digestMultibase` — claims backed by verifiable hashes |
| **Code Review** | Critical issues block merge | D24 trust gaps surface `fabric:PendingTask` instead of silent acceptance |

This matters for research reproducibility. When Claude Code builds a SPARQL endpoint, the brainstorming skill forces explicit design decisions before implementation. Those decisions are recorded in the project's decision log (D1–D30 in the Obsidian vault). The writing-plans skill decomposes the design into tasks small enough that each can be verified independently. The TDD skill forces each task to start with a test encoding a specific requirement — often a W3C spec requirement — before the implementation exists. The git history records the RED→GREEN transition for every feature: the test was written, it failed, the implementation was written, it passed.

That git history is the raw material for D28's conformance evidence chain. The `[Agent: Claude]` commit prefix identifies which commits were produced by the development agent. The HURL tests map to W3C spec section URIs. The test results become EARL (W3C Evaluation and Report Language) assertions stored in `/graph/conformance`. The EARL assertions link back to the agent's DID via PROV-O provenance. The result is a verifiable chain: spec requirement → test → implementation → test result → agent identity → git commit — queryable by SPARQL, bound to the conformance credential by `digestMultibase`, and auditable by anyone who wants to verify how the infrastructure was built.

## The vault as planning substrate

The Obsidian vault (`~/Obsidian/obsidian/`) provides the planning and decision-making substrate that the superpowers skills operate within. The vault holds:

- **`KF-Prototype-PLAN.md`** — phased implementation plan with prioritized tasks (P0/P1/P2), timelines, and success criteria. This is what the writing-plans skill references when decomposing work.
- **`KF-Prototype-Decisions.md`** — 30 architectural decisions (D1–D30) with context, alternatives considered, and implications. When the brainstorming skill forces design exploration before coding, the decisions log captures what was decided and why.
- **Daily notes** — chronological work log linking concepts, implementations, and papers. Provides the "why was this decision made on this day" context that git commits alone don't capture.

The vault is not documentation written after the fact. It is the active planning environment that the agent works within. When a brainstorming session produces a new decision (e.g., D27: SHACL-gated vocabulary admission), the decision is written to the vault, tasks are added to the plan, and only then does the implementation pipeline begin. The vault provides the strategic context; the skills enforce the tactical execution; the tests verify the result.
