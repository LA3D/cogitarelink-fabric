# node-rlm Fabric Experiment — Design

**Goal**: Run the existing SIO navigation tasks against the fabric using node-rlm's JS RLM engine, comparing agent behavior across tool conditions (baseline Comunica, +jsonld, +LTQP, combined).

**Motivation**: The Python DSPy agent uses raw httpx for SPARQL. The JS agent gets Comunica (tested SPARQL engine with federation and link traversal) and jsonld.js (W3C reference JSON-LD processor). The question is whether these capabilities produce measurably different fabric navigation behavior.

**Prerequisite**: Phase 2.5a JSON-LD content negotiation infrastructure (completed 2026-03-06).

---

## Architecture: Hybrid (Option C)

The experiment lives in `cogitarelink-fabric/experiments/node-rlm-fabric/` and imports node-rlm's `runEval` harness for concurrency, resumability, incremental saves, and observer events. No modifications to node-rlm itself.

```
experiments/node-rlm-fabric/
├── package.json              # node-rlm (github:), @comunica/query-sparql,
│                             # @comunica/query-sparql-link-traversal, jsonld
├── tsconfig.json
├── run-experiment.ts         # CLI entry: loads tasks, creates driver, calls runEval()
├── sandbox-tools.ts          # fabric tools injected as sandboxGlobals
├── sandbox-jsonld.ts         # jsonld.js + fabric document loader (js-jsonld condition)
├── sandbox-comunica.ts       # Comunica engine factory + LTQP tools (js-ltqp condition)
├── setup-teardown.ts         # SPARQL INSERT/DROP via Comunica (test data lifecycle)
├── scoring.ts                # substring_match_scorer
├── tasks/
│   └── phase1-sio-baseline.json   # 6 SIO tasks (same as Python phase3)
├── results/                  # auto-saved by runEval (gitignored)
└── README.md
```

### Why Option C (hybrid)

Reusing node-rlm's `runEval` provides:
- **Resumability** — partial results survive crashes; resumes from matching config
- **Concurrency control** — Promise pool with configurable parallelism
- **Pass@N** — multiple attempts per task, keeps best score
- **Incremental saves** — crash-safe after every task
- **Observer events** — typed events at every depth (delegation tree, sandbox snapshots, timing)
- **Cost tracking** — built into wrappedCallLLM, aggregated automatically

### node-rlm Dependency

Referenced via git in package.json: `"node-rlm": "github:openprose/node-rlm"`. No local clone required to run experiments. Portable across machines.

---

## Anthropic Driver

No custom driver. node-rlm's `fromOpenRouterCompatible` supports any OpenAI-compatible API:

```typescript
import { fromOpenRouterCompatible } from "node-rlm/drivers/openrouter-compatible";

const callLLM = fromOpenRouterCompatible({
  baseUrl: "https://api.anthropic.com/v1",
  apiKey: process.env.ANTHROPIC_API_KEY!,
  model: "claude-sonnet-4-6-20250514",
});
```

API key from environment (`ANTHROPIC_API_KEY`), same as Python experiments.

---

## Sandbox Tools

**Design principle**: Use Comunica for all SPARQL interaction. Only use raw `fetch()` for non-SPARQL HTTP endpoints. Minimize custom code.

### Dependency stack

| Package | Role |
|---|---|
| `@comunica/query-sparql` | All SPARQL (SELECT, CONSTRUCT, INSERT DATA, DROP GRAPH) |
| `@comunica/query-sparql-link-traversal` | LTQP condition only |
| `jsonld` | JSON-LD condition only |
| `node-rlm` | Harness + RLM engine |

### Agent-visible tools (injected via sandboxGlobals)

**Baseline (all conditions)**:
- `comunica_query(query, sources)` — SPARQL SELECT/CONSTRUCT against fabric endpoint(s)
- `fetchVoID(endpoint)` — GET `/.well-known/void`
- `fetchShapes(endpoint)` — GET `/.well-known/shacl`
- `fetchExamples(endpoint)` — GET `/.well-known/sparql-examples`
- `fetchEntity(endpoint, entityId)` — GET `/entity/{entityId}`

**js-jsonld condition adds**:
- `jsonld.expand`, `jsonld.compact`, `jsonld.frame`, `jsonld.fromRDF`, `jsonld.toRDF`
- Fabric document loader (VoID-bootstrapped, redirects vocab URIs to `/ontology/{vocab}`)

**js-ltqp condition adds**:
- `comunica_traverse(query, seedUrls)` — Comunica LTQP, follows links during query execution

### Harness-only tools (not agent-visible)

Setup/teardown uses Comunica for SPARQL UPDATE (`INSERT DATA`, `DROP SILENT GRAPH`). Same lifecycle as Python `setup_task_data`/`teardown_task_data`.

### globalDocs

Documents available tools for the agent (equivalent to Python `_RDFS_TOOL_HINT`). Condition-specific — only documents tools actually available in that condition.

---

## Experiment Conditions

CLI: `--condition <name>` controls which sandbox tools are injected.

| Condition | Sandbox globals | What it tests |
|---|---|---|
| `js-baseline` | comunica_query + discovery fetch tools | Comunica SPARQL vs Python httpx |
| `js-jsonld` | baseline + jsonld processing | JSON-LD framing/compaction on results |
| `js-ltqp` | baseline + comunica_traverse | Automated link traversal (Path B) |
| `js-combined` | all | Agent tool selection when all available |

---

## TLS and Authentication

**TLS**: `NODE_EXTRA_CA_CERTS=./caddy-root.crt` trusts the fabric's Caddy CA for all Node.js HTTPS calls (Comunica internal fetches + discovery fetch). Same pattern as Python `SSL_CERT_FILE`.

**VP Auth**: `POST /test/create-vp` at experiment start, token threaded into Comunica's HTTP headers. Discovery fetch calls are unauthenticated (`.well-known/*` routes are public).

---

## Tasks and Scoring

### Task format

Same JSON schema as Python experiments: `{id, query, context, expected, metadata}`.

`context` field: the full VoID/SD string fetched at experiment start (not just the URL). node-rlm passes this to the agent as `__ctx.shared.data`.

### Scoring

Case-insensitive substring match (identical to Python):

```typescript
function substringMatch(predicted: string, expected: string | string[]): number {
  const lower = predicted.toLowerCase();
  const targets = Array.isArray(expected) ? expected : [expected];
  return targets.some(e => lower.includes(e.toLowerCase())) ? 1.0 : 0.0;
}
```

### Task set

Phase 1 uses the 6 SIO tasks from Python phase3 — the discriminator tasks where vocabulary is outside LLM pretraining (+0.167 lift with TBox paths in Python).

---

## CLI Interface

```bash
NODE_EXTRA_CA_CERTS=./caddy-root.crt \
npx tsx experiments/node-rlm-fabric/run-experiment.ts \
  --tasks experiments/node-rlm-fabric/tasks/phase1-sio-baseline.json \
  --condition js-baseline \
  --model anthropic/claude-sonnet-4-6-20250514 \
  --max-iterations 10 \
  --concurrency 1
```

Concurrency defaults to 1 — tasks share the fabric endpoint and do INSERT/DROP per task. Parallel execution would cause data conflicts.

---

## Measures and Success Criteria

### Primary measures (cross-comparable with Python)

- Score (substring match, 0.0 or 1.0 per task)
- Iterations to answer
- Wall time
- Cost estimate (input/output chars)

### New measures (from node-rlm observer)

- Delegation tree (if agent uses `rlm()` for sub-queries)
- Per-iteration sandbox snapshots
- Tool call sequence and ordering

### Cross-platform comparisons

| Comparison | Question |
|---|---|
| Python phase3b vs JS-baseline | Does JS RLM + Comunica match Python RLM + httpx? |
| JS-baseline vs JS-jsonld | Does JSON-LD processing change agent behavior? |
| JS-baseline vs JS-ltqp | Does automated link traversal help on fabric tasks? |
| JS-combined tool selection | Which tools does the agent choose when all available? |

### Phase 1 success criteria

- JS-baseline matches Python phase3b score (6/6 on SIO tasks)
- If it doesn't, diagnose sandbox/tooling issues before expanding conditions
- Results directly comparable to Python experiment output format

Phase 1 is intentionally narrow: 6 SIO tasks, one condition (js-baseline), one model (Sonnet). Validate the harness against known Python results before expanding.

---

## Relationship to Existing Plans

This design refines Phase 0 and Phase 1 of `KF-NodeRLM-Experiment-PLAN.md`. Key changes from the broad plan:

- **Option C (hybrid)** instead of standalone runner — reuses node-rlm's `runEval`
- **Comunica for all SPARQL** instead of raw fetch baseline — no reinventing tested functionality
- **Git dependency** instead of local file reference — portable across machines
- **Phase 0.3 infrastructure already complete** — Phase 2.5a delivered all five work units
