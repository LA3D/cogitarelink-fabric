# efficiency

kind: let

source:
```prose
let efficiency = session: navigator_analyst
  prompt: "Compare efficiency across conditions..."
```

---

## Summary Table

| Metric | js-baseline | js-jsonld | js-combined | Meaningful diff? |
|--------|-------------|-----------|-------------|-----------------|
| Mean score | **0.885** | **0.900** | 0.850 | Marginal: jsonld +0.015 over baseline; combined −0.035 |
| Mean iterations | 6.50 | 6.65 | 6.70 | No: <0.2 iter difference across all three |
| Mean SPARQL queries/task | **4.15** | **2.90** | 3.30 | Yes: jsonld saves 1.25 comunica calls/task (−30%) on schema tasks |
| Mean JSON-LD ops/task | 0.00 | fetchJsonLd: 1.10, jsonld.*: 0.40 | fetchJsonLd: 0.60, jsonld.*: 0.35 | Yes: shows adoption pattern |
| Mean tokens/task | **36,928** | 44,262 | 44,308 | Yes: jsonld/combined cost 20% more tokens per task |
| Mean wall time/task | **22.8s** | 28.4s | 26.5s | Yes: jsonld adds ~5.6s/task; combined adds ~3.7s |
| Est. cost/task (USD) | **$0.127** | $0.153 | $0.151 | Yes: 20-21% premium for JSON-LD conditions |

All three conditions used model `claude-sonnet-4-6`, endpoint `https://bootstrap.cogitarelink.ai`.
Run counts: js-baseline n=5 runs (26 task runs), js-jsonld n=4 runs (20 task runs), js-combined n=4 runs (20 task runs).

---

## Results by Task Category

### Existing SIO tasks (sio-has-value-type, sio-attribute-inverse, sio-measured-value-range, obs-sio-measured-value, obs-sio-unit, obs-sio-chemical-entity)

| Metric | js-baseline | js-jsonld | js-combined |
|--------|-------------|-----------|-------------|
| Mean score | 0.889 (n=18) | **0.917** (n=12) | **0.917** (n=12) |
| Mean iterations | 6.06 | 5.92 | 6.08 |
| Mean comunica/task | 3.28 | 2.58 | 2.92 |
| Mean fetchJsonLd/task | 0.00 | 0.50 | 0.25 |

The +0.028 score improvement in jsonld/combined on SIO tasks comes entirely from `sio-attribute-inverse` (0.67 baseline → 1.00 in both enhanced conditions). The agent uses `fetchJsonLd` on schema-only SIO tasks (`sio-has-value-type`, `sio-attribute-inverse`, `sio-measured-value-range`) and never on data-retrieval tasks (`obs-*`). Data tasks score 1.00 across all conditions.

### New vocabulary tasks (vocab-obs-to-sensor-properties, vocab-sio-datatype-property, vocab-sio-float-range-properties, vocab-sio-inverse-chain, vocab-observation-subclasses)

| Metric | js-baseline | js-jsonld | js-combined |
|--------|-------------|-----------|-------------|
| Mean score | 0.875 (n=8) | 0.875 (n=8) | 0.750 (n=8) |
| Mean iterations | 7.50 | 7.75 | 7.62 |
| Mean comunica/task | 6.12 | 3.38 | 3.88 |
| Mean fetchJsonLd/task | 0.00 | 2.00 | 1.12 |

The score improvement from JSON-LD access does not materialize for vocab tasks as a category. Both baseline and jsonld score 0.875; combined actually drops to 0.750. The hardest task, `vocab-sio-inverse-chain`, fails at 50% in all three conditions regardless of JSON-LD availability. When jsonld replaces high-SPARQL-iteration exploration (baseline: 6.12 comunica/task) with direct ontology fetching (jsonld: 3.38 comunica/task), it cuts SPARQL calls by 45% but does not improve accuracy on tasks that require multi-hop inference across ontology axioms.

---

## Per-Task Score Across Conditions

| Task | Category | js-baseline | js-jsonld | js-combined |
|------|----------|-------------|-----------|-------------|
| `obs-sio-chemical-entity` | data | 1.00 | 1.00 | 1.00 |
| `obs-sio-measured-value` | data | 1.00 | 1.00 | 1.00 |
| `obs-sio-unit` | data | 1.00 | 1.00 | 1.00 |
| `sio-has-value-type` | schema | 1.00 | 1.00 | 1.00 |
| `sio-attribute-inverse` | schema | 0.67 | **1.00** | **1.00** |
| `sio-measured-value-range` | schema | 0.67 | 0.50 | 0.50 |
| `vocab-obs-to-sensor-properties` | schema | 1.00 | 1.00 | 1.00 |
| `vocab-observation-subclasses` | schema | 1.00 | 1.00 | 1.00 |
| `vocab-sio-datatype-property` | schema | 1.00 | 1.00 | 1.00 |
| `vocab-sio-float-range-properties` | schema | 1.00 | 1.00 | 0.00 |
| `vocab-sio-inverse-chain` | schema | 0.50 | 0.50 | 0.50 |

Scores are mean across all runs of that condition. `n` per cell ranges from 1 (single-run tasks) to 3 (baseline SIO tasks).

---

## Efficiency Analysis

### The JSON-LD cost premium

JSON-LD conditions pay approximately 20% more in tokens and cost per task. This overhead is driven by the large payloads returned by `fetchJsonLd` on schema tasks — ontology documents can be tens of thousands of tokens. The most extreme example: `vocab-sio-float-range-properties` in js-jsonld (run 16-01-32) consumed 108,044 tokens across 14 iterations with 7 `fetchJsonLd` calls. A comparable baseline run completed in fewer iterations with fewer tokens.

The overhead is not uniformly distributed. Tasks where the agent doesn't use `fetchJsonLd` (all obs-* tasks, and some schema tasks) show no token premium.

### SPARQL query reduction

The clearest efficiency gain in jsonld/combined is the reduction in `comunica_query` calls for schema tasks: baseline averages 4.71 SPARQL queries per schema task, while jsonld averages 2.79 and combined 3.14. The agent substitutes direct ontology fetching for exploratory SPARQL iteration. Whether this is a net efficiency win depends on the relative cost of the JSON-LD payload vs multiple SPARQL round-trips. Given the 20% token premium, the substitution is roughly cost-neutral or slightly negative.

### Iteration count is stable

Mean iterations are virtually identical across all three conditions (6.50 vs 6.65 vs 6.70). JSON-LD access does not reduce the number of reasoning steps the agent takes — it changes the tools used within those steps but not the reasoning depth required.

### Wall time

js-jsonld is the slowest at 28.4s/task vs baseline's 22.8s. This is counterintuitive if `fetchJsonLd` replaces SPARQL queries, but makes sense when the agent uses both tools rather than substituting — it fetches the ontology document and then still runs SPARQL queries against it. js-combined at 26.5s is intermediate.

### The selectivity pattern holds in JavaScript

In Python phases 4-6, the `analyze_rdfs_routes` tool was used selectively on schema introspection tasks (2/6 per run) and never on data tasks. The JavaScript `fetchJsonLd` tool shows the same pattern with equal clarity: adoption rate is 0% for obs-* data tasks across all enhanced conditions, and 50-100% for schema tasks depending on the run. This suggests the selectivity is a property of the task structure (data tasks ground reasoning through SPARQL; schema tasks lack grounding data), not the tool interface.

---

## Failure Mode Analysis

Two tasks persistently fail across all conditions:

**`vocab-sio-inverse-chain` (50% failure rate, all conditions)**: The task requires reasoning about an inverse property chain in SIO. Failure persists even when the agent fetches the SIO ontology via `fetchJsonLd` and uses `jsonld.expand`. In the failing runs, the agent correctly identifies the relevant properties but extracts the wrong answer from the chain — suggesting the issue is answer extraction or chain direction disambiguation, not ontology access.

**`sio-measured-value-range` (33% baseline, 50% jsonld/combined)**: Counterintuitively, JSON-LD access does not help and may slightly hurt (0.67 baseline → 0.50 in enhanced conditions). In failing runs with jsonld, the agent uses `fetchJsonLd` then still fails to identify the correct rdfs:range target. The failure is in reasoning about the range relationship when multiple candidate classes exist, not in data access.

**`sio-attribute-inverse` (33% failure baseline → 0% with JSON-LD)**: The one clear win. JSON-LD access resolves this task by providing direct `owl:inverseOf` access from the ontology document, short-circuiting the exploratory SPARQL that sometimes failed on the compressed SIO namespace.

---

## Conclusion

The efficiency tradeoff: JSON-LD conditions pay 20% more in tokens/cost and 3-5s more in wall time per task for a modest +1.5% score improvement over baseline (0.900 vs 0.885). The improvement is concentrated in a single task (`sio-attribute-inverse`) where direct ontology access resolves an ambiguity that exploratory SPARQL missed. For the hardest tasks (`vocab-sio-inverse-chain`, `sio-measured-value-range`), JSON-LD access provides no benefit — these failures are in multi-hop inference and answer extraction, not in data access.

The combined condition shows no additive benefit over jsonld alone; its lower vocab task score (0.750 vs 0.875 in both baseline and jsonld) suggests that the additional tooling creates option paralysis on some runs.

At current task difficulty, the SPARQL-only baseline remains the most cost-efficient strategy. JSON-LD access would likely become more valuable for genuinely unfamiliar vocabularies not covered by SPARQL TBox caching, where the agent cannot fall back on pretraining knowledge to fill in ontological gaps.
