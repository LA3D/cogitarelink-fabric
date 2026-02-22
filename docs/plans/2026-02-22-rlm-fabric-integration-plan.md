# RLM-Fabric Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build `discover_endpoint` + SPARQL query tool + RLM agent orchestration so an agent can navigate a fabric node using only its `.well-known/` self-description.

**Architecture:** Three Python modules in `agents/` (discovery, query, agent) with layered dependencies. Discovery and query have no dspy dependency. Agent layer wires them together with `dspy.RLM`. Pre-REPL loading: discover_endpoint runs before the RLM loop, passing a text routing plan as input.

**Tech Stack:** Python 3.12, httpx 0.28, rdflib 7.6, dspy 3.1. All from `~/uvws/.venv`. Docker stack must be running for integration tests.

**Design doc:** `docs/plans/2026-02-22-rlm-fabric-integration-design.md`

---

## Prerequisites

- Docker stack running: `docker compose up -d` (from cogitarelink-fabric root)
- All 13 HURL tests passing: `hurl --test --variable gateway=http://localhost:8080 --variable oxigraph=http://localhost:7878 tests/hurl/phase1/*.hurl`
- Python: `~/uvws/.venv/bin/python` (3.12.8 with rdflib, httpx, dspy)

---

### Task 1: Create agents/ package skeleton

**Files:**
- Create: `agents/__init__.py`
- Create: `agents/fabric_discovery.py` (empty placeholder)
- Create: `agents/fabric_query.py` (empty placeholder)
- Create: `agents/fabric_agent.py` (empty placeholder)
- Create: `tests/pytest/integration/__init__.py`

**Step 1: Create directory structure**

```bash
mkdir -p agents tests/pytest/integration
touch agents/__init__.py agents/fabric_discovery.py agents/fabric_query.py agents/fabric_agent.py
touch tests/pytest/integration/__init__.py
```

**Step 2: Verify imports work**

Run: `~/uvws/.venv/bin/python -c "import agents"`
Expected: No error

**Step 3: Commit**

```bash
git add agents/ tests/pytest/integration/__init__.py
git commit -m "feat: agents/ package skeleton for RLM-fabric integration"
```

---

### Task 2: Dataclasses — ShapeSummary, ExampleSummary, FabricEndpoint

**Files:**
- Create: `tests/pytest/integration/test_fabric_discovery.py` (first test)
- Modify: `agents/fabric_discovery.py`

**Step 1: Write the failing test**

Write to `tests/pytest/integration/test_fabric_discovery.py`:

```python
"""Tier 1 integration tests: fabric endpoint discovery (Docker stack only)."""
import pytest
from agents.fabric_discovery import ShapeSummary, ExampleSummary, FabricEndpoint


def test_fabric_endpoint_routing_plan_contains_basics():
    """FabricEndpoint.routing_plan renders endpoint, vocabs, shapes, examples."""
    ep = FabricEndpoint(
        base="http://localhost:8080",
        sparql_url="http://localhost:8080/sparql",
        void_ttl="",
        profile_ttl="",
        shapes_ttl="",
        examples_ttl="",
        vocabularies=["http://www.w3.org/ns/sosa/", "http://www.w3.org/2006/time#"],
        conforms_to="https://w3id.org/cogitarelink/fabric#CoreProfile",
        shapes=[
            ShapeSummary(
                name="ObservationShape",
                target_class="sosa:Observation",
                agent_instruction="Query /graph/observations for sosa:Observation instances.",
                properties=["hasSimpleResult", "resultTime", "observedProperty"],
            )
        ],
        examples=[
            ExampleSummary(
                label="List recent observations",
                comment="Returns observations ordered by time.",
                sparql="SELECT ?obs WHERE { ?obs a sosa:Observation }",
                target="http://localhost:8080/sparql",
            )
        ],
    )
    plan = ep.routing_plan
    assert "http://localhost:8080" in plan
    assert "sosa" in plan.lower()
    assert "ObservationShape" in plan
    assert "List recent observations" in plan
    assert "CoreProfile" in plan
```

**Step 2: Run test to verify it fails**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_discovery.py::test_fabric_endpoint_routing_plan_contains_basics -v`
Expected: FAIL with `ImportError` (classes don't exist yet)

**Step 3: Write minimal implementation**

Write to `agents/fabric_discovery.py`:

```python
"""Fabric endpoint discovery — four-layer KR loading (D9)."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ShapeSummary:
    name: str
    target_class: str
    agent_instruction: str | None
    properties: list[str] = field(default_factory=list)


@dataclass
class ExampleSummary:
    label: str
    comment: str
    sparql: str
    target: str


@dataclass
class FabricEndpoint:
    base: str
    sparql_url: str
    void_ttl: str
    profile_ttl: str
    shapes_ttl: str
    examples_ttl: str
    vocabularies: list[str] = field(default_factory=list)
    conforms_to: str = ""
    shapes: list[ShapeSummary] = field(default_factory=list)
    examples: list[ExampleSummary] = field(default_factory=list)

    @property
    def routing_plan(self) -> str:
        lines = [
            f"Endpoint: {self.base}",
            f"SPARQL: {self.sparql_url}",
            f"Profile: {self.conforms_to}",
            "",
            "Vocabularies:",
        ]
        for v in self.vocabularies:
            # Extract short prefix from IRI
            short = v.rstrip("/#").rsplit("/", 1)[-1]
            lines.append(f"  - {short}: <{v}>")

        lines.append("")
        lines.append(f"Shapes ({len(self.shapes)}):")
        for s in self.shapes:
            lines.append(f"  {s.name} -> {s.target_class}")
            if s.properties:
                lines.append(f"    Properties: {', '.join(s.properties)}")
            if s.agent_instruction:
                lines.append(f"    Agent hint: {s.agent_instruction}")

        lines.append("")
        lines.append(f"SPARQL Examples ({len(self.examples)}):")
        for e in self.examples:
            lines.append(f'  "{e.label}" -> {e.target}')
            lines.append(f"    {e.comment}")
            # Include the actual SPARQL so the agent can adapt it
            for sparql_line in e.sparql.strip().splitlines():
                lines.append(f"    {sparql_line}")

        return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_discovery.py::test_fabric_endpoint_routing_plan_contains_basics -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/fabric_discovery.py tests/pytest/integration/test_fabric_discovery.py
git commit -m "feat: FabricEndpoint dataclass with routing_plan rendering"
```

---

### Task 3: discover_endpoint() — four-layer HTTP loading + RDF parsing

**Files:**
- Modify: `tests/pytest/integration/test_fabric_discovery.py` (add tests)
- Modify: `agents/fabric_discovery.py` (add discover_endpoint)

**Step 1: Write the failing tests**

Append to `tests/pytest/integration/test_fabric_discovery.py`:

```python
import httpx
from agents.fabric_discovery import discover_endpoint

GATEWAY = "http://localhost:8080"


def test_discover_endpoint():
    """discover_endpoint returns FabricEndpoint with all four layers populated."""
    ep = discover_endpoint(GATEWAY)
    assert ep.base == GATEWAY
    assert ep.sparql_url == f"{GATEWAY}/sparql"
    assert "http://www.w3.org/ns/sosa/" in ep.vocabularies
    assert "http://www.w3.org/2006/time#" in ep.vocabularies
    assert "CoreProfile" in ep.conforms_to
    assert len(ep.void_ttl) > 0
    assert len(ep.profile_ttl) > 0
    assert len(ep.shapes_ttl) > 0
    assert len(ep.examples_ttl) > 0


def test_discover_parses_shapes():
    """discover_endpoint extracts ShapeSummary from SHACL."""
    ep = discover_endpoint(GATEWAY)
    assert len(ep.shapes) >= 1
    obs_shape = next((s for s in ep.shapes if "Observation" in s.target_class), None)
    assert obs_shape is not None
    assert obs_shape.agent_instruction is not None
    assert len(obs_shape.properties) >= 1


def test_discover_parses_examples():
    """discover_endpoint extracts ExampleSummary from spex: catalog."""
    ep = discover_endpoint(GATEWAY)
    assert len(ep.examples) >= 1
    assert any("observation" in e.label.lower() for e in ep.examples)
    assert all(e.sparql.strip() for e in ep.examples)


def test_routing_plan_readable():
    """routing_plan contains shapes, examples, vocabularies from live endpoint."""
    ep = discover_endpoint(GATEWAY)
    plan = ep.routing_plan
    assert "sosa" in plan.lower()
    assert "SPARQL" in plan
    assert "Observation" in plan


def test_discover_bad_endpoint():
    """Non-existent endpoint raises ConnectError."""
    with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
        discover_endpoint("http://localhost:9999")
```

**Step 2: Run tests to verify they fail**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_discovery.py -v -k "not routing_plan_contains_basics"`
Expected: FAIL with `ImportError` (discover_endpoint not defined)

**Step 3: Write minimal implementation**

Add to `agents/fabric_discovery.py` (after the dataclasses):

```python
import httpx
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS

VOID = Namespace("http://rdfs.org/ns/void#")
SH = Namespace("http://www.w3.org/ns/shacl#")
SPEX = Namespace("https://purl.expasy.org/sparql-examples/ontology#")
SDO = Namespace("https://schema.org/")


def _fetch(url: str, accept: str = "text/turtle") -> str:
    r = httpx.get(url, headers={"Accept": accept}, timeout=10.0)
    r.raise_for_status()
    return r.text


def _parse_void(ttl: str) -> tuple[str, list[str], str]:
    """Extract sparql_url, vocabularies, conforms_to from VoID Turtle."""
    g = Graph()
    g.parse(data=ttl, format="turtle")
    sparql_url = ""
    vocabs = []
    conforms = ""
    for s in g.subjects(RDF.type, VOID.Dataset):
        for o in g.objects(s, VOID.sparqlEndpoint):
            sparql_url = str(o)
        for o in g.objects(s, VOID.vocabulary):
            vocabs.append(str(o))
        for o in g.objects(s, DCTERMS.conformsTo):
            conforms = str(o)
    return sparql_url, vocabs, conforms


def _parse_shapes(ttl: str) -> list[ShapeSummary]:
    g = Graph()
    g.parse(data=ttl, format="turtle")
    shapes = []
    for s in g.subjects(RDF.type, SH.NodeShape):
        name = str(s).rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        tc = ""
        for o in g.objects(s, SH.targetClass):
            tc = _compact(str(o))
        instr = None
        for o in g.objects(s, SH.agentInstruction):
            instr = str(o)
        props = []
        for prop_node in g.objects(s, SH.property):
            for path in g.objects(prop_node, SH.path):
                props.append(_compact(str(path)))
        shapes.append(ShapeSummary(name=name, target_class=tc,
                                   agent_instruction=instr, properties=props))
    return shapes


def _parse_examples(ttl: str) -> list[ExampleSummary]:
    g = Graph()
    g.parse(data=ttl, format="turtle")
    examples = []
    for s in g.subjects(RDF.type, SPEX.SPARQLExecutable):
        label = str(g.value(s, RDFS.label) or "")
        comment = str(g.value(s, RDFS.comment) or "")
        sparql = str(g.value(s, SH.select) or "")
        target = str(g.value(s, SDO.target) or "")
        if sparql:
            examples.append(ExampleSummary(label=label, comment=comment,
                                           sparql=sparql, target=target))
    return examples


def _compact(iri: str) -> str:
    """Shorten well-known IRIs to prefix:local form."""
    prefixes = {
        "http://www.w3.org/ns/sosa/": "sosa:",
        "http://www.w3.org/2006/time#": "time:",
        "http://www.w3.org/ns/shacl#": "sh:",
    }
    for ns, prefix in prefixes.items():
        if iri.startswith(ns):
            return prefix + iri[len(ns):]
    return iri


def discover_endpoint(url: str) -> FabricEndpoint:
    """Fetch all four D9 layers from a fabric node's .well-known/ endpoints.

    Args:
        url: Base URL of the fabric node (e.g. "http://localhost:8080")

    Returns:
        FabricEndpoint with structured fields and .routing_plan text
    """
    base = url.rstrip("/")

    void_ttl = _fetch(f"{base}/.well-known/void")
    sparql_url, vocabs, conforms = _parse_void(void_ttl)

    profile_ttl = _fetch(f"{base}/.well-known/profile")
    shapes_ttl = _fetch(f"{base}/.well-known/shacl")
    examples_ttl = _fetch(f"{base}/.well-known/sparql-examples")

    shapes = _parse_shapes(shapes_ttl)
    examples = _parse_examples(examples_ttl)

    return FabricEndpoint(
        base=base, sparql_url=sparql_url,
        void_ttl=void_ttl, profile_ttl=profile_ttl,
        shapes_ttl=shapes_ttl, examples_ttl=examples_ttl,
        vocabularies=vocabs, conforms_to=conforms,
        shapes=shapes, examples=examples,
    )
```

**Step 4: Run tests to verify they pass**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_discovery.py -v`
Expected: All 6 PASS

**Step 5: Commit**

```bash
git add agents/fabric_discovery.py tests/pytest/integration/test_fabric_discovery.py
git commit -m "feat: discover_endpoint with four-layer KR loading"
```

---

### Task 4: make_fabric_query_tool() — bounded SPARQL query function

**Files:**
- Create: `tests/pytest/integration/test_fabric_query.py`
- Modify: `agents/fabric_query.py`

**Step 1: Write the failing tests**

Write to `tests/pytest/integration/test_fabric_query.py`:

```python
"""Tier 2 integration tests: fabric SPARQL query tool (Docker stack only)."""
import json
from agents.fabric_discovery import discover_endpoint
from agents.fabric_query import make_fabric_query_tool

GATEWAY = "http://localhost:8080"


def test_sparql_query_tool_returns_json():
    """Tool executes SPARQL and returns JSON results."""
    ep = discover_endpoint(GATEWAY)
    query_fn = make_fabric_query_tool(ep)
    result = query_fn("SELECT * WHERE {} LIMIT 1")
    parsed = json.loads(result)
    assert "results" in parsed
    assert "bindings" in parsed["results"]


def test_sparql_query_with_sosa():
    """Tool can query SOSA vocabulary from TBox graph."""
    ep = discover_endpoint(GATEWAY)
    query_fn = make_fabric_query_tool(ep)
    result = query_fn(
        "PREFIX sosa: <http://www.w3.org/ns/sosa/> "
        "PREFIX owl: <http://www.w3.org/2002/07/owl#> "
        "ASK { GRAPH <http://localhost:8080/ontology/sosa> { sosa:Observation a owl:Class } }"
    )
    assert "true" in result.lower()


def test_sparql_error_surfaced_as_string():
    """Malformed SPARQL returns error string, not exception."""
    ep = discover_endpoint(GATEWAY)
    query_fn = make_fabric_query_tool(ep)
    result = query_fn("NOT VALID SPARQL")
    assert "error" in result.lower()


def test_sparql_result_bounded():
    """Results exceeding max_chars are truncated."""
    ep = discover_endpoint(GATEWAY)
    query_fn = make_fabric_query_tool(ep, max_chars=50)
    result = query_fn("SELECT * WHERE {} LIMIT 1")
    assert len(result) <= 200  # truncated + suffix message
```

**Step 2: Run tests to verify they fail**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_query.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Write to `agents/fabric_query.py`:

```python
"""Fabric SPARQL query tool factory — bounded, sync, error-surfacing."""
from __future__ import annotations
from typing import Callable
import httpx
from agents.fabric_discovery import FabricEndpoint


def make_fabric_query_tool(ep: FabricEndpoint, max_chars: int = 10_000) -> Callable:
    """Return a sparql_query(query) function bound to ep's SPARQL endpoint.

    The returned function is sync (for dspy.RLM REPL), bounded (truncates
    large results), and error-surfacing (returns error strings, not exceptions).
    """
    def sparql_query(query: str) -> str:
        """Execute SPARQL against the fabric endpoint. Returns JSON results.
        Results are truncated to ~10k chars. On error, returns error description."""
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
        except httpx.HTTPStatusError as e:
            return f"SPARQL error (HTTP {e.response.status_code}): {e.response.text[:500]}"
        except Exception as e:
            return f"SPARQL error: {e}"
    return sparql_query
```

**Step 4: Run tests to verify they pass**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_query.py -v`
Expected: All 4 PASS

**Step 5: Commit**

```bash
git add agents/fabric_query.py tests/pytest/integration/test_fabric_query.py
git commit -m "feat: make_fabric_query_tool with bounded sync SPARQL"
```

---

### Task 5: run_fabric_query() — dspy.RLM orchestration

**Files:**
- Create: `tests/pytest/integration/test_fabric_agent.py`
- Modify: `agents/fabric_agent.py`
- Modify: `tests/pytest/conftest.py` (add markers)

**Step 1: Register pytest markers**

Append to `tests/pytest/conftest.py`:

```python
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "llm: marks tests requiring LLM API key")
```

**Step 2: Write the failing test**

Write to `tests/pytest/integration/test_fabric_agent.py`:

```python
"""Tier 3 integration tests: RLM agent end-to-end (Docker stack + LLM API).

Run with: ~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_agent.py -v -m llm
Requires: ANTHROPIC_API_KEY set, Docker stack running.
"""
import pytest
import httpx
from agents.fabric_discovery import discover_endpoint
from agents.fabric_agent import run_fabric_query

GATEWAY = "http://localhost:8080"


def _insert_test_observation(temp: float, sensor: str) -> None:
    """Insert a known observation into the fabric node for testing."""
    sparql_update = f"""
    PREFIX sosa: <http://www.w3.org/ns/sosa/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT DATA {{
        GRAPH <{GATEWAY}/graph/observations> {{
            <{GATEWAY}/entity/test-obs-agent> a sosa:Observation ;
                sosa:madeBySensor <{GATEWAY}/entity/{sensor}> ;
                sosa:hasSimpleResult "{temp}"^^xsd:double ;
                sosa:resultTime "2026-02-22T12:00:00Z"^^xsd:dateTime .
        }}
    }}
    """
    r = httpx.post(
        f"{GATEWAY}/sparql/update",
        data={"update": sparql_update},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    r.raise_for_status()


def _cleanup_test_observation() -> None:
    sparql_update = f"""
    DROP SILENT GRAPH <{GATEWAY}/graph/observations>
    """
    httpx.post(
        f"{GATEWAY}/sparql/update",
        data={"update": sparql_update},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


@pytest.mark.slow
@pytest.mark.llm
def test_agent_answers_from_self_description():
    """End-to-end: insert data, discover endpoint, RLM query, verify answer."""
    try:
        _insert_test_observation(temp=23.5, sensor="sensor-1")
        ep = discover_endpoint(GATEWAY)
        result = run_fabric_query(
            ep, "What temperature did sensor-1 measure?", verbose=True,
        )
        assert "23.5" in result.answer
        assert result.sparql is not None
    finally:
        _cleanup_test_observation()
```

**Step 3: Run test to verify it fails**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_agent.py -v -m llm`
Expected: FAIL with `ImportError` (run_fabric_query not defined)

**Step 4: Write minimal implementation**

Write to `agents/fabric_agent.py`:

```python
"""Fabric agent orchestration — discover + query via dspy.RLM."""
from __future__ import annotations
from dataclasses import dataclass, field
import dspy
from agents.fabric_discovery import FabricEndpoint
from agents.fabric_query import make_fabric_query_tool


@dataclass
class FabricQueryResult:
    answer: str
    sparql: str | None = None
    sources: list[str] = field(default_factory=list)
    iterations: int = 0
    converged: bool = True


class FabricQuery(dspy.Signature):
    """Navigate a fabric endpoint using its self-description to answer a query.
    Use the endpoint's SHACL shapes and SPARQL examples as guides for
    constructing SPARQL queries. Execute queries with sparql_query()."""
    endpoint_sd: str = dspy.InputField(
        desc="Endpoint self-description: vocabularies, SHACL shapes with "
             "agent instructions, and SPARQL example queries")
    query: str = dspy.InputField(desc="Natural language question to answer")
    answer: str = dspy.OutputField(
        desc="Answer with supporting evidence from SPARQL results")
    sparql_used: str = dspy.OutputField(
        desc="The SPARQL query that produced the answer")
    sources: list[str] = dspy.OutputField(
        desc="Named graphs consulted")


def run_fabric_query(
    ep: FabricEndpoint,
    query: str,
    *,
    model: str = "anthropic/claude-sonnet-4-6",
    max_iterations: int = 10,
    max_llm_calls: int = 20,
    verbose: bool = False,
) -> FabricQueryResult:
    """Run an RLM agent against a fabric endpoint.

    Pre-loads the endpoint's self-description (four-layer KR), then
    launches a dspy.RLM REPL with a bound SPARQL query tool.

    Args:
        ep: FabricEndpoint from discover_endpoint()
        query: Natural language question
        model: LLM model identifier
        max_iterations: REPL turn budget
        max_llm_calls: Sub-LLM call budget
        verbose: Print REPL trace

    Returns:
        FabricQueryResult with answer, SPARQL used, and sources
    """
    sparql_query = make_fabric_query_tool(ep)

    dspy.configure(lm=dspy.LM(model))
    rlm = dspy.RLM(
        FabricQuery,
        tools=[sparql_query],
        max_iterations=max_iterations,
        max_llm_calls=max_llm_calls,
        verbose=verbose,
    )

    result = rlm(endpoint_sd=ep.routing_plan, query=query)

    return FabricQueryResult(
        answer=getattr(result, "answer", ""),
        sparql=getattr(result, "sparql_used", None),
        sources=getattr(result, "sources", []),
    )
```

**Step 5: Run test to verify it passes**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_agent.py -v -m llm`
Expected: PASS (requires ANTHROPIC_API_KEY in environment)

**Step 6: Commit**

```bash
git add agents/fabric_agent.py tests/pytest/integration/test_fabric_agent.py tests/pytest/conftest.py
git commit -m "feat: run_fabric_query RLM orchestration + end-to-end test"
```

---

### Task 6: Verify full test suite — no regressions

**Step 1: Run all HURL tests**

Run: `hurl --test --variable gateway=http://localhost:8080 --variable oxigraph=http://localhost:7878 tests/hurl/phase1/*.hurl`
Expected: 13/13 PASS

**Step 2: Run Tier 1+2 pytest (no LLM)**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/ -v -m "not llm"`
Expected: All PASS (existing 2 unit tests + 10 new integration tests)

**Step 3: Run Tier 3 pytest (LLM)**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_agent.py -v -m llm`
Expected: 1 PASS

**Step 4: Final commit with all tests green**

If any adjustments needed, fix and commit. Then:

```bash
git add -A  # only if all tracked, no secrets
git commit -m "chore: all tests green — RLM-fabric integration complete"
```

---

### Task 7: Update agents/__init__.py with public API

**Files:**
- Modify: `agents/__init__.py`

**Step 1: Write the failing test**

Add to `tests/pytest/integration/test_fabric_discovery.py`:

```python
def test_public_api_importable():
    """Public API is importable from agents package."""
    from agents import discover_endpoint, make_fabric_query_tool, run_fabric_query
    assert callable(discover_endpoint)
    assert callable(make_fabric_query_tool)
    assert callable(run_fabric_query)
```

**Step 2: Run test to verify it fails**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_discovery.py::test_public_api_importable -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Write to `agents/__init__.py`:

```python
"""cogitarelink-fabric agent tools — RLM integration with fabric endpoints."""
from agents.fabric_discovery import discover_endpoint, FabricEndpoint, ShapeSummary, ExampleSummary
from agents.fabric_query import make_fabric_query_tool
from agents.fabric_agent import run_fabric_query, FabricQueryResult
```

**Step 4: Run test to verify it passes**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_discovery.py::test_public_api_importable -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/__init__.py tests/pytest/integration/test_fabric_discovery.py
git commit -m "feat: agents/ public API exports"
```

---

## Summary

| Task | Module | Tests | Needs LLM? |
|---|---|---|---|
| 1 | Package skeleton | import check | No |
| 2 | Dataclasses + routing_plan | 1 unit test | No |
| 3 | discover_endpoint() | 5 integration tests | No |
| 4 | make_fabric_query_tool() | 4 integration tests | No |
| 5 | run_fabric_query() | 1 end-to-end test | Yes |
| 6 | Full regression check | 13 HURL + all pytest | Yes |
| 7 | Public API exports | 1 import test | No |

Total: 7 tasks, 12 new tests, 3 new modules.
