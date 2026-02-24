# cogitarelink-fabric

Federated knowledge fabric prototype: RLM agents navigating self-describing SPARQL
endpoints with DID/VC identity and nanopublication-compatible provenance.

**Vault**: `~/Obsidian/obsidian` — launch with `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`

## Architecture

Three-container fabric node: FastAPI gateway + Oxigraph SPARQL + Credo-TS sidecar.
Agents connect externally via HTTP; fabric does not host agents.
Agent substrate lives in `~/dev/git/LA3D/agents/rlm` (Stage 6 adds fabric tools).

See @.claude/rules/decisions-index.md for architectural decisions (D1-D25).
See @.claude/memory/MEMORY.md for experiment state, key patterns, and findings.
See @~/Obsidian/obsidian/01 - Projects/Knowledge Fabric Prototyping/KF-Prototype-PLAN.md

## Key Commands

```bash
docker compose up -d                         # start fabric stack
docker compose logs -f fabric-node           # tail node logs
curl http://localhost:8080/.well-known/void  # inspect SD
pytest tests/ -v                             # run test suite
python scripts/sparql_query.py <query>       # SPARQL against local node
```

## Repo Structure

```
fabric/          — Docker Compose + per-node config (FastAPI, Oxigraph, Credo)
agents/          — DSPy/RLM agent implementations
ontology/        — TBox cache: SOSA, OWL-Time, QUDT, PROV-O (named graph content)
shapes/          — SHACL shapes: standard (sosa-v1) + endpoint-specific
sparql/          — SPARQL examples (spex: pattern, SIB convention)
scripts/         — Python CLI tools (sparql_query, shacl_validate, prov_record)
credentials/     — Mock VCs (claude-code-agent-vc.json)
provenance/      — SPDX SBOM + PROV-O activity records
tests/           — conformance + integration tests
```

## Git Protocol

Prefix: `[Agent: Claude]`
Co-Author: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
Never force push. Stage specific files.

## Identity

ORCID: https://orcid.org/0000-0003-4091-6059
Notre Dame ROR: https://ror.org/00mkhxb43
CI-Compass ROR: https://ror.org/001zwgm84
