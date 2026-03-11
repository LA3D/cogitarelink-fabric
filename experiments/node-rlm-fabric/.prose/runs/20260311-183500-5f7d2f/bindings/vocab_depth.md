# vocab_depth

kind: let

source:
```prose
let vocab_depth = session: navigator_analyst
  prompt: "For trajectories using JSON-LD tools, measure vocabulary navigation depth..."
```

---

## Summary

JSON-LD tools reduce SPARQL calls for schema tasks by ~41% but do not reduce iteration count. The agent's navigation strategy shifts from iterative SPARQL exploration to a single fetch-and-filter pattern over the expanded JSON-LD graph. Both approaches converge in roughly the same number of iterations. The hard tasks (`vocab-sio-inverse-chain`, `sio-measured-value-range`) fail at the same rate regardless of access mode, indicating the failure is in answer extraction, not vocabulary navigation depth.

---

## Dataset

13 trajectory files across three conditions, all using `claude-sonnet-4-6` against `https://bootstrap.cogitarelink.ai`. Analyzed tool call patterns extracted from the `code` field of each trajectory step.

| Condition | Runs | Tasks | Schema tasks | Data tasks |
|-----------|------|-------|-------------|------------|
| js-baseline | 5 | 26 | 17 | 9 |
| js-jsonld | 4 | 20 | 14 | 6 |
| js-combined | 4 | 20 | 14 | 6 |

---

## 1. fetchJsonLd Call Counts and URLs

### Total fetchJsonLd calls by task and condition (js-jsonld)

| Task | fetchJsonLd/run | URLs fetched |
|------|----------------|--------------|
| `vocab-obs-to-sensor-properties` | 1.0 | `https://bootstrap.cogitarelink.ai/ontology/sosa` |
| `vocab-sio-float-range-properties` | 7.0 | `https://bootstrap.cogitarelink.ai/ontology/sio`, `http://semanticscience.org/ontology/sio.owl` |
| `vocab-sio-inverse-chain` | 0.5 | `https://bootstrap.cogitarelink.ai/ontology/sio` |
| `vocab-observation-subclasses` | 3.0 | `https://bootstrap.cogitarelink.ai/ontology/sosa`, `https://bootstrap.cogitarelink.ai/ontology/ssn-ext`, `http://www.w3.org/ns/sosa/` |
| `sio-attribute-inverse` | 1.0 | `https://bootstrap.cogitarelink.ai/ontology/sio` |
| `sio-has-value-type` | 0.5 | `https://bootstrap.cogitarelink.ai/ontology/sio` |
| `sio-measured-value-range` | 1.0 | `https://bootstrap.cogitarelink.ai/ontology/sio` |
| `obs-sio-*` (all three data tasks) | 0.0 | (none — fetchJsonLd never used) |

The agent first fetches the relevant ontology named graph from the fabric node (e.g., `/ontology/sio`, `/ontology/sosa`), which returns JSON-LD with `@context` pointing to `https://bootstrap.cogitarelink.ai/.well-known/context/meta.jsonld`. The internal fabric representation is a slim subset: the cached SIO graph has only 25 nodes in expanded form.

### One external escalation observed

In `vocab-sio-float-range-properties`, after finding no `rdfs:range xsd:float` in the fabric's 25-node SIO cache, the agent fetched `http://semanticscience.org/ontology/sio.owl` directly (5 repeat calls on the same URL in one run — the agent re-fetches on each iteration rather than caching the result in a variable). This is the only external vocabulary escalation across all runs.

---

## 2. jsonld.expand() Usage

`jsonld.expand()` is called to normalize prefixed JSON-LD into absolute IRIs before in-memory filtering. All calls target the already-fetched document — no additional network requests.

### Observed expand patterns by task

| Task | Condition | expand calls/run | What was expanded |
|------|-----------|-----------------|-------------------|
| `vocab-obs-to-sensor-properties` | js-jsonld | 1.5 | SOSA ontology — filtering for ObjectProperties with domainIncludes/rangeIncludes pointing to sosa:Observation and sosa:Sensor |
| `sio-attribute-inverse` | js-jsonld | 0.5 | SIO ontology — searching for `owl:inverseOf` on the `has-attribute` property |
| `sio-has-value-type` | js-jsonld | 0.5 | SIO ontology — finding the datatype of `sio:has-value` |
| `vocab-sio-float-range-properties` | js-jsonld | 2.0 | SIO ontology — querying all `rdfs:range` values (result: no `xsd:float` in the fabric's cached subset) |
| `vocab-observation-subclasses` | js-jsonld | 1.5 | SOSA + SSN-ext — filtering for `rdfs:subClassOf sosa:Observation` |

The expand step is always paired with JavaScript `.filter()` over the resulting array rather than using `jsonld.frame()` for extraction. The agent uses expand as a normalization preprocessor for its own traversal logic.

---

## 3. jsonld.frame() Usage

`jsonld.frame()` appears in only 3 steps across the entire dataset (one per condition):

| Task | Condition | Frame pattern | Result |
|------|-----------|---------------|--------|
| `vocab-obs-to-sensor-properties` | js-jsonld | `{ "@id": { "@in": ["sosa:madeBySensor", "sosa:madeObservation"] } }` | Retrieved full property descriptions with domain/range metadata |
| `vocab-sio-inverse-chain` | js-combined | `{ "@id": "http://semanticscience.org/resource/SIO_000070" }` | Empty — SIO_000070 not in the fabric's cached SIO subset |
| `vocab-observation-subclasses` | js-combined | Used `jsonld.expand` + JS `.filter()` (called as frame-like in reasoning) | No subclasses found (SOSA has none) |

`jsonld.frame()` is used sparingly and opportunistically — the agent reaches for it when it already knows the target IRI and wants structured output, but defaults to expand + filter otherwise. One frame call returned empty because the node identifier (SIO_000070/MeasuredValue) was not present in the fabric's slim SIO cache, which only contains 25 nodes covering the core observation-property chain.

---

## 4. @context Link-Following and Vocabulary Discovery

The agent does follow `@context` references — every JSON-LD response from the fabric includes `"@context": "https://bootstrap.cogitarelink.ai/.well-known/context/meta.jsonld"` — but in no run does the agent fetch that context document separately to discover related vocabularies. The agent treats the returned JSON-LD as self-contained.

### The ssn-ext case

In one `vocab-observation-subclasses` run (js-jsonld, `2026-03-11T18-45-54-138Z`), the agent fetches `https://bootstrap.cogitarelink.ai/ontology/ssn-ext` after an explicit SPARQL step reveals the SSN-ext named graph in the VoID. This is graph inventory discovery via SPARQL, not `@context` link-following.

```
Step 1: SPARQL — query /ontology/sosa for rdfs:subClassOf sosa:Observation → empty
Step 2: fetchJsonLd /ontology/sosa — inspect content
Step 3: jsonld.expand + filter → no subclasses
Step 4: SPARQL → empty
Step 5: SPARQL (all graphs) → empty
Step 6: fetchJsonLd http://www.w3.org/ns/sosa/ — fetch canonical W3C vocab → 0 subClassOf occurrences
Step 7: SPARQL enumerate classes in /ontology/sosa
Step 8: SPARQL enumerate classes in /ontology/ssn-ext (discovered from VoID graph inventory)
```

The agent independently discovers that `sosa:ObservationCollection` exists in SSN-ext but verifies (correctly) that it is not a `rdfs:subClassOf sosa:Observation`. The navigation is seven iterations deep before convergence — the same depth as baseline.

### No autonomous @context traversal observed

No trajectory shows the pattern: fetch document → read `@context` link → fetch that context → follow links to discover related vocabularies. The agent's JSON-LD navigation is always target-directed (known ontology IRI from VoID), not exploratory link-following.

---

## 5. Navigation Depth Before Sufficient Information

"Sufficient information" = the iteration at which the agent's SPARQL or JSON-LD call first returns the data needed to construct the correct answer.

### vocab-obs-to-sensor-properties

| Condition | Depth to sufficient info | Total iters | Method |
|-----------|------------------------|-------------|--------|
| js-baseline | Step 4 (SPARQL with `schema:domainIncludes` — after 3 failed attempts) | 7 | SPARQL exploration: tried `rdfs:domain`, then full scan, then sampled graph, then found `schema:domainIncludes` |
| js-jsonld | Step 1 (fetchJsonLd + expand — first try) | 4 | Fetched SOSA ontology directly, expanded to absolute IRIs, filtered for properties with correct predicates |
| js-combined | Step 1 (fetchJsonLd + expand) then Step 2 (cq refinement) | 6–7 | Mixed — one run used JSON-LD first, converged in 4 iters; other used SPARQL-first, 7 iters |

For this task, JSON-LD navigation reaches sufficient vocabulary information 3 iterations earlier than SPARQL exploration. The baseline agent requires 3 failed SPARQL probes to discover that SOSA uses `schema:domainIncludes` rather than `rdfs:domain` — the JSON-LD fetcher returns the full property node set without requiring knowledge of the predicate names.

### sio-attribute-inverse

| Condition | Depth to sufficient info | Total iters | Method |
|-----------|------------------------|-------------|--------|
| js-baseline (2 of 3 runs succeed) | Step 1 (SPARQL hit, 1 call) | 3–8 | When SPARQL probe finds `owl:inverseOf` in first attempt: 3 iters. When it doesn't: 8 iters |
| js-jsonld | Step 1 (fetchJsonLd + expand, 1 call) | 3 | Fetched SIO ontology, searched expanded array for nodes with `owl:inverseOf` |

The SPARQL-only approach is noisy for this task: whether it succeeds quickly depends on the query formulation in iteration 0. JSON-LD fetches the whole SIO graph once and filters in-memory, making the outcome deterministic.

### vocab-sio-float-range-properties

| Condition | Depth to sufficient info | Total iters | Method |
|-----------|------------------------|-------------|--------|
| js-baseline | Step 9 (after 10 SPARQL calls, found via all-graphs SELECT) | 13 | Extensive SPARQL exploration — DESCRIBE, SELECT over subsets, final all-graphs query |
| js-jsonld | Step 4–12 (fetched local SIO, found 0 xsd:float, escalated to external OWL) | 14 | Local fabric JSON-LD showed no `rdfs:range xsd:float` in 25-node cache; escalated to external `sio.owl`; correct answer (no such property exists) reached at step 12 |

This is the anomaly: JSON-LD navigation takes *more* iterations than SPARQL-only. The fabric's SIO cache is too thin for this task. The SPARQL all-graphs query (baseline step 9) reaches the same negative conclusion ("no `xsd:float` range") after 10 SPARQL calls and 13 iterations, versus 7 `fetchJsonLd` calls plus 3 SPARQL calls over 14 iterations in the JSON-LD condition. The JSON-LD path is slower because the agent escalates to an external OWL file and processes it line-by-line as raw text.

---

## 6. Efficiency Comparison: JSON-LD Navigation vs SPARQL Exploration

### Iteration counts

| Condition | Schema tasks (mean iters) | Data tasks (mean iters) |
|-----------|--------------------------|-------------------------|
| js-baseline | 6.35 (n=17) | 6.78 (n=9) |
| js-jsonld | 6.57 (n=14) | 6.83 (n=6) |
| js-combined | 6.36 (n=14) | — |

Iteration counts are essentially identical across conditions. JSON-LD navigation does not reduce total iterations.

### SPARQL call reduction for schema tasks

| Condition | Mean SPARQL calls/schema task |
|-----------|------------------------------|
| js-baseline | 4.71 |
| js-jsonld | 2.79 |

JSON-LD navigation reduces SPARQL calls by ~41% on schema tasks. The agent substitutes fetch-and-filter in-memory for iterative SPARQL probing. However, each iteration still involves at least one LLM call regardless of tool type, so the wall time and token cost are not reduced proportionally.

### Token overhead

| Condition | Mean tokens/task |
|-----------|-----------------|
| js-baseline | 35,542 |
| js-jsonld | 42,396 (+19%) |
| js-combined | 42,869 (+21%) |

JSON-LD documents (especially expanded form) are verbose. The single `vocab-sio-float-range-properties` run in js-jsonld consumed 108,044 tokens across 14 iterations with 7 fetchJsonLd calls. Large ontology payloads drive token overhead higher than the SPARQL-only baseline.

### Score improvement

JSON-LD access improves `sio-attribute-inverse` from 0.67 → 1.00 (both jsonld and combined). This is the most direct JSON-LD benefit: the SIO ontology's `owl:inverseOf` axioms are returned reliably by the endpoint JSON-LD fetch, whereas SPARQL probes sometimes miss them due to query formulation variance.

`vocab-sio-inverse-chain` and `sio-measured-value-range` fail at the same rate (50%) regardless of tool availability. The failure is not a navigation depth problem — it is answer extraction: the agent correctly identifies the property chain or the range constraint but formats the final answer incorrectly.

---

## 7. Key Findings

**Fetch-and-filter replaces iterative probe, not iterations**: JSON-LD navigation consolidates 3–5 SPARQL calls into 1 fetchJsonLd + in-memory filter. Each of these is still one LLM iteration. The per-task iteration budget does not shrink.

**Data tasks never use JSON-LD**: All 15 data task runs (obs-sio-*) across all conditions show 0 fetchJsonLd calls. The SPARQL endpoint serves instance data directly; there is no reason to navigate vocabulary documents for data retrieval. This replicates the Python phase 4–6 finding exactly in a different language and tool set.

**In-memory filtering is more reliable than SPARQL formulation for schema tasks**: The `sio-attribute-inverse` improvement (0.67→1.00) comes from bypassing SPARQL formulation uncertainty. Once the full expanded SIO graph is in memory, a JavaScript `.filter()` over `owl:inverseOf` nodes is deterministic regardless of SPARQL dialect issues.

**Fabric's L2 TBox cache is deliberately thin**: The cached SIO graph contains 25 nodes covering the core observation property chain. This is sufficient for most tasks but insufficient for `vocab-sio-float-range-properties`, which requires `xsd:float` range axioms that are absent from the subset. The agent correctly escalates to the canonical OWL file, but this escalation path is expensive (5 repeat fetches, raw XML text search).

**No autonomous @context link traversal occurs**: The agent never follows the `@context` link in a returned JSON-LD document to discover related vocabularies. All vocabulary discovery happens via VoID graph inventory (SPARQL) or direct IRI construction from prior knowledge. The D9 L1 VoID layer (not JSON-LD @context links) drives vocabulary navigation.

**JSON-LD navigation is faster for tasks where SOSA/SIO property axioms are the answer**: `vocab-obs-to-sensor-properties` converges 3 iterations earlier with fetchJsonLd. `sio-attribute-inverse` converges in 3 iterations vs a variable 3–8 with SPARQL. For tasks where the answer is a specific OWL axiom value, the fetch-and-filter pattern dominates.

**JSON-LD navigation is slower when the local TBox cache is incomplete**: `vocab-sio-float-range-properties` takes 14 iterations in js-jsonld vs 13 in js-baseline. The JSON-LD path triggers an external escalation that baseline SPARQL avoids by staying within the endpoint's all-graphs index.

---

## Appendix: Tool Sequence Abbreviations

| Abbreviation | Tool |
|---|---|
| `fv` | `fetchVoID` |
| `fs` | `fetchShapes` |
| `cq` | `comunica_query` |
| `fjl` | `fetchJsonLd` |
| `jsonld.expand` | `jsonld.expand()` in-process |
| `jsonld.frame` | `jsonld.frame()` in-process |
