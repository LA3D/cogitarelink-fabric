# boundary_moments

kind: let

source:
```prose
let boundary_moments = session: boundary_analyst
  prompt: "For js-jsonld and js-combined conditions, find boundary moments: iterations where the agent switches from JSON-LD navigation to SPARQL (or vice versa). Analyze what triggered the switch, whether it succeeded, and whether it was necessary."
```

---

## Overview

Across 8 runs (4 js-jsonld + 4 js-combined), 13 boundary moments were identified — instances where the agent switched tool families mid-task. Additionally, 6 tasks showed a stronger finding: no switch occurred because one tool family was sufficient from the start. The analysis covers all tasks where both SPARQL (comunica_query) and JSON-LD (fetchJsonLd / jsonld.*) appeared in the trajectory.

Abbreviations: `fjl` = fetchJsonLd, `cq` = comunica_query, `fv` = fetchVoID, `jexp` = jsonld.expand, `jframe` = jsonld.frame.

---

## Data Tasks (obs-*): No Boundary Moments — SPARQL-Only Pattern

Across all 12 obs-task runs in js-jsonld and js-combined, `fetchJsonLd` was called **zero times**. The agent never attempted a JSON-LD switch for data retrieval. This is a clean non-event finding.

**Why**: Data tasks ask "what is the measured value / unit / chemical entity of this observation?" The answer lives in `/graph/observations` as RDF triples. SPARQL fetches it directly. JSON-LD vocabulary navigation would be irrelevant — there is no ontology structure to traverse, only instance data to query.

**Pattern**: `fv → cq → fetchEntity (optional 404) → cq → return`. The agent bootstraps with fetchVoID, issues one broad SPARQL, falls back to `fetchEntity` when guessing IRIs, then issues a targeted follow-up query. The boundary is never reached because the task does not touch ontology structure.

This mirrors the Python experiment finding: `fetchJsonLd` is the JS equivalent of `analyze_rdfs_routes`, and both are called exclusively on schema tasks.

---

## Schema Task: SPARQL First, JSON-LD on Failure

### Boundary Moment 1 — `sio-has-value-type` (js-jsonld, 16:08, iter 0→1)

**Before**: Agent starts at iter 0 with `fetchJsonLd('/ontology/sio')` + `jsonld.expand`. Fails immediately — relative URL causes `Fetch error: Failed to parse URL from /ontology/sio`.

**Trigger**: Hard error. The relative path is invalid in the runtime context (requires a fully-qualified URL).

**Switch**: iter 1 falls back to `fetchVoID()` to discover the correct base URL, then iter 2 issues SPARQL. The JSON-LD path is abandoned entirely.

**Did it succeed?**: Yes — SPARQL alone finds `owl:DatatypeProperty` in two queries. Score = 1.

**Was the switch necessary?**: The initial JSON-LD attempt was unnecessary (wrong URL). After the error the agent correctly routes to SPARQL, which was always sufficient. The JSON-LD path would have worked too with the correct URL (`https://bootstrap.cogitarelink.ai/ontology/sio`).

---

### Boundary Moment 2 — `sio-attribute-inverse` (js-jsonld, 16:08, iter 0→1)

**Before**: iter 0 starts with `fetchVoID()` — the standard discovery pattern. No JSON-LD or SPARQL yet.

**Trigger**: None explicit. Agent chooses JSON-LD proactively at iter 1.

**Switch**: iter 1 calls `fetchJsonLd("https://bootstrap.cogitarelink.ai/ontology/sio")` + `jsonld.expand`, then filters the expanded graph for `has-attribute`. Finds the inverse directly from the JSON-LD structure without any SPARQL.

**Did it succeed?**: Yes — `jsonld.expand` exposes `owl:inverseOf` as a plain JSON property. The agent reads off `is-attribute-of` in one step. Score = 1, only 3 iterations.

**Was the switch necessary?**: JSON-LD was the more direct route here. SPARQL would have required two queries (find property by label, then query its inverseOf). JSON-LD expand + filter is more efficient for this task type — finding one property and its axioms in a small ontology graph.

---

### Boundary Moment 3 — `sio-measured-value-range` (js-jsonld, 16:08, iter 0→2)

**Before**: iter 0 `fetchVoID()`. iter 1 `fetchJsonLd('https://bootstrap.cogitarelink.ai/ontology/sio')` — agent inspects raw JSON-LD but only prints first 3000 chars, which does not contain the answer.

**Trigger**: Incomplete output. The ontology JSON-LD is large; the first 3000 chars preview covers only `InformationContentEntity`. The answer about `has-measurement-value` is not visible.

**Switch**: iter 2 issues SPARQL with a `FROM <.../ontology/sio>` clause. Gets a 400 error (missing `rdfs:` prefix declaration). iter 3 fixes the SPARQL. Returns `rdfs:range = sio:MeasuredValue`.

**Did it succeed?**: Yes. Score = 1.

**Was the switch necessary?**: Partly. The agent fetched JSON-LD but didn't parse/search it — only previewed it. SPARQL was needed because the agent never actually read the JSON-LD structure (no `jsonld.expand` call in this run). In the successful pattern (see js-jsonld 16:01 run), the agent would have expanded the JSON-LD and filtered for `rdfs:range`. The switch from "peek at JSON-LD" to SPARQL was the correct recovery.

---

### Boundary Moment 4 — `sio-attribute-inverse` (js-jsonld, 18:53, iters 1→2→3→4)

**Before**: iter 0 `fetchVoID()`. iter 1 tries SPARQL for `owl:inverseOf` on `sio:has-attribute` in the named graph. Returns `[]`.

**Trigger**: SPARQL returns empty. The endpoint stores SIO under numeric IRIs (`SIO_000008`) not human-readable ones (`sio:has-attribute`). SPARQL with the prefixed name finds nothing.

**Switch**: iter 2 calls `fetchJsonLd('https://bootstrap.cogitarelink.ai/ontology/sio')`. Doesn't parse it. iter 3 issues a SPARQL query searching by label `"has attribute"` — this works, returns the IRI `SIO_000008` and its inverse `SIO_000011`.

**Did it succeed?**: Yes. Score = 1.

**Was the switch necessary?**: The initial JSON-LD fetch was unused (just printed). The real switch that mattered was the SPARQL strategy change: from `sio:has-attribute owl:inverseOf ?x` to `?prop rdfs:label "has attribute"; owl:inverseOf ?x`. The JSON-LD call in iter 2 was a diagnostic that confirmed the ontology uses numeric IRIs, which informed the label-search SPARQL strategy.

**Key insight**: The agent learned from the JSON-LD peek (iter 2 output shows `SIO_010336`...) that SIO uses numeric IDs and switched to a label-based SPARQL approach. The JSON-LD here served as diagnostic ground truth, not as the primary retrieval mechanism.

---

### Boundary Moment 5 — `sio-measured-value-range` (js-jsonld, 18:53, iters 1→2→3)

**Before**: iter 0 `fetchVoID()`. iter 1 SPARQL for `sio:has-measurement-value rdfs:range ?range` in the named graph — returns `[]` (same prefixed-name problem as above).

**Trigger**: SPARQL with human-readable prefix fails because the endpoint stores `SIO_000216` not `sio:has-measurement-value`.

**Switch**: iter 2 `fetchJsonLd` — agent peeks at the raw JSON-LD (first 3000 chars), sees numeric IDs again. iter 3 SPARQL with label search `CONTAINS(LCASE(STR(?label)), "measurement")` — finds `SIO_000216`.

**Did it succeed?**: Agent finds the correct property `SIO_000216` → range `SIO_000070`. But score = 0. The expected answer is "MeasuredValue" and the agent returns "measurement value" / `SIO_000070`. The evaluator requires the string "MeasuredValue" and this does not match `SIO_000070` or the label "measurement value". This is a **scoring mismatch**, not a reasoning failure — the agent found the right class but under its numeric ID with a label that doesn't exactly match the expected string.

**Was the switch necessary?**: Yes — SPARQL by prefixed name fails on this endpoint for SIO. The JSON-LD peek was useful as a diagnostic step. The label-search SPARQL pattern is the correct adaptive response.

---

### Boundary Moment 6 — `vocab-obs-to-sensor-properties` (js-jsonld, 16:01, iters 0→1→2)

**Before**: iter 0 `fetchVoID()`. iter 1 `fetchJsonLd` + `jsonld.expand` — agent expands the SOSA ontology and filters for ObjectProperties with `sosa:Observation`/`sosa:Sensor` in domain/range.

**Trigger**: JSON-LD expand succeeds and returns the answer. No SPARQL needed.

**Pattern**: Pure JSON-LD path. No boundary moment. Score = 1, only 4 iterations (including 2 no-op return steps).

**Was SPARQL needed?**: No. JSON-LD expand of the SOSA ontology (~30 nodes) gives clean access to all properties, their types, and their `schema:domainIncludes` annotations. The agent filters the expanded graph in-memory and returns both properties directly.

---

### Boundary Moment 7 — `vocab-obs-to-sensor-properties` (js-combined, 16:06, iters 1→2→3)

**Before**: iter 0 `fetchVoID()`. iter 1 `fetchJsonLd` + `jsonld.expand`.

**Trigger**: JSON-LD expand returns data but the agent doesn't trust it as sufficient. After extracting the answer from JSON-LD in iter 1, the agent issues SPARQL in iters 2-4 to confirm via `rdfs:domain`/`rdfs:range` and `owl:inverseOf`.

**Switch**: JSON-LD first, then SPARQL for verification.

**Did it succeed?**: Yes. Score = 1.

**Was the switch necessary?**: No. The JSON-LD path alone (as in js-jsonld 16:01) was sufficient. The agent over-verified — this added 3 extra SPARQL iterations and more tokens for no additional accuracy. This is the "confirmatory mode" pattern: JSON-LD provides the answer, SPARQL verifies it.

---

### Boundary Moment 8 — `vocab-sio-inverse-chain` (js-combined, 16:06, iters 0→1)

**Before**: iter 0 `fetchVoID()`. iter 1 `fetchJsonLd` + `jsonld.expand` — agent uses JavaScript array filter on the expanded graph to find terms containing "attribute" in their IRI.

**Trigger**: Proactive JSON-LD choice. The agent knows this is an SIO schema task and starts with vocabulary-level navigation.

**Switch**: None needed — JSON-LD alone resolves the task. iter 2 calls `jsonld.expand` (on the already-fetched document to pull out the full `is-attribute-of` node). Confirms `owl:inverseOf` relationship. No SPARQL at all.

**Did it succeed?**: Yes. Score = 1, 0 comunica_query calls.

**Was SPARQL needed?**: No. This is the cleanest JSON-LD-only successful trajectory in the dataset. The agent fetches once, expands, filters by IRI substring, and reads `owl:inverseOf` directly from the expanded graph. The task is pure schema introspection and JSON-LD handles it completely.

---

### Boundary Moment 9 — `vocab-sio-inverse-chain` (js-combined, 18:48, iters 1→2→3→4→5)

**Before**: iter 0 `fetchVoID()`. iter 1 tries SPARQL CONSTRUCT (not SELECT) — gets error "Query result type 'bindings' was expected, while 'quads' was found." iter 2 falls back to SPARQL SELECT, but queries with `FROM <.../ontology/sio>` and the prefixed `sio:MeasuredValue`. Returns `[]`.

**Trigger**: Two consecutive SPARQL failures — wrong query type, then wrong IRI form.

**Switch**: iter 3 `fetchJsonLd`. The large SIO JSON-LD arrives but at iter 4 the agent tries `jsonld.frame` on `sio:SIO_000070` — fails with JSON parse error (bad control character at position 10000, likely from the outputSize limit truncating the JSON mid-stream).

**Second switch**: iter 5 back to SPARQL. The agent now uses the SIO numeric ID `SIO_000070` learned from earlier inspection, and finds the property via label search. Eventually finds `SIO_000011 "is attribute of"`. Returns `sio:isAttributeOf`.

**Did it succeed?**: No. Score = 0. The expected answer is "is-attribute-of" (hyphenated), but the agent returns "isAttributeOf" (camelCase). This is a string-format mismatch — the reasoning was correct.

**Was each switch necessary?**: The first JSON-LD attempt (iter 3-4) was necessary as recovery from SPARQL failure but was itself foiled by the JSON parse error. The second SPARQL return (iter 5+) was the correct final strategy. Two boundary moments in one trajectory: SPARQL→JSON-LD (recovery from CONSTRUCT error + empty SELECT) then JSON-LD→SPARQL (recovery from JSON parse truncation error).

---

### Boundary Moment 10 — `vocab-observation-subclasses` (js-combined, 18:48, iters 2→3→4)

**Before**: iters 0-2 use `fetchVoID()` then two SPARQL queries — both return `[]`. iter 2 `fetchJsonLd` gets the SOSA ontology.

**Trigger**: Two SPARQL queries for `rdfs:subClassOf sosa:Observation` return empty. Agent switches to JSON-LD to verify via a different access path.

**Switch**: iter 3 tries `jsonld.expand` + filter for `rdfs:subClassOf = sosa:Observation`. Gets JSON parse error (same truncation issue).

**Recovery**: iter 4 returns to SPARQL — broader cross-graph query also finds nothing. Agent concludes the absence is real.

**Did it succeed?**: Yes. Score = 1. The expected answer is "none" and the agent confirms this.

**Was the switch necessary?**: The JSON-LD attempt was a redundant cross-check. SPARQL had already confirmed absence at iters 1-2. The JSON-LD failed with a parse error anyway. The agent correctly concluded "none" from the SPARQL evidence alone (iter 4+ SPARQL confirms).

---

### Boundary Moment 11 — `vocab-sio-float-range-properties` (js-jsonld, 16:01, iters 1→4→5→6→7)

This task is the most complex boundary case: **repeated back-and-forth between SPARQL and JSON-LD over 14 iterations**.

**Phase 1 (iters 1-3)**: SPARQL with `rdfs:range xsd:float` in named graph → `[]`. SPARQL across all graphs → `[]`. SPARQL for all range values → shows only SIO class IRIs, no XSD types.

**Trigger**: SPARQL exhausted — the endpoint truly has no `rdfs:range xsd:float` axiom. Agent correctly reads this as a substrate limitation, not a query error.

**Phase 2 (iters 4-6)**: `fetchJsonLd` for the local SIO subset → `jsonld.expand` → filter for `XSD_FLOAT` in ranges → 0 results. Local graph confirmed incomplete (25 nodes, no XSD datatypes). Cross-checks via second `jsonld.expand` call.

**Trigger**: JSON-LD confirms the local graph is a curated subset. Agent correctly concludes it needs the upstream ontology.

**Phase 3 (iters 7-12)**: Agent fetches the canonical SIO OWL file from `http://semanticscience.org/ontology/sio.owl` using `fetchJsonLd` as an HTTP fetch. Searches line-by-line for "float". Finds 2 occurrences — one `owl:someValuesFrom xsd:float` (not `rdfs:range`), one irrelevant. Confirms no `rdfs:range xsd:float` exists.

**Did it succeed?**: Yes. Score = 1. The correct answer is "none" — SIO uses `owl:someValuesFrom` restrictions, not `rdfs:range` axioms, for xsd:float.

**Was it necessary?**: The repeated switching was necessary because this task has a negative answer that required exhaustive verification. SPARQL confirmed the local graph had no xsd:float ranges. JSON-LD confirmed the local graph was a 25-node subset. The external OWL fetch confirmed the canonical source also lacks `rdfs:range xsd:float`. Each tool confirmed a different layer of the substrate, and the correct answer required all three confirmations to be credible.

This is the one task where the multi-tool switching pattern adds genuine epistemic value — not just confirmatory redundancy.

---

### Boundary Moment 12 — `vocab-sio-float-range-properties` (js-combined, 16:06, iters 2→7→8)

**Pattern**: SPARQL confirms empty local graph (iters 1, 5, 6, 8-10). JSON-LD fetch (iter 2) peeks at the raw ontology. Another JSON-LD fetch (iter 7) tries to reach `http://semanticscience.org/resource/` — gets HTTP 404. Agent does not escalate to the external OWL file (as in js-jsonld).

**Switch**: JSON-LD used for two diagnostic peeks between SPARQL queries. Neither JSON-LD call uses `jsonld.expand` or structured parsing.

**Did it succeed?**: No. Score = 0. The agent concludes "no rdfs:range xsd:float in the fabric endpoint's SIO graph" and returns without checking the upstream canonical OWL. This is the correct finding for the fabric endpoint, but the evaluator likely expected "none" based on canonical SIO.

**Was it necessary?**: The JSON-LD calls were diagnostic peeks that confirmed the local graph is incomplete. The agent stopped short of the upstream OWL fetch that would have clinched the answer.

---

### Boundary Moment 13 — `vocab-observation-subclasses` (js-jsonld, 18:45, iters 1-8)

**Before**: iter 0 `fetchVoID()`. iter 1 `cq` (subClassOf in named graph → `[]`). iter 2 `fjl` (peek at SOSA JSON-LD). iters 3-4 more `fjl` calls + `cq`. iters 4, 5, 6, 7 all SPARQL with escalating breadth.

**Pattern**: SPARQL → JSON-LD (for confirmation) → SPARQL (for broader search). Multiple sub-patterns.

**Did it succeed?**: No. Score = 0. The expected answer is "none". The agent iterates 8 times across tools but at iter 7 returns without a clear negative answer. The task expects the agent to explicitly say "none" — the trajectory ends without that definitive statement being returned.

**Was the switching necessary?**: The JSON-LD calls confirmed the SOSA graph is loaded. The SPARQL queries at expanding scope confirmed no subclasses exist. The switching itself was reasonable but the agent failed to synthesize the evidence into a clean negative answer.

---

## Summary Table

| Task | Run | Condition | Trigger for Switch | Direction | Score | Switch Necessary? |
|---|---|---|---|---|---|---|
| sio-has-value-type | 16:08 | js-jsonld | Error (relative URL in fetchJsonLd) | JSON-LD→SPARQL | 1 | Yes (error recovery) |
| sio-attribute-inverse | 16:08 | js-jsonld | Proactive choice | VoID→JSON-LD (no SPARQL) | 1 | No (JSON-LD alone sufficient) |
| sio-measured-value-range | 16:08 | js-jsonld | Incomplete JSON-LD preview | JSON-LD peek→SPARQL | 1 | SPARQL was the operative tool |
| sio-attribute-inverse | 18:53 | js-jsonld | SPARQL returns [] (numeric IRI mismatch) | SPARQL→JSON-LD (diagnostic)→SPARQL (label) | 1 | JSON-LD as diagnostic |
| sio-measured-value-range | 18:53 | js-jsonld | SPARQL returns [] (numeric IRI mismatch) | SPARQL→JSON-LD (diagnostic)→SPARQL (label) | 0* | JSON-LD as diagnostic |
| vocab-obs-to-sensor-properties | 16:01 | js-jsonld | Pure JSON-LD (no switch) | JSON-LD only | 1 | N/A |
| vocab-obs-to-sensor-properties | 16:06 | js-combined | Proactive choice then over-verification | JSON-LD→SPARQL (confirm) | 1 | No (JSON-LD alone sufficient) |
| vocab-sio-inverse-chain | 16:06 | js-combined | Proactive choice | JSON-LD only | 1 | N/A |
| vocab-sio-inverse-chain | 18:48 | js-combined | SPARQL CONSTRUCT error + empty SELECT | SPARQL→JSON-LD (parse error)→SPARQL | 0* | Yes (recovery chain) |
| vocab-observation-subclasses | 18:48 | js-combined | SPARQL confirms absence → redundant check | SPARQL→JSON-LD (failed)→SPARQL | 1 | No (SPARQL alone sufficient) |
| vocab-sio-float-range-properties | 16:01 | js-jsonld | Exhausted SPARQL on local graph | SPARQL→JSON-LD→external OWL fetch | 1 | Yes (multi-layer verification) |
| vocab-sio-float-range-properties | 16:06 | js-combined | Partial exhaustion of SPARQL | SPARQL→JSON-LD (diagnostic only) | 0 | Incomplete (stopped before external OWL) |
| vocab-observation-subclasses | 18:45 | js-jsonld | SPARQL→JSON-LD→SPARQL escalation | Multi-switch | 0 | Unclear — failed to return "none" |

*Score = 0 due to string format mismatch, not reasoning failure.

---

## Findings

### Finding 1: The natural boundary is ontology size and IRI transparency

The clearest boundary signal is whether the ontology uses human-readable IRIs (SOSA: `sosa:Observation`, `sosa:madeBySensor`) or opaque numeric IRIs (SIO: `SIO_000008`, `SIO_000070`).

- **SOSA tasks** (vocab-obs-to-sensor-properties): JSON-LD is the dominant tool. Expand + filter on the small SOSA graph (~30 nodes) is sufficient and more direct than SPARQL. The agent uses SPARQL only for confirmation or when it misses the JSON-LD first step.
- **SIO tasks** with human-readable names (sio-attribute-inverse, sio-has-value-type): JSON-LD works for the small local subset where `has-attribute` and `is-attribute-of` are stored with their prefixed IRIs. SPARQL by prefixed name also works on this subset.
- **SIO tasks** using numeric IDs (sio-measured-value-range, vocab-sio-inverse-chain in the full graph): SPARQL with prefixed names fails (returns `[]`). The correct adaptive strategy is label-search SPARQL or JSON-LD traversal using substring matching. Agents that try prefixed-name SPARQL first must switch to one of these.

### Finding 2: JSON-LD as diagnostic, not primary retrieval

In 5 of the 13 boundary moments, the agent used `fetchJsonLd` as a diagnostic step — peeking at the raw JSON to understand the ontology's ID scheme (numeric vs. prefixed) — rather than as the primary retrieval mechanism. The agent then returned to SPARQL with a better-informed query (label search instead of prefixed-IRI lookup).

This is a novel pattern not seen in the Python baseline: JSON-LD as a low-cost probe to adapt SPARQL strategy. The probe costs roughly one iteration (one LLM call + one HTTP request) and often unblocks the subsequent SPARQL query.

### Finding 3: JSON-LD expand is the high-value JSON-LD operation

When JSON-LD succeeds, it almost always involves `jsonld.expand`. The expand operation normalizes compact IRIs and context-qualified terms into full IRI form, making property lookup a simple `Array.filter`. Calls that just `console.log(sioJsonLd.substring(0, N))` without expand rarely produce answers — they are the diagnostic peeks of Finding 2.

`jsonld.frame` appeared in 4 trajectories and failed in 2 (JSON parse error due to output truncation). Frame is more powerful but requires a well-formed full document. The truncation bug makes it unreliable for large ontologies.

### Finding 4: The parse error at position 10000 is a recurring failure mode

Three boundary moments were caused or complicated by the same error: `SyntaxError: Bad control character in string literal in JSON at position 10000`. This occurs when the agent calls `JSON.parse(await fetchJsonLd(...))` on a large ontology and the tool implementation truncates the output at a character boundary, producing invalid JSON.

Every time this error occurred (js-combined 18:48 vocab-sio-inverse-chain iter 4; js-combined 18:48 vocab-observation-subclasses iter 3), the agent correctly diagnosed it as a truncation problem and switched back to SPARQL. The error is a hard boundary: large ontologies (SIO full graph, SOSA in some contexts) cannot be processed via JSON-LD expand when the tool output is truncated.

The js-jsonld run that successfully used JSON-LD expand on the full SOSA graph (16:01 iter 1) worked because the graph is small (~30 nodes). The runs that failed with parse errors were attempting the same on the larger SIO full graph.

### Finding 5: The boundary is data type × ontology size

The natural boundary between JSON-LD and SPARQL resolves to a 2x2:

|  | Small ontology (SOSA ~30 nodes) | Large ontology (SIO ~700+ nodes) |
|---|---|---|
| **Schema task** | JSON-LD expand preferred — direct, efficient | SPARQL preferred — no truncation risk; label-search works |
| **Data task** | SPARQL only (N/A for JSON-LD) | SPARQL only (N/A for JSON-LD) |

For small ontologies, JSON-LD expand is simpler and requires fewer iterations. For large ontologies, SPARQL with appropriate `FROM` clauses and label-based filtering is more reliable. The agent's natural behavior reflects this: it switches to SPARQL when JSON-LD fails or returns incomplete data, and it switches to JSON-LD when SPARQL returns empty results on prefixed-IRI queries.

### Finding 6: `vocab-sio-inverse-chain` fails consistently at 50% across all conditions for a non-tool reason

The task expects "is-attribute-of" (hyphenated). Agents consistently find the correct concept (`SIO_000011`, label "is attribute of") but return it as "isAttributeOf" (camelCase) or "is-attribute-of with the SIO_000011 IRI". The evaluator's string-match on "is-attribute-of" fails when the agent uses camelCase or provides additional context.

This is not a JSON-LD/SPARQL boundary issue — it is an answer-formatting issue that affects all conditions equally. The boundary moments in this task (SPARQL→JSON-LD→SPARQL) are incidental to the failure.

### Finding 7: Pure JSON-LD success cases are rare but exist

Two trajectories used JSON-LD without any SPARQL:
1. `vocab-obs-to-sensor-properties` (js-jsonld 16:01): `fetchJsonLd` + `jsonld.expand` + in-memory filter. 4 iterations, score = 1.
2. `vocab-sio-inverse-chain` (js-combined 16:06): `fetchJsonLd` + `jsonld.expand` + substring filter on `@id`. 7 iterations (many no-op), score = 1.

Both are on the small ontology subset and involve IRI-substring or type-based filtering rather than full-text search. These represent the ideal JSON-LD path: fetch once, expand, filter, return.

---

## Conclusion

The natural boundary between JSON-LD navigation and SPARQL querying is **ontology scale and IRI transparency**, not task type. For schema tasks on small ontologies with readable IRIs (SOSA), JSON-LD is the efficient choice. For schema tasks on large or numeric-IRI ontologies (SIO full graph), SPARQL with label search is more reliable. The agent's actual behavior — switching when one tool returns empty or errors — closely tracks this boundary. The main failure mode is the JSON parse truncation error for large ontologies, which pushes all large-ontology schema tasks back toward SPARQL as the reliable fallback.
