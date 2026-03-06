# node-rlm Fabric Experiment

Run SIO navigation tasks against the cogitarelink fabric using node-rlm's JS RLM engine, comparing agent behavior across tool conditions.

## Prerequisites

- **node-rlm** cloned and built at `~/dev/git/LA3D/agents/node-rlm` (run `npm run build` there first)
- **Docker fabric stack** running at `https://bootstrap.cogitarelink.ai`
- **ANTHROPIC_API_KEY** in environment
- **caddy-root.crt** at repo root (exported from fabric Caddy CA)
- Node.js v20+

## Setup

```bash
cd experiments/node-rlm-fabric
npm install
```

## Run

```bash
NODE_EXTRA_CA_CERTS=../../caddy-root.crt \
npx tsx run-experiment.ts \
  --tasks tasks/phase1-sio-baseline.json \
  --condition js-baseline \
  --max-iterations 10
```

### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--tasks` | (required) | Path to task JSON file |
| `--condition` | `js-baseline` | Experiment condition |
| `--model` | `claude-sonnet-4-6-20250514` | Model identifier |
| `--max-iterations` | `10` | Max REPL iterations per task |
| `--endpoint` | `https://bootstrap.cogitarelink.ai` | Fabric endpoint URL |

### Conditions

| Condition | Tools | Phase |
|-----------|-------|-------|
| `js-baseline` | SPARQL query + discovery fetch | Phase 1 (current) |
| `js-jsonld` | baseline + jsonld.js processing | Phase 2 |
| `js-ltqp` | baseline + Comunica link traversal | Phase 2 |
| `js-combined` | all tools | Phase 2 |

## Tests

```bash
npm test
```

## Architecture

Uses `rlm()` directly from node-rlm (the eval harness is not exported). Each task runs sequentially with setup/teardown via SPARQL UPDATE (POST to `/sparql/update`). SPARQL queries use POST to `/sparql` with `application/sparql-results+json`. VP Bearer auth is acquired from `/test/create-vp` and threaded through all HTTP calls.

## Comparing with Python Results

```bash
# Python phase3b
cat ../fabric_navigation/results/phase3b-* | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Python: {d[\"aggregate\"][\"meanScore\"]}')"

# JS baseline
cat results/fabric-js-baseline* | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'JS: {d[\"aggregate\"][\"meanScore\"]}')"
```

## Design

See `docs/plans/2026-03-06-node-rlm-fabric-experiment-design.md` for the full design rationale.
