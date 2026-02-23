# TBox Lift Experiments Design

**Date**: 2026-02-23
**Phase**: Phase 2 — measuring L2 TBox impact on agent navigation
**Decisions**: D2 (RLM), D9 (four-layer KR), D20 (SDL use case)

## Problem

Phase 1.5 experiments (phases a–d) all saturated at 3 iterations / 2 SPARQL attempts / 1.0 score. The three baseline tasks are too simple — the agent copies an example query from the routing plan and submits in two steps regardless of what the routing plan contains. The tasks don't require TBox knowledge.

L2 TBox loading (Feb 2026) added 7 ontologies to Oxigraph and updated the routing plan to show `-> /ontology/{stem}` graph paths. This gives the agent two new capabilities:

1. **Ontology graph queries** — SPARQL against `GRAPH <.../ontology/sosa>` for schema facts
2. **Property discovery** — look up unfamiliar SOSA properties before querying instance data

Neither capability is exercised by the baseline tasks. New tasks are needed.

## Research Hypothesis

An agent whose routing plan reveals local ontology graph paths (`tbox-graph-paths` feature) will:

1. Correctly answer ontology-introspection questions that are unanswerable from instance data alone (sharp discriminators)
2. Navigate richer instance data more efficiently because it looks up unfamiliar property names in the ontology before constructing SPARQL (efficiency differentiators)

## Experiment Design

### Independent variable

`tbox-graph-paths` in the routing plan:
- **phase2a-no-tbox-paths**: routing plan shows `sosa: <http://www.w3.org/ns/sosa/>` (no graph path)
- **phase2b-tbox-paths**: routing plan shows `sosa: <http://www.w3.org/ns/sosa/> -> /ontology/sosa`

Ontology graphs are **present and queryable in both phases** via the existing `sparql_query` tool. The only difference is whether the routing plan signals their existence.

### Task set: `tasks/phase2-tbox-lift.json`

All six tasks run in both phases. Discriminators failing in phase2a is part of the measurement.

#### Sharp discriminators (3)

Answer exists only in the ontology graph — no instance data can provide it.

| id | query | expected substrings |
|---|---|---|
| `schema-property-type` | "Is sosa:hasSimpleResult a datatype or object property according to the SOSA ontology?" | `["DatatypeProperty"]` |
| `schema-used-procedure-range` | "What class does sosa:usedProcedure link an observation to, according to the SOSA ontology?" | `["Procedure"]` |
| `schema-phenomenon-time-exists` | "Does the SOSA ontology define a property for when the observed phenomenon occurred (distinct from when the result was recorded)?" | `["phenomenonTime"]` |

#### Efficiency differentiators (3)

Richer instance data using SOSA properties absent from current SHACL shape (`sosa:usedProcedure`, `sosa:hasFeatureOfInterest`, `sosa:phenomenonTime` — all in the loaded SOSA ontology, none in `endpoint-sosa.ttl` shape properties).

| id | extra triple | query | expected substrings |
|---|---|---|---|
| `obs-used-procedure` | `sosa:usedProcedure <.../procedure/electrochemical-scan>` | "What procedure was used to collect the observations?" | `["electrochemical-scan"]` |
| `obs-feature-of-interest` | `sosa:hasFeatureOfInterest <.../feature/sample-alpha>` | "What feature of interest was being observed?" | `["sample-alpha"]` |
| `obs-phenomenon-time` | `sosa:phenomenonTime "2026-02-22T11:30:00Z"` + `sosa:resultTime "2026-02-22T12:00:00Z"` | "When did the observed phenomenon actually occur (not when it was recorded)?" | `["11:30"]` |

### Phases

```python
"phase2a-no-tbox-paths": [
    "void-sd", "void-urispace", "void-graph-inventory",
    "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
    "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
],
"phase2b-tbox-paths": [
    "void-sd", "void-urispace", "void-graph-inventory",
    "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
    "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
    "tbox-graph-paths",
],
```

## Harness Changes

### `run_experiment.py`

1. **`_strip_tbox_paths(routing_plan: str) -> str`** — regex replaces `-> /ontology/\S+` with empty string on ontology cache lines; used by phase2a
2. **`kwarg_builder`** — checks `"tbox-graph-paths" in PHASE_FEATURES[phase]`; if absent, strips paths from `ep.routing_plan` before passing as `endpoint_sd`
3. **`_build_insert`** — extend to accept optional fields: `sosa:usedProcedure`, `sosa:hasFeatureOfInterest`, `sosa:phenomenonTime`

No new RLM tools. No changes to `dspy_eval_harness.py`. No changes to `FabricEndpoint` or `fabric_discovery.py`.

## Metrics

Same as Phase 1.5: score, iterations, converged, sparql_attempts, empty_recoveries, wall_time, cost.

**Primary lift metric**: `Δiterations = mean(phase2a efficiency tasks) − mean(phase2b efficiency tasks)`

**Expected outcomes**:

| Phase | Discriminators | Efficiency tasks |
|---|---|---|
| phase2a | score 0.0, hallucinate or iterate max | score 1.0, ≥ 2 extra iterations vs phase2b |
| phase2b | score 1.0, ≤ 4 iterations | score 1.0, fewer iterations |

Target: Δiterations ≥ 1.5 on efficiency tasks; all 3 discriminators score 0.0 in phase2a.

## File Summary

| File | Action |
|---|---|
| `experiments/fabric_navigation/tasks/phase2-tbox-lift.json` | New — 6 task definitions |
| `experiments/fabric_navigation/run_experiment.py` | Edit — two new phases, `_strip_tbox_paths`, `_build_insert` extension |
