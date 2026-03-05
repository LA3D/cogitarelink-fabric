# RLM-Fabric Integration Design

**Date**: 2026-02-22
**Status**: Approved
**Scope**: Phase 1 Week 3-4 — `discover_endpoint` + `query_endpoint` + integration test

---

## Context

The fabric node's self-description layer is complete (13 HURL tests green):
- `/.well-known/void` — VoID SD with `dct:conformsTo` + `void:vocabulary`
- `/.well-known/profile` — CoreProfile PROF (7 ResourceDescriptors, 5 roles)
- `/.well-known/shacl` — Endpoint SHACL shapes with `sh:agentInstruction`
- `/.well-known/sparql-examples` — SIB spex: pattern

An RLM agent needs tools to consume this self-description and query the endpoint. This design covers those tools.

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Tool location | cogitarelink-fabric repo (`agents/`) | Keeps consumer next to provider |
| Discovery timing | Pre-REPL loading | Matches rdfs_instruct pattern: scaffolding loaded before iteration 1 |
| Output format | Dataclass with `.routing_plan` text | Structured fields for tool config; text rendering for RLM input |
| Query tool | Standalone httpx (sync) | No rlm_runtime dependency; REPL is sync; swap to sparqlx later if needed |
| Test criteria | Agent returns correct answer | End-to-end: insert data, discover, RLM query, verify answer |

---

## Module Structure

```
agents/
  __init__.py
  fabric_discovery.py    # discover_endpoint() -> FabricEndpoint
  fabric_query.py        # make_fabric_query_tool() -> Callable
  fabric_agent.py        # run_fabric_query() -> FabricQueryResult

tests/
  pytest/
    integration/
      test_fabric_discovery.py   # Tier 1: Docker stack only
      test_fabric_query.py       # Tier 2: Docker stack only
      test_fabric_agent.py       # Tier 3: Docker stack + LLM API
```

**Dependencies:**
- `fabric_discovery.py` -> httpx, rdflib (no dspy)
- `fabric_query.py` -> httpx (no dspy)
- `fabric_agent.py` -> dspy, imports discovery + query

All use `~/uvws/.venv` (rdflib 7.6, dspy 3.1, sparqlx 0.10, httpx 0.28).

---

## Layer 1: `fabric_discovery.py`

### Data Types

```python
@dataclass
class ShapeSummary:
    name: str                      # shape local name
    target_class: str              # sh:targetClass
    agent_instruction: str | None  # sh:agentInstruction
    properties: list[str]          # sh:path local names

@dataclass
class ExampleSummary:
    label: str          # rdfs:label
    comment: str        # rdfs:comment
    sparql: str         # sh:select content
    target: str         # schema:target endpoint

@dataclass
class FabricEndpoint:
    base: str                        # e.g. "http://localhost:8080"
    sparql_url: str                  # e.g. "http://localhost:8080/sparql"
    void_ttl: str                    # raw VoID Turtle
    profile_ttl: str                 # raw CoreProfile Turtle
    shapes_ttl: str                  # raw SHACL Turtle
    examples_ttl: str                # raw SPARQL examples Turtle
    vocabularies: list[str]          # void:vocabulary IRIs
    conforms_to: str                 # dct:conformsTo IRI
    shapes: list[ShapeSummary]       # parsed from SHACL
    examples: list[ExampleSummary]   # parsed from spex:

    @property
    def routing_plan(self) -> str:
        """Agent-readable text: endpoint, vocabs, shapes, examples."""
```

### Discovery Flow

`discover_endpoint(url: str) -> FabricEndpoint`:

1. GET `{url}/.well-known/void` (Accept: text/turtle) -> parse with rdflib
2. Extract `void:sparqlEndpoint`, `void:vocabulary` list, `dct:conformsTo`
3. GET `{url}/.well-known/profile` -> store raw
4. GET `{url}/.well-known/shacl` -> parse shapes into ShapeSummary list
5. GET `{url}/.well-known/sparql-examples` -> parse into ExampleSummary list
6. Return `FabricEndpoint`

### Routing Plan Output

The `.routing_plan` property renders a text summary like:

```
Endpoint: http://localhost:8080
SPARQL: http://localhost:8080/sparql
Profile: https://w3id.org/cogitarelink/fabric#CoreProfile

Vocabularies:
  - sosa: <http://www.w3.org/ns/sosa/>
  - time: <http://www.w3.org/2006/time#>

Shapes (2):
  ObservationShape -> sosa:Observation
    Properties: observedProperty, hasSimpleResult, resultTime, ...
    Agent hint: "Use sosa:hasSimpleResult for literal values..."

SPARQL Examples (2):
  "List recent observations" -> /sparql
    PREFIX sosa: ...
    SELECT ?obs ?result ?time WHERE { ... }
  "Observations by sensor" -> /sparql
    ...
```

---

## Layer 2: `fabric_query.py`

```python
def make_fabric_query_tool(ep: FabricEndpoint, max_chars: int = 10_000) -> Callable:
    """Returns a sparql_query(query) function bound to the endpoint."""
    def sparql_query(query: str) -> str:
        """Execute SPARQL SELECT/ASK/CONSTRUCT against the fabric endpoint.
        Returns JSON results (truncated to ~10k chars).
        On error, returns error description string."""
        try:
            r = httpx.post(
                ep.sparql_url,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30.0,
            )
            r.raise_for_status()
            txt = r.text
            if len(txt) > max_chars:
                return txt[:max_chars] + f"\n... truncated ({len(txt)} total chars)"
            return txt
        except Exception as e:
            return f"SPARQL error: {e}"
    return sparql_query
```

Key properties:
- Sync (dspy.RLM REPL is sync)
- Bounded output (10k chars default)
- Errors surfaced as strings (agent can adapt, not crash)

---

## Layer 3: `fabric_agent.py`

```python
@dataclass
class FabricQueryResult:
    answer: str
    sparql: str | None          # last SPARQL the agent executed
    sources: list[str]          # named graphs consulted
    iterations: int
    converged: bool

class FabricQuery(dspy.Signature):
    """Navigate a fabric endpoint using its self-description to answer a query."""
    endpoint_sd: str = dspy.InputField(desc="Endpoint self-description")
    query: str = dspy.InputField(desc="Natural language question")
    answer: str = dspy.OutputField(desc="Answer with supporting evidence")
    sparql_used: str = dspy.OutputField(desc="SPARQL query that produced the answer")
    sources: list[str] = dspy.OutputField(desc="Named graphs consulted")

def run_fabric_query(
    ep: FabricEndpoint,
    query: str,
    *,
    model: str = "anthropic/claude-sonnet-4-6",
    max_iterations: int = 10,
    max_llm_calls: int = 20,
    verbose: bool = False,
) -> FabricQueryResult:
```

Flow:
1. `make_fabric_query_tool(ep)` -> sparql_query tool
2. `dspy.configure(lm=dspy.LM(model))`
3. `dspy.RLM(FabricQuery, tools=[sparql_query], ...)`
4. Call with `endpoint_sd=ep.routing_plan, query=query`
5. Map result to `FabricQueryResult`

No memory, MLflow, or trajectory logging. Phase 1 minimal.

---

## Testing Strategy

### Tier 1: Discovery (Docker stack only)

```python
def test_discover_endpoint():
    ep = discover_endpoint("http://localhost:8080")
    assert ep.sparql_url == "http://localhost:8080/sparql"
    assert "http://www.w3.org/ns/sosa/" in ep.vocabularies
    assert len(ep.shapes) > 0
    assert len(ep.examples) > 0

def test_routing_plan_readable():
    ep = discover_endpoint("http://localhost:8080")
    plan = ep.routing_plan
    assert "sosa:Observation" in plan
    assert "SPARQL" in plan

def test_discover_bad_endpoint():
    with pytest.raises(httpx.ConnectError):
        discover_endpoint("http://localhost:9999")
```

### Tier 2: Query Tool (Docker stack only)

```python
def test_sparql_query_tool():
    ep = discover_endpoint("http://localhost:8080")
    query_fn = make_fabric_query_tool(ep)
    result = query_fn("SELECT ?s WHERE { ?s a <http://www.w3.org/ns/sosa/Observation> } LIMIT 1")
    assert "results" in result or "bindings" in result

def test_sparql_error_surfaced():
    ep = discover_endpoint("http://localhost:8080")
    query_fn = make_fabric_query_tool(ep)
    result = query_fn("NOT VALID SPARQL")
    assert "error" in result.lower()
```

### Tier 3: Agent End-to-End (Docker stack + LLM API)

```python
@pytest.mark.slow
@pytest.mark.llm
def test_agent_answers_from_self_description():
    insert_test_observation(temp=23.5, sensor="sensor-1")
    ep = discover_endpoint("http://localhost:8080")
    result = run_fabric_query(ep, "What temperature did sensor-1 measure?")
    assert "23.5" in result.answer
    assert result.sparql is not None
```

**Markers:** `@pytest.mark.slow` + `@pytest.mark.llm` — Tier 3 runs only with `pytest -m llm`. Tiers 1-2 run in normal CI.

---

## Success Criteria (from PLAN.md)

- [ ] RLM `discover_endpoint` implements full four-layer loading
- [ ] Agent constructs and executes valid SPARQL using only endpoint self-description
- [ ] SHACL validation rejects malformed assertions
- [ ] Performance target: ~4 iterations on SOSA tasks (Experiment 9 SH-I condition)

---

## Deferred

- Memory integration (ReasoningBank, curriculum retrieval)
- MLflow/Phoenix observability
- Trajectory logging
- Ref handle pattern (bounded result handles from rlm_runtime)
- Multi-endpoint map-reduce
- VC-based authentication (Phase 2)
