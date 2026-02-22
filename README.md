# cogitarelink-fabric

Federated knowledge fabric prototype implementing RLM-native navigation of self-describing SPARQL endpoints with DID/VC identity and nanopublication-compatible provenance.

## Research Goals

1. Validate that SHACL + SPARQL examples as self-description gives RLM agents enough structure to construct correct queries without additional prompting
2. Measure scaffolding advantage: RLM with SHACL/SPARQL-example self-description vs baseline
3. Demonstrate DID/VC identity as agent-native trust layer
4. Produce reusable fabric node infrastructure for scientific cyberinfrastructure
5. Feed findings into agentic memory research publication

See [full plan](~/Obsidian/obsidian/01\ -\ Projects/Knowledge\ Fabric\ Prototyping/KF-Prototype-PLAN.md) in vault.

## Architecture

Three-container fabric node per endpoint:
- **FastAPI gateway** — `.well-known/` self-description, `/entity/` dereferenceability, `/sparql` proxy
- **Oxigraph** — SPARQL 1.2 HTTP server with named graph storage
- **Credo-TS sidecar** — DID/VC issuance (did:webvh + W3C VC 2.0)

Agent substrate lives in `~/dev/git/LA3D/agents/rlm` (Stage 6 adds fabric navigation tools).

## Quick Start

```bash
# Launch with vault context (recommended)
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ~/Obsidian/obsidian

# Or add alias to ~/.bashrc.local:
alias kf='CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ~/Obsidian/obsidian'
```

```bash
# Start fabric stack (Week 1+)
docker compose up -d

# Check status
/fabric-status

# Discover endpoint capabilities
/fabric-discover http://localhost:8080

# Run conformance tests
/fabric-test
```

## Repo Structure

```
fabric/          Docker Compose + per-node config
agents/          DSPy/RLM agent implementations
ontology/        TBox cache (SOSA, OWL-Time, QUDT, PROV-O)
shapes/          SHACL shapes (standard + endpoint-specific)
sparql/          SPARQL examples (SIB spex: pattern)
scripts/         Python CLI tools
credentials/     Mock VCs (Phase 1)
provenance/      SPDX SBOM + PROV-O activity records
tests/           Conformance + integration tests
.claude/
  rules/         Path-scoped coding rules + decisions index
  skills/        Workflow skills (fabric-discover, fabric-test, etc.)
```

## Key Decisions

See `.claude/rules/decisions-index.md` (always loaded) or full log in vault.

| # | Decision |
|---|---------|
| D4 | Oxigraph Server (HTTP SPARQL 1.2) |
| D7 | PROF + VoID + SHACL + SPARQL examples at .well-known/ |
| D9 | Four-layer KR: SD → TBox → shapes → examples+SSSOM |
| D17 | Claude Code as DevelopmentAgent with SPDX/PROV-O provenance |
| D20 | SDL electrochemical instrument station (Phase 1 use case) |
| D21 | SSSOM as native vocabulary alignment (/graph/mappings) |

## Identity

**Owner**: Charles F. Vardeman II
**ORCID**: https://orcid.org/0000-0003-4091-6059
**Institution**: University of Notre Dame (https://ror.org/00mkhxb43)
**License**: Apache-2.0
