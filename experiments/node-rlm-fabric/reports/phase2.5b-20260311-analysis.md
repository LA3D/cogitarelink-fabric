# Phase 2.5b: JSON-LD Navigation Analysis

**Date**: 2026-03-11
**Conditions**: js-baseline (n=5 runs, 26 tasks), js-jsonld (n=4 runs, 20 tasks), js-combined (n=4 runs, 20 tasks)
**Model**: claude-sonnet-4-6
**Endpoint**: https://bootstrap.cogitarelink.ai

---

## Key Finding

JSON-LD navigation provides a modest accuracy improvement (+1.5% mean score, 0.900 vs 0.885) concentrated in a single task class — small-ontology schema introspection with human-readable IRIs — at a 20% token cost premium and ~5s wall-time penalty per task. The SPARQL-first pattern from Python phases 4-6 replicates exactly in JavaScript: `fetchJsonLd` is adopted exclusively for schema tasks and never for data retrieval, confirming the selectivity is a structural property of the task type, not the tool interface.

---

## Tool Choice Patterns

### Iteration Family Distribution

| Family | js-baseline | js-jsonld | js-combined |
|--------|-------------|-----------|-------------|
| discovery | 25.7% (43/167) | 24.3% (34/140) | 25.4% (36/142) |
| sparql | 55.1% (92/167) | 47.1% (66/140) | 51.4% (73/142) |
| jsonld | 0.0% (0/167) | 11.4% (16/140) | 9.2% (13/142) |
| submit | 19.2% (32/167) | 17.1% (24/140) | 14.1% (20/142) |

JSON-LD occupies 11.4% of all js-jsonld iterations and 9.2% in js-combined. The discovery budget (fetchVoID, fetchShapes) is nearly identical across all three conditions, showing that JSON-LD displaces SPARQL iterations, not discovery iterations.

### Per-Condition Tool Adoption by Task Category

**Schema tasks** (sio-attribute-inverse, sio-has-value-type, sio-measured-value-range, vocab-*):

| Condition | Mean SPARQL/task | Mean fetchJsonLd/task | Mean jsonld.ops/task |
|-----------|------------------|-----------------------|----------------------|
| js-baseline | 4.71 | 0.00 | 0.00 |
| js-jsonld | 2.79 | 1.57 | 0.64 |
| js-combined | 3.14 | 0.86 | 0.43 |

**Data tasks** (obs-sio-chemical-entity, obs-sio-measured-value, obs-sio-unit):

| Condition | Mean SPARQL/task | Mean fetchJsonLd/task | Mean jsonld.ops/task |
|-----------|------------------|-----------------------|----------------------|
| js-baseline | 3.11 | 0.00 | 0.00 |
| js-jsonld | 3.17 | **0.00** | **0.00** |
| js-combined | 3.67 | **0.00** | **0.00** |

The data task columns are uniformly zero across all enhanced conditions. Every single one of the 12 data task runs in js-jsonld and js-combined showed zero `fetchJsonLd` calls. This is a clean, consistent finding.

### Per-Task fetchJsonLd Adoption (js-jsonld condition)

| Task | Runs | fetchJsonLd used | Mean calls/run |
|------|------|-----------------|----------------|
| obs-sio-chemical-entity | 2 | 0/2 | 0.0 |
| obs-sio-measured-value | 2 | 0/2 | 0.0 |
| obs-sio-unit | 2 | 0/2 | 0.0 |
| sio-attribute-inverse | 2 | 2/2 | 1.0 |
| sio-has-value-type | 2 | 2/2 | 1.0 |
| sio-measured-value-range | 2 | 2/2 | 1.0 |
| vocab-obs-to-sensor-properties | 2 | 2/2 | 1.0 |
| vocab-observation-subclasses | 2 | 2/2 | 3.0 |
| vocab-sio-datatype-property | 1 | 0/1 | 0.0 |
| vocab-sio-float-range-properties | 1 | 1/1 | 7.0 |
| vocab-sio-inverse-chain | 2 | 1/2 | 0.5 |

### Timeline Visualizations (representative trajectories)

**vocab-obs-to-sensor-properties** — best JSON-LD case (js-jsonld, 16:01):
```
i0: [discovery] fetchVoID
i1: [jsonld]    fetchJsonLd(/ontology/sosa) + jsonld.expand → filter → answer found
i2: [submit]    (none)
i3: [submit]    (none)
Score: 1  |  3 comunica calls: 0  |  iterations: 4
```

**vocab-obs-to-sensor-properties** — baseline comparison (js-baseline, 15:58):
```
i0: [discovery] fetchShapes + fetchVoID
i1: [sparql]    cq (rdfs:domain → [])
i2: [sparql]    cq (rdfs:range → [])
i3: [sparql]    cq (full scan → ...)
i4: [sparql]    cq (schema:domainIncludes → found)
i5: [sparql]    cq (confirm)
i6: [submit]    (none)
Score: 1  |  comunica calls: 5  |  iterations: 7
```

**vocab-sio-float-range-properties** — most complex case (js-jsonld, 16:01):
```
i0:  [discovery] fetchVoID
i1:  [sparql]    cq (rdfs:range xsd:float → [])
i2:  [sparql]    cq (all graphs → [])
i3:  [sparql]    cq (all range values → SIO class IRIs only)
i4:  [jsonld]    fetchJsonLd(/ontology/sio)
i5:  [jsonld]    jsonld.expand → filter XSD_FLOAT → 0 results (25-node cache incomplete)
i6:  [jsonld]    jsonld.expand → cross-check
i7:  [jsonld]    fetchJsonLd(http://semanticscience.org/ontology/sio.owl) — external escalation
i8:  [jsonld]    fetchJsonLd(sio.owl) again
i9:  [jsonld]    fetchJsonLd(sio.owl) again
i10: [jsonld]    fetchJsonLd(sio.owl) again
i11: [jsonld]    fetchJsonLd(sio.owl) again
i12: [jsonld]    fetchJsonLd(sio.owl) again
i13: [submit]    answer: "none" (confirmed via external OWL)
Score: 1  |  comunica calls: 3, fetchJsonLd calls: 7  |  iterations: 14
```

**vocab-sio-inverse-chain** — pure JSON-LD success (js-combined, 16:06):
```
i0: [discovery] fetchVoID
i1: [jsonld]    fetchJsonLd(/ontology/sio)
i2: [jsonld]    jsonld.expand → filter @id contains "attribute" → found owl:inverseOf
i3: [submit]    (none)
i4: [submit]    (none)
i5: [submit]    (none)
i6: [submit]    (none)
Score: 1  |  comunica calls: 0  |  iterations: 7
```

---

## The SPARQL/JSON-LD Boundary

### Where agents switch

The boundary is not a fixed iteration number — it's triggered by tool failure or empty results. The primary patterns observed across the 13 boundary moments identified in the data:

1. **SPARQL returns empty → switch to JSON-LD (diagnostic)**: The most common trigger. SIO stores properties under numeric IRIs (SIO_000008, SIO_000070). SPARQL with human-readable prefixed names (sio:has-attribute) returns `[]`. The agent fetches the JSON-LD to verify the ID scheme, then reformulates SPARQL with label search (`rdfs:label CONTAINS "has attribute"`).

2. **JSON-LD expand succeeds → no SPARQL needed**: The cleanest pattern. SOSA ontology is small (~30 nodes). `jsonld.expand` + JavaScript `.filter()` over the expanded array finds the answer in one step. Seen in 2 trajectories: `vocab-obs-to-sensor-properties` (js-jsonld 16:01) and `vocab-sio-inverse-chain` (js-combined 16:06).

3. **JSON-LD as confirmation after SPARQL success**: Agent finds the answer via SPARQL, then fetches JSON-LD to verify. Adds unnecessary iterations. Seen in `vocab-obs-to-sensor-properties` (js-combined 16:06): JSON-LD alone was sufficient but the agent ran 3 extra SPARQL queries to confirm.

4. **JSON-LD parse error → back to SPARQL**: The truncation failure mode. Large ontologies (SIO full graph) exceed the tool's output size limit, producing `SyntaxError: Bad control character in string literal in JSON at position 10000`. Agent correctly diagnoses truncation and returns to SPARQL. Seen 3 times in js-combined.

5. **JSON-LD diagnostic → label-based SPARQL**: Novel pattern not seen in Python experiments. Agent uses `fetchJsonLd` as a one-iteration probe to learn the ontology's ID scheme, then adapts SPARQL strategy. This is the most efficient use of JSON-LD in the dataset: one fetch call reduces subsequent SPARQL failures.

### Is there a consistent pattern?

Yes. The agent applies a consistent heuristic:

- **SPARQL-first** for all data tasks (without exception)
- **SPARQL-first then JSON-LD on failure** for most schema tasks (the majority pattern)
- **JSON-LD-first** for schema tasks on small ontologies where the agent's pretraining suggests a well-structured vocabulary document (SOSA, and occasionally SIO)

The natural boundary resolves to ontology scale and IRI transparency:

|  | Small ontology (SOSA ~30 nodes) | Large ontology (SIO ~700+ nodes) |
|---|---|---|
| Schema task | JSON-LD expand preferred — direct, efficient | SPARQL with label search preferred — no truncation risk |
| Data task | SPARQL only (N/A for JSON-LD) | SPARQL only (N/A for JSON-LD) |

---

## Vocabulary Navigation Depth

### How deep do agents go?

For tasks where JSON-LD is used, navigation depth is shallow — almost always a single fetch:

- `fetchJsonLd` is called once per task in 7 of the 11 tasks where it appears in js-jsonld
- The one outlier, `vocab-sio-float-range-properties`, required 7 calls (6 re-fetches of the external SIO OWL) because the agent did not cache the result in a variable between iterations
- No trajectory shows `@context` link-following to discover related vocabularies; all vocabulary discovery routes through the D9 L1 VoID graph inventory via SPARQL

### jsonld.expand vs jsonld.frame

| Operation | Calls total | Success rate | Notes |
|-----------|------------|--------------|-------|
| jsonld.expand | 11 | ~80% | Reliable on small graphs; fails with truncation on large |
| jsonld.frame | 4 | 50% | 2 successes on specific-IRI lookups; 2 failures (parse errors or empty result from incomplete cache) |

`jsonld.expand` is the operative tool. It normalizes the compact JSON-LD to absolute IRIs, after which the agent uses JavaScript `.filter()` for traversal — treating the expanded graph as an array of objects. `jsonld.frame` appears opportunistically when the agent already knows the target IRI, but is less reliable.

### Is navigation efficient?

Only when the fetch-and-filter completes in a single step. The key inefficiency is lack of inter-iteration variable persistence: the agent repeatedly re-fetches the same ontology URL across iterations (5 re-fetches of `sio.owl` in one task run) rather than caching the response. This multiplies the token cost of what should be a one-time fetch.

For tasks where JSON-LD succeeds efficiently:
- `vocab-obs-to-sensor-properties`: depth 1 (one fetch, one expand, one filter → answer)
- `sio-attribute-inverse`: depth 1 (one fetch, one expand, one `owl:inverseOf` lookup → answer)

For tasks where JSON-LD navigation becomes expensive:
- `vocab-sio-float-range-properties`: depth 7+ (one local cache miss, six external re-fetches)
- `vocab-observation-subclasses` (one run): depth 4 (two fetchJsonLd + two expand across 9 iterations)

---

## Condition Comparison

| Metric | js-baseline | js-jsonld | js-combined |
|--------|-------------|-----------|-------------|
| Runs | 5 | 4 | 4 |
| Task runs | 26 | 20 | 20 |
| **Mean score** | **0.885** | **0.900** | **0.850** |
| Mean iterations/task | 6.50 | 6.65 | 6.70 |
| Mean SPARQL/task | 4.15 | 2.90 | 3.30 |
| Mean fetchJsonLd/task | 0.00 | 1.10 | 0.60 |
| Mean jsonld.ops/task | 0.00 | 0.40 | 0.35 |
| Mean tokens/task | 35,542 | 42,396 | 42,869 |
| Mean wall time/task | 22.6s | 28.0s | 26.3s |
| Est. cost/task (USD) | $0.127 | $0.153 | $0.151 |
| Token overhead vs baseline | — | +19% | +21% |
| Cost overhead vs baseline | — | +20% | +19% |

**Score delta by task category:**

| Category | js-baseline | js-jsonld | js-combined |
|----------|-------------|-----------|-------------|
| SIO tasks (n=18/12/12) | 0.889 | **0.917** | **0.917** |
| Vocab tasks (n=8/8/8) | 0.875 | 0.875 | 0.750 |
| Data tasks (n=9/6/6) | 1.000 | 1.000 | 1.000 |
| **All** | **0.885** | **0.900** | **0.850** |

The js-combined condition underperforms on vocab tasks (0.750 vs 0.875 in baseline and jsonld). The likely cause: the additional tooling (write tools, rdfs-routes tools) creates option paralysis on runs where vocab tasks are the primary challenge, producing less decisive tool selection and higher iteration counts without accuracy gains.

---

## Per-Task Analysis

| taskId | condition | score (mean) | tool_sequence_pattern | boundary_moment | notes |
|--------|-----------|-------------|----------------------|-----------------|-------|
| obs-sio-chemical-entity | all | 1.00 | fv → cq → fetchEntity → cq | None | Data task; never touches JSON-LD |
| obs-sio-measured-value | all | 1.00 | fv → cq → fetchEntity → cq | None | Data task; never touches JSON-LD |
| obs-sio-unit | all | 1.00 | fv → cq → fetchEntity → cq | None | Data task; never touches JSON-LD |
| sio-has-value-type | baseline: 1.00, jsonld: 1.00, combined: 1.00 | 1.00 | baseline: fv→cq×2; jsonld: fjl+jexp i0 then fv→cq×2 | JSON-LD-first or SPARQL-first depending on run | Relative URL error in one jsonld run caused immediate fallback to SPARQL |
| sio-attribute-inverse | baseline: 0.67, jsonld: 1.00, combined: 1.00 | baseline 0.67 | baseline: fv→cq×(2-6); jsonld: fv→fjl+jexp→done | SPARQL→JSON-LD or JSON-LD-first | **The clear JSON-LD win**: owl:inverseOf from expand is deterministic; SPARQL formulation was noisy in baseline |
| sio-measured-value-range | baseline: 0.67, jsonld: 0.50, combined: 0.50 | worsens with JSON-LD | fv → (fjl diagnostic) → cq label-search | SPARQL→JSON-LD(peek)→SPARQL | Fails due to evaluator string mismatch ("MeasuredValue" vs SIO_000070 label); JSON-LD peek doesn't fix this |
| vocab-obs-to-sensor-properties | all: 1.00 | 1.00 | jsonld: fv→fjl+jexp→done (4 iter); baseline: fv→cq×5 (7 iter) | JSON-LD replaces 3+ SPARQL probes | Best efficiency gain from JSON-LD: 3 fewer iterations, 0 vs 5 SPARQL calls |
| vocab-observation-subclasses | all: 1.00 | 1.00 | cq→fv→cq×(3-5); jsonld adds fjl between sparql steps | SPARQL→JSON-LD→SPARQL (confirm) | Answer is "none"; both paths confirm via absence; JSON-LD adds redundant cross-check |
| vocab-sio-datatype-property | all: 1.00 | 1.00 | fv→cq×1-2→done | None (JSON-LD never used) | Simple SPARQL task; agent never reaches for JSON-LD |
| vocab-sio-float-range-properties | baseline: 1.00, jsonld: 1.00, combined: 0.00 | 0.67 | baseline: cq×10 (13 iter); jsonld: cq×3+fjl×7 (14 iter) | Exhausted SPARQL → JSON-LD → external OWL | Answer is "none"; jsonld path escalates to external OWL correctly; combined fails to complete escalation |
| vocab-sio-inverse-chain | all: 0.50 | 0.50 | Highly variable; combined 16:06 pure JSON-LD 0 SPARQL | SPARQL→JSON-LD→SPARQL or pure JSON-LD | Failure is answer formatting ("isAttributeOf" vs "is-attribute-of"); persists across all conditions |

---

## Research Implications

### Does JSON-LD add value? When?

JSON-LD access adds value in a narrow but real scenario: **small-ontology schema introspection where the answer is a specific OWL axiom value** (domain, range, inverseOf) and the ontology uses human-readable IRIs. The canonical example is `vocab-obs-to-sensor-properties` against SOSA: `jsonld.expand` over ~30 nodes is more efficient and deterministic than iterative SPARQL exploration. `sio-attribute-inverse` shows the accuracy benefit: the baseline's SPARQL formulation uncertainty (0.67 score) is eliminated by `owl:inverseOf` lookup from the expanded graph (1.00 score).

JSON-LD does **not** add value for:
- Data retrieval (instance triples from observation graphs)
- Tasks where the failure is in multi-hop reasoning or answer formatting, not data access
- Tasks requiring the full canonical OWL file of large ontologies (SIO ~700+ nodes), where the fabric's L2 TBox cache is intentionally thin

### Connections to D9 Progressive Disclosure

The experiment confirms D9's four-layer KR architecture is doing what it was designed to do. The agent navigates L1 (VoID self-description) in every task, L2 (TBox cache via fetchJsonLd) selectively for schema tasks, and L3/L4 (SHACL shapes + SPARQL examples) implicitly via the endpoint SD. The four layers are not additive overhead — the agent routes to the appropriate layer based on task type. JSON-LD is the L2 access mechanism; SPARQL is L1/L4 access.

The missing piece is the gap between L2 (fabric's 25-node SIO cache) and canonical SIO (~700 nodes). The agent's escalation to `http://semanticscience.org/ontology/sio.owl` in `vocab-sio-float-range-properties` was correct but inefficient (5 re-fetches, raw XML text search). This points to D9 L2 design work: the fabric should either cache a richer SIO subset or provide a cleaner query interface for canonical-vocabulary questions.

### D31 Transport Complementarity

These results provide the empirical grounding for a new design decision around transport-level complementarity. JSON-LD and SPARQL are not competing retrieval mechanisms — they are complementary access modes suited to different task/data combinations:

| Data characteristic | Preferred access | Reason |
|---------------------|-----------------|--------|
| Instance triples (observations, sensor readings) | SPARQL | Pattern matching across graph; no vocabulary structure needed |
| Small vocabulary axioms (SOSA, curated SIO subset) | JSON-LD expand | One fetch, in-memory filter, deterministic |
| Large vocabulary axioms (full SIO, OWL files) | SPARQL with label search | Truncation-safe; label-based predicates work across numeric IRI schemes |
| Diagnostic IRI scheme identification | JSON-LD peek (unfollowed) | Single fetch to inspect raw ID format before reformulating SPARQL |

A fabric that serves both formats from the same named graph (as it currently does — fetchJsonLd on `/ontology/soa` returns the same data that SPARQL queries) enables the agent to choose dynamically based on task context.

### The selectivity finding replicates across languages

The Python phases 4-6 finding — that schema-introspection tools are adopted selectively (2/6 tasks per run) and ignored for data tasks — reproduces cleanly in JavaScript with a different tool interface, different execution substrate, and different vocabulary set. The agent independently arrives at the same task-type heuristic. This suggests the selectivity is not an artifact of the Python DSPy framework or the specific tool signature — it is a stable behavioral property driven by task structure.

---

## Recommendations

### Immediate experiments

1. **Resolve the vocab-sio-inverse-chain scoring issue**: The task fails at 50% across all conditions due to answer formatting (camelCase vs hyphenated), not reasoning failure. Fix the evaluator or the answer key to accept both "is-attribute-of" and "isAttributeOf" / the numeric IRI SIO_000011. Then re-run to confirm whether JSON-LD access provides any benefit for this task type.

2. **Resolve the sio-measured-value-range regression**: JSON-LD conditions score worse (0.50) than baseline (0.67) on this task. The root cause is an evaluator string-match issue ("MeasuredValue" vs "SIO_000070" with label "measurement value"). The agent's reasoning is correct but the answer format doesn't match. Fixing the evaluator may reveal that this task is actually solved correctly across all conditions.

3. **Add variable caching across iterations**: The `vocab-sio-float-range-properties` run in js-jsonld re-fetched the external `sio.owl` file 5 times. A simple inter-iteration store (`window.__fetchCache` or a global Map in the agent code) would eliminate this. This is likely a significant source of the token overhead.

### Fabric structure changes

4. **Expand the L2 SIO TBox cache**: The 25-node SIO subset is insufficient for `vocab-sio-float-range-properties` and triggers external escalation. Add the `rdfs:range` axioms for the core observation property chain (SIO_000216 → rdfs:range → SIO_000070, etc.) to the cached graph. This would make `sio-measured-value-range` solvable via local JSON-LD, eliminating the external OWL fetch.

5. **Expose VoID `void:subset` or PROF `prof:hasResource` for "lite" vs "full" ontology variants**: The agent currently cannot distinguish the fabric's slim TBox cache from a complete copy of the ontology. Adding metadata that signals incompleteness (e.g., `fabric:coverage "subset"`, `void:triples 25`) would let the agent short-circuit the local-fetch→external-escalation pattern and go directly to the canonical source.

6. **Fix the `jsonld.frame` truncation bug**: Large ontologies exceed the output size limit and produce invalid JSON at position 10000. This affects every attempt to use `jsonld.frame` on SIO. Fix the tool to either increase the output limit or return a clean error with the truncated document's byte count so the agent can decide whether to proceed with partial data.

### Tool improvements

7. **Add `fetchJsonLdCompact` or an in-API filter parameter**: The agent uses `fetchJsonLd` + `jsonld.expand` + JavaScript filter. Providing `fetchJsonLd(url, { filter: { property: "owl:inverseOf" } })` would return only the relevant nodes and eliminate the large expanded-graph token overhead. This directly addresses the 20% token premium.

8. **Investigate `jsonld.frame` as a replacement for expand+filter**: When it works (2/4 cases), `jsonld.frame` is cleaner than expand+filter. The parse error from truncation is the primary barrier. A fix to the output limit would make framing the preferred pattern for specific-IRI lookups, which are the most common schema-task use case.

9. **Consider phase2.5c with genuinely unfamiliar vocabulary**: All current experiments use SIO and SOSA, both partially covered by pretraining. The untested hypothesis — that JSON-LD becomes essential for vocabularies outside pretraining — should be tested with a custom or obscure vocabulary that the model cannot reason about without explicit structure. This is the cleanest path to understanding whether JSON-LD provides capability (new knowledge) vs. guardrail (confirmatory mode for known knowledge).

---

## Appendix: Persistent Failures

| Task | All-condition score | Root cause | JSON-LD impact |
|------|-------------------|------------|----------------|
| vocab-sio-inverse-chain | 0.50 | Answer format: agent returns "isAttributeOf" (camelCase), evaluator expects "is-attribute-of" (hyphenated) | None — both formats are correct SIO vocabulary representations |
| sio-measured-value-range | baseline: 0.67, jsonld/combined: 0.50 | Answer format: agent returns SIO numeric IRI or label "measurement value", evaluator expects string "MeasuredValue" | Slight regression — JSON-LD access enables the agent to find the range more consistently but in a format the evaluator rejects |
| vocab-sio-float-range-properties | baseline: 1.00, jsonld: 1.00, combined: 0.00 | js-combined fails because the agent does not escalate to external OWL (stops after diagnostic JSON-LD peek without completing the fetch-and-search pattern) | JSON-LD is necessary for the correct answer (confirming "none" via canonical SIO); combined's tooling mix discourages the escalation |
