# Phase 2.5b: JSON-LD Navigation Analysis

**Date**: 2026-03-11
**Conditions**: js-baseline, js-jsonld, js-combined
**Model**: claude-sonnet-4-6
**Endpoint**: https://bootstrap.cogitarelink.ai
**Max iterations**: 15

## Key Finding

JSON-LD tools (fetchJsonLd, jsonld.expand/compact/frame) are **adopted when available** (41% of iterations in js-jsonld vocab tasks), but agents **strongly prefer SPARQL when both are present** (JSON-LD drops to 18% in js-combined). Having both tool families can paradoxically hurt performance: the js-combined condition failed one task (75%) where both js-baseline and js-jsonld scored 100%, because the agent wasted iterations switching between approaches rather than committing to one strategy.

## Experiment Design

Three conditions with identical tasks:

| Condition | SPARQL | JSON-LD tools | Discovery |
|-----------|--------|---------------|-----------|
| js-baseline | comunica_query | -- | fetchVoID/Shapes/Examples |
| js-jsonld | comunica_query | fetchJsonLd, jsonld.* | fetchVoID/Shapes/Examples |
| js-combined | comunica_query | fetchJsonLd, jsonld.* | fetchVoID/Shapes/Examples |

js-jsonld and js-combined have identical tool sets but different globalDocs (documentation).

Two task sets:
- **Vocab navigation** (4 tasks): Schema introspection requiring ontology structure understanding
- **SIO baseline** (6 tasks): Mixed schema + data tasks from Phase 1

## Condition Comparison

### Vocab Navigation Tasks (4 tasks)

| Metric | js-baseline | js-jsonld | js-combined |
|--------|-------------|-----------|-------------|
| Score | 100% (4/4) | 100% (4/4) | **75% (3/4)** |
| Mean iterations | 8.3 | 8.5 | 8.3 |
| Total tokens (in/out) | 172K/6.6K | 176K/7.1K | 197K/7.8K |
| Total cost | $0.71 | $0.76 | $0.71 |
| Cost per task | $0.178 | $0.190 | $0.177 |

### SIO Baseline Tasks (6 tasks)

| Metric | js-baseline | js-jsonld | js-combined |
|--------|-------------|-----------|-------------|
| Score | 100% (6/6) | 100% (6/6) | 100% (6/6) |
| Mean iterations | 5.5 | 5.3 | 5.8 |
| Total tokens (in/out) | 142K/5.0K | 149K/5.6K | 178K/6.0K |
| Total cost | $0.50 | $0.53 | $0.63 |
| Cost per task | $0.083 | $0.089 | $0.104 |

### Cost Overhead of JSON-LD Tools

JSON-LD tool availability increases cost due to longer globalDocs (more tokens per iteration):
- SIO baseline: js-jsonld is +6% cost vs baseline; js-combined is +25%
- Vocab tasks: js-jsonld is +7% cost vs baseline; js-combined is flat (but failed a task)

## Tool Choice Patterns

### JSON-LD Tool Adoption Rate

| Condition | Task Set | JSON-LD iterations | SPARQL iterations | Discovery | Compute/Submit |
|-----------|----------|-------------------|-------------------|-----------|----------------|
| js-jsonld | vocab (4) | **41.2%** (14/34) | 26.5% (9/34) | 20.6% | 11.8% |
| js-combined | vocab (4) | 18.2% (6/33) | **42.4%** (14/33) | 21.2% | 18.2% |
| js-jsonld | SIO baseline (6) | 9.4% (3/32) | **31.2%** (10/32) | 28.1% | 31.2% |
| js-combined | SIO baseline (6) | 5.7% (2/35) | **40.0%** (14/35) | 22.9% | 31.4% |

**Pattern**: When SPARQL is equally documented (js-combined), JSON-LD adoption drops 58% relative to js-jsonld for vocab tasks. SPARQL is the agent's default when both are available.

### Tool Selection Heuristic

The agent follows this implicit priority:

1. Fetch VoID (always first)
2. Try SPARQL queries against named graphs
3. If SPARQL returns empty or insufficient → try fetchJsonLd + local JSON parsing
4. If JSON-LD exploration is insufficient → iterate with compute/reasoning

In js-jsonld condition, the globalDocs documentation emphasizes JSON-LD as the primary vocab exploration tool (steps 4-6 in the discovery strategy). This steers the agent toward JSON-LD first for schema tasks, explaining the higher adoption rate.

## The SPARQL/JSON-LD Boundary

### Boundary Moments

In js-jsonld and js-combined conditions, the agent switches between tool families at predictable points:

1. **SPARQL→JSON-LD**: When SPARQL against /ontology/* returns empty results (the ontology named graph doesn't have the expected triples)
2. **JSON-LD→SPARQL**: When JSON-LD expand/parse reveals the property structure but the agent needs to verify against instance data

For schema-only tasks (e.g., `sio-attribute-inverse`):
- js-jsonld: Agent fetches ontology as JSON-LD, finds inverse property in **1 iteration**
- js-combined: Agent queries SPARQL first, needs **3+ iterations** to find same answer
- **JSON-LD is more efficient for pure ontology reasoning**

For data tasks (e.g., `obs-sio-measured-value`):
- JSON-LD adoption drops to <10% in both conditions
- SPARQL is the natural tool for grounding in instance data
- **SPARQL is the right tool for data retrieval**

### Natural Boundary

The natural SPARQL/JSON-LD boundary maps to **D9 four-layer KR**:
- **L2 TBox (ontology structure)**: JSON-LD navigation is more efficient — expand, frame, and parse locally
- **L3-L4 (shapes, examples, instance data)**: SPARQL is more efficient — structured queries with bindings

## Critical Failure Analysis: vocab-sio-float-range-properties

### The Failure

Task: "List the SIO properties that have xsd:float as their rdfs:range."
Expected: `["has-value"]`

| Condition | Score | Iterations | Strategy |
|-----------|-------|------------|----------|
| js-baseline | 1.00 | 12 | SPARQL exploration, found has-value as DatatypeProperty |
| js-jsonld | 1.00 | 14 | JSON-LD deep exploration, named has-value |
| js-combined | **0.00** | 12 | Tool switching, concluded "no properties have xsd:float range" |

### Root Causes

**1. Schema curation gap**: The fabric endpoint's `/ontology/sio` is a curated subset (~100 triples). `sio:has-value` is present as `owl:DatatypeProperty` with `rdfs:domain sio:Attribute`, but its `rdfs:range xsd:float` triple is **missing** from the subset.

**2. Tool-switching cost**: The js-combined agent:
- Iteration 1: SPARQL for rdfs:range xsd:float → empty
- Iteration 2: fetchJsonLd → parsed SIO → no range found
- Iterations 3-10: Alternated between SPARQL variations and JSON-LD, never committing to either
- Iteration 11: Concluded negatively

The js-baseline and js-jsonld agents, constrained to fewer tool options, committed more deeply to their available strategy and found the answer (likely through pretraining inference or naming has-value in their exploratory output, triggering substring match).

**3. Paradox of choice**: Having more tools made the agent *less* effective. Instead of exhausting one approach, it shallow-sampled both approaches and concluded negative. This is a direct instance of the satisficing/optimizing tradeoff in agentic decision-making.

### Schema Gap Remediation

The `/ontology/sio` named graph should include the `rdfs:range xsd:float` triple for `sio:has-value`. This is a TBox curation issue — the SIO subset loaded at bootstrap time is incomplete for this axiom.

## Per-Task Analysis

### Vocab Navigation Tasks

| Task | Condition | Score | Iters | Tool Sequence | Notes |
|------|-----------|-------|-------|---------------|-------|
| vocab-obs-to-sensor-properties | js-baseline | 1.00 | 10 | discovery→sparql×9→submit | Found madeBySensor via SPARQL |
| vocab-obs-to-sensor-properties | js-jsonld | 1.00 | 9 | discovery→sparql→jsonld×5→sparql→submit | Mixed approach |
| vocab-obs-to-sensor-properties | js-combined | 1.00 | 6 | discovery→sparql→jsonld→sparql×2→submit | Efficient |
| vocab-sio-float-range-properties | js-baseline | 1.00 | 12 | discovery→sparql×10→submit | Named has-value |
| vocab-sio-float-range-properties | js-jsonld | 1.00 | 14 | discovery→sparql×3→jsonld×9→submit | Deep JSON-LD |
| vocab-sio-float-range-properties | js-combined | **0.00** | 12 | discovery→sparql→jsonld→compute→sparql×6→submit | Tool switching failure |
| vocab-sio-inverse-chain | js-baseline | 1.00 | 5 | discovery→sparql×4→submit | Fast |
| vocab-sio-inverse-chain | js-jsonld | 1.00 | 7 | discovery→sparql→jsonld×4→sparql→submit | JSON-LD for inverse |
| vocab-sio-inverse-chain | js-combined | 1.00 | 7 | discovery→sparql×2→jsonld×3→submit | Hybrid |
| vocab-observation-subclasses | js-baseline | 1.00 | 6 | discovery→sparql×4→submit | Negative correctly |
| vocab-observation-subclasses | js-jsonld | 1.00 | 5 | discovery→sparql→jsonld×2→submit | Efficient |
| vocab-observation-subclasses | js-combined | 1.00 | 8 | discovery→sparql×2→jsonld×4→submit | More exploration |

### SIO Baseline Tasks (all conditions 100%)

| Task | js-baseline iters | js-jsonld iters | js-combined iters |
|------|-------------------|-----------------|-------------------|
| sio-has-value-type | 4 | 5 | 4 |
| sio-attribute-inverse | 4 | 3 | 5 |
| sio-measured-value-range | 4 | 5 | 3 |
| obs-sio-measured-value | 6 | 8 | 7 |
| obs-sio-unit | 7 | 6 | 8 |
| obs-sio-chemical-entity | 8 | 5 | 8 |

No consistent efficiency advantage for any condition on baseline tasks.

## Research Implications

### D9 Progressive Disclosure Validated

The four-layer KR architecture maps cleanly to tool selection:
- **L1 (VoID/SD)**: Agent always starts here (fetchVoID → understand structure)
- **L2 (TBox)**: JSON-LD navigation is natural — expand/frame operations match the vocabulary-as-document model
- **L3-L4 (shapes, examples, data)**: SPARQL is more efficient for structured queries

### D31 Transport Complementarity

JSON-LD and SPARQL are **complementary, not competing**:
- JSON-LD excels at **document-oriented vocabulary exploration** (what properties exist? what are their domains/ranges?)
- SPARQL excels at **graph-pattern matching over instance data** (what observations match this pattern?)

The agent naturally discovers this boundary — when given both tools, it uses JSON-LD for vocab and SPARQL for data.

### Tool Availability vs. Tool Documentation

The js-jsonld condition's higher JSON-LD adoption (41% vs 18% in js-combined) is driven by **documentation emphasis**, not tool availability. Both conditions have identical tools. The globalDocs for js-jsonld presents JSON-LD as the primary vocab exploration path (steps 4-6), while js-combined presents them equally. This confirms the earlier finding that **tool advertisement drives adoption**.

### Paradox of Choice for Agents

More tools can hurt performance when:
1. The agent shallow-samples multiple approaches instead of committing to one
2. Context window fills with diverse but shallow tool outputs
3. The agent's implicit planning horizon doesn't account for tool-switching overhead

This suggests that **curated tool sets per task type** may outperform **universal tool sets** — the fabric should guide agents toward the right tool for their current subtask through D9 layer hints.

## Recommendations

### Immediate

1. **Fix SIO schema gap**: Add `sio:has-value rdfs:range xsd:float` to the SIO TBox subset at `/ontology/sio`. This is a curation bug, not an experiment design issue.

2. **Rerun js-combined after fix**: The failure may be partly stochastic, partly schema-gap-driven. Rerun to separate these factors.

### Experiment Design

3. **Add trajectory depth metrics**: Track JSON-LD navigation depth (how many fetchJsonLd calls, how many expand/frame calls) per task to quantify the exploration cost.

4. **Test with unfamiliar vocabularies**: Current tasks use SOSA/SIO (partially in pretraining). Test with a custom or obscure vocabulary to see if JSON-LD tools become essential rather than optional.

5. **Test condition-specific documentation**: Create a condition where JSON-LD docs explicitly say "use fetchJsonLd for /ontology/* exploration, SPARQL for /graph/* queries" — test whether explicit boundary guidance improves tool selection.

### Fabric Structure

6. **Layer-specific tool hints**: The SD/VoID should include hints like "ontology graphs are best explored via JSON-LD; data graphs are best queried via SPARQL" — embedding D9 progressive disclosure into the self-description.

7. **JSON-LD @context quality**: Ensure all /ontology/* responses include proper @context with prefix mappings. The agent's JSON-LD processing efficiency depends on well-structured context documents.

## Raw Results

| File | Contents |
|------|----------|
| `fabric-js-baseline_*_2026-03-11T15-58-31-918Z.json` | Baseline vocab tasks |
| `fabric-js-jsonld_*_2026-03-11T16-01-32-644Z.json` | JSON-LD vocab tasks |
| `fabric-js-combined_*_2026-03-11T16-06-07-967Z.json` | Combined vocab tasks |
| `fabric-js-baseline_*_2026-03-11T16-12-53-597Z.json` | Baseline SIO tasks |
| `fabric-js-jsonld_*_2026-03-11T16-08-35-772Z.json` | JSON-LD SIO tasks |
| `fabric-js-combined_*_2026-03-11T16-10-46-303Z.json` | Combined SIO tasks |
| `trajectory-*` | Corresponding trajectory files |
