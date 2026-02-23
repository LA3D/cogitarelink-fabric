# analyze_rdfs_routes RLM Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Expose RDFS/OWL reasoning (PDDL-Instruct methodology) as a dspy.RLM REPL tool backed by `ep.tbox_graph`, enabling the fabric agent to derive SPARQL triple patterns from ontology axioms.

**Architecture:** `agents/fabric_rdfs_routes.py` adapts three functions from `ontology-agent-kr/experiments/rdfs_instruct/rdfs_instruct.py` (`RDFS_INSTRUCT_PATTERNS`, `extract_ontology_structure`, `build_rdfs_sub_agent_prompt`) into a factory `make_rdfs_routes_tool(ep)`. The factory pre-computes the ontology summary at creation time; each REPL call invokes `dspy.settings.lm` (the configured LLM) to run a reasoning sub-agent and return a routing analysis. The experiment runner is extended with `phase4a/4b` entries to measure whether the tool reduces iterations on SIO tasks.

**Tech Stack:** Python 3.12, rdflib 7.6, dspy 3.1 (rawwerks fork), httpx — no new dependencies.

---

## Context

`ep.tbox_graph` is an `rdflib.Graph | None` on `FabricEndpoint`, populated during `discover_endpoint()` with all ontology named graphs (`/ontology/sosa`, `/ontology/sio`, etc.) via SPARQL CONSTRUCT. Phase 3b experiments confirmed the TBox graph is present and queryable.

`rdfs_instruct.py` (in the sibling repo `ontology-agent-kr`) contains:
- `RDFS_INSTRUCT_PATTERNS` — 7 RDFS/OWL reasoning worked examples as a system prompt
- `extract_ontology_structure(g: Graph) -> str` — converts rdflib.Graph to routing-relevant text
- `build_rdfs_sub_agent_prompt(ont_summary, information_need, instance_context=None) -> str`

We copy (not import across repos) only these three into `agents/fabric_rdfs_routes.py` plus the tool factory.

The tool is callable from within the dspy.RLM REPL:
```python
analyze_rdfs_routes("What SPARQL pattern reaches sio:has-measurement-value rdfs:range?")
# → "ROUTING ANALYSIS:\n1. sio:has-measurement-value: domain=...\nROUTING PLAN: ..."
```

Inside the REPL, `analyze_rdfs_routes` calls `dspy.settings.lm` to run the sub-agent (not `llm_query()`, which is a REPL built-in unavailable from tool context).

---

## Task 1: Core Module + Unit Tests (TDD)

**Files:**
- Create: `agents/fabric_rdfs_routes.py`
- Create: `tests/pytest/unit/test_fabric_rdfs_routes.py`

---

### Step 1: Write failing tests

Create `tests/pytest/unit/test_fabric_rdfs_routes.py`:

```python
"""Unit tests for fabric_rdfs_routes — no Docker, no network."""
from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

from agents.fabric_discovery import FabricEndpoint


def _make_ep(tbox: Graph | None) -> FabricEndpoint:
    return FabricEndpoint(
        base="http://localhost:8080",
        sparql_url="http://localhost:8080/sparql",
        void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
        tbox_graph=tbox,
    )


def _tiny_tbox() -> Graph:
    """Minimal OWL graph: one ObjectProperty with domain/range."""
    g = Graph()
    SIO = "http://semanticscience.org/resource/"
    prop = URIRef(SIO + "has-attribute")
    obs  = URIRef("http://www.w3.org/ns/sosa/Observation")
    mv   = URIRef(SIO + "MeasuredValue")
    g.add((prop, RDF.type, OWL.ObjectProperty))
    g.add((prop, RDFS.domain, obs))
    g.add((prop, RDFS.range, mv))
    return g


# --- T1: factory with no tbox returns stub callable -------------------------

def test_no_tbox_returns_stub():
    from agents.fabric_rdfs_routes import make_rdfs_routes_tool
    ep = _make_ep(None)
    tool = make_rdfs_routes_tool(ep)
    result = tool("anything")
    assert "no" in result.lower() or "tbox" in result.lower() or "not available" in result.lower()


# --- T2: factory with tbox returns callable ----------------------------------

def test_with_tbox_returns_callable():
    from agents.fabric_rdfs_routes import make_rdfs_routes_tool
    ep = _make_ep(_tiny_tbox())
    tool = make_rdfs_routes_tool(ep)
    assert callable(tool)
    assert tool.__name__ == "analyze_rdfs_routes"


# --- T3: tool calls dspy.settings.lm with correct prompt structure ----------

def test_tool_calls_lm_with_rdfs_prompt():
    from agents.fabric_rdfs_routes import make_rdfs_routes_tool, RDFS_INSTRUCT_PATTERNS
    ep = _make_ep(_tiny_tbox())
    tool = make_rdfs_routes_tool(ep)

    mock_lm = MagicMock(return_value=["ROUTING PLAN: ?x sio:has-attribute ?mv ."])

    with patch("dspy.settings") as mock_settings:
        mock_settings.lm = mock_lm
        result = tool("What is the range of sio:has-attribute?")

    assert mock_lm.called
    call_kwargs = mock_lm.call_args
    # The prompt passed to LM must contain RDFS patterns and the information need
    messages = call_kwargs[1].get("messages") or call_kwargs[0][0]
    prompt_text = messages[0]["content"] if isinstance(messages, list) else str(messages)
    assert "RDFS" in prompt_text or "ROUTING" in prompt_text
    assert "sio:has-attribute" in prompt_text
    assert "ROUTING PLAN" in result


# --- T4: tool handles no LM configured gracefully ---------------------------

def test_tool_no_lm_configured():
    from agents.fabric_rdfs_routes import make_rdfs_routes_tool
    ep = _make_ep(_tiny_tbox())
    tool = make_rdfs_routes_tool(ep)

    with patch("dspy.settings") as mock_settings:
        mock_settings.lm = None
        result = tool("What is the range of sio:has-attribute?")

    assert "no" in result.lower() or "llm" in result.lower() or "configured" in result.lower()
```

### Step 2: Run tests to confirm they fail

```bash
cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric
~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_fabric_rdfs_routes.py -v
```

Expected: FAIL — `ImportError: cannot import name 'make_rdfs_routes_tool' from 'agents.fabric_rdfs_routes'`

### Step 3: Implement `agents/fabric_rdfs_routes.py`

Create `agents/fabric_rdfs_routes.py` — copy only the needed parts from rdfs_instruct:

```python
"""RDFS route analysis tool for fabric RLM agents.

Adapts PDDL-Instruct methodology for SPARQL via a sub-agent that reads
ontology structure and produces routing plans with SPARQL triple patterns.

Source: ontology-agent-kr/experiments/rdfs_instruct/rdfs_instruct.py
Copied (not imported) to keep fabric repo self-contained.

Public API:
    make_rdfs_routes_tool(ep) -> Callable[[str], str]
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from agents.fabric_discovery import FabricEndpoint

SCHEMA = Namespace("http://schema.org/")

# ---------------------------------------------------------------------------
# RDFS Instruct Patterns (Pattern 0-6) — copied from rdfs_instruct.py
# ---------------------------------------------------------------------------

RDFS_INSTRUCT_PATTERNS = """\
You are an RDFS reasoning specialist. Given an ontology's structural
declarations and an information need, apply the RDFS/OWL reasoning patterns
below to identify routing paths and affordances for SPARQL construction.

For each step, cite the specific RDFS/OWL axiom being applied and show
the SPARQL triple pattern it produces.

=== PATTERN 0: TYPE GROUNDING ===

RDFS RULE: rdf:type declares which class an individual belongs to.
           Ontology axioms (domain/range, allValuesFrom) are defined on
           classes, not individuals. You cannot route from an individual
           without knowing its type.

INSTANCE CONTEXT (provided by the caller):
  inst:station-alpha  rdf:type  :Platform .

ONTOLOGY:
  :hosts  schema:domainIncludes :Platform ;
          schema:rangeIncludes  :Sensor, :Actuator .

REASONING: The question asks what inst:station-alpha hosts. The instance
  context says it's a :Platform. Properties with :Platform in domainIncludes:
  :hosts. Route: inst:station-alpha :hosts ?device .

INCORRECT: Guessing the type from structural fingerprints or question text.
  WHY WRONG: Obfuscated URIs are opaque. Only rdf:type assertions in the
  data are authoritative.

WHEN NO INSTANCE CONTEXT IS PROVIDED:
  Flag in your routing plan that the main agent must first resolve the
  individual's type via sparql_describe(uri), then re-call with context.


=== PATTERN 1: DOMAIN/RANGE ROUTING ===

RDFS RULE: rdfs:domain declares which class a property belongs to.
           rdfs:range declares what class the property points to.
           (Also applies to schema:domainIncludes/rangeIncludes.)

ONTOLOGY (any ontology):
  :propA  rdfs:domain :ClassX ;  rdfs:range :ClassY .
  :propB  rdfs:domain :ClassY ;  rdfs:range :ClassZ .

REASONING: To get from :ClassX to :ClassZ, there is no direct property.
  But :propA goes X->Y and :propB goes Y->Z.
  Route: ?x :propA ?y . ?y :propB ?z .

INCORRECT: ?x :propB ?z
  WHY WRONG: :propB has rdfs:domain :ClassY, not :ClassX.
  You need the intermediate hop through :ClassY.

DIRECTION RULE: At each hop, determine if the starting node's type
  appears in the property's domain or range:
  - Type in DOMAIN -> FORWARD: starting node is subject.
      SPARQL: ?startingNode :prop ?target .
  - Type in RANGE -> BACKWARD: starting node is object.
      SPARQL: ?target :prop ?startingNode .

DIRECTION EXAMPLE:
  :madeBySensor  domain :Observation ;  range :Sensor .

  Starting from a :Sensor instance (inst:temp-01):
    :Sensor is in RANGE -> BACKWARD traversal.
    SPARQL: ?observation :madeBySensor inst:temp-01 .

  Starting from an :Observation instance:
    :Observation is in DOMAIN -> FORWARD traversal.
    SPARQL: ?obs :madeBySensor ?sensor .

INCORRECT: inst:temp-01 :madeBySensor ?observation .
  WHY WRONG: :Sensor is the range, not the domain. The sensor goes
  in object position when using :madeBySensor.

SPARQL MATERIALIZATION:
  SELECT ?z WHERE { ?x :propA ?y . ?y :propB ?z . }


=== PATTERN 2: HIERARCHY EXPANSION ===

RDFS RULE: rdfs:subClassOf creates a type hierarchy.
           Instances of a subclass are also instances of the parent.
           Querying the parent misses instances typed only as the subclass.

ONTOLOGY:
  :SubA  rdfs:subClassOf :Parent .
  :SubB  rdfs:subClassOf :Parent .
  :propX rdfs:domain :SubA ; rdfs:range :Target .

REASONING: If I need :Target from a :Parent instance, I must know which
  subclass has the property. :propX is on :SubA only. Querying :Parent
  for :propX will fail -- the domain is :SubA.
  I must either: (a) query for :SubA specifically, or
                 (b) use rdfs:subClassOf* to find which subclasses exist,
                     then check which one has :propX.

INCORRECT: ?x a :Parent . ?x :propX ?target
  WHY WRONG: :propX has rdfs:domain :SubA. If ?x is typed as :Parent
  but the actual data types it as :SubB, this returns nothing.

SPARQL MATERIALIZATION (two options):
  Option A (specific): ?x a :SubA . ?x :propX ?target .
  Option B (discovery): ?sub rdfs:subClassOf :Parent .
                        ?x a ?sub . ?x :propX ?target .


=== PATTERN 3: INVERSE PROPERTY NAVIGATION ===

RDFS+ RULE: owl:inverseOf means two properties express the same
            relationship from opposite directions.

ONTOLOGY:
  :madeObservation  owl:inverseOf :madeBySensor .
  :madeObservation  domain :Sensor ;     range :Observation .
  :madeBySensor     domain :Observation ; range :Sensor .

MATERIALIZATION RULE: Endpoints without inference may only materialize
  ONE direction of an inverse pair. Do not assume both exist as triples.
  Prefer the property where your starting type is in the DOMAIN
  (forward traversal), as forward triples are more commonly asserted.

REASONING: Starting from a :Sensor instance, I need :Observation.
  Option A: inst:sensor :madeObservation ?obs (forward on :madeObservation)
  Option B: ?obs :madeBySensor inst:sensor   (forward on :madeBySensor)
  Both are semantically correct. But if the data only asserts
  :madeBySensor triples, Option A returns nothing. Option B works.

DIRECTION CHOICE (using Pattern 1 direction rule):
  My starting type is :Sensor.
  - :madeObservation has domain :Sensor -> FORWARD traversal available.
  - :madeBySensor has range :Sensor -> BACKWARD traversal available.
  Both reach :Observation. Use whichever property is asserted in data.

BEST PRACTICE: In the routing plan, specify BOTH the forward and
  backward forms so the main agent can try the materialized one:
    FORWARD: inst:sensor :madeObservation ?obs .
    BACKWARD: ?obs :madeBySensor inst:sensor .
  If the forward form returns 0 results, the backward form uses the
  inverse property and is equivalent.


=== PATTERN 4: EXISTENTIAL GUARANTEE (OWL RESTRICTION) ===

OWL RULE: owl:someValuesFrom on a property means every instance
          of the restricted class has at least one value for that property.

ONTOLOGY:
  :ClassX rdfs:subClassOf [ owl:onProperty :propA ;
                             owl:someValuesFrom :ClassY ] .

REASONING: Every :ClassX instance is GUARANTEED to have a :propA link
  to some :ClassY. If my query returns zero results for this path,
  my query is wrong -- the data must be there.
  This means I can plan confidently: I don't need to check whether
  the path exists before building on it.

DIAGNOSTIC: Zero results on a guaranteed path = query error, not data absence.


=== PATTERN 5: DISJOINTNESS PRUNING ===

OWL RULE: owl:disjointWith means no instance can belong to both classes.

ONTOLOGY:
  :SubA  owl:disjointWith :SubB .
  :SubA  rdfs:subClassOf :Parent .
  :SubB  rdfs:subClassOf :Parent .

REASONING: If I'm looking for data via :SubA, I can ignore :SubB entirely.
  No entity is both :SubA and :SubB. This prunes the search space.

NEGATIVE AFFORDANCE: Don't look for :SubA-specific properties on :SubB instances.


=== PATTERN 6: UNIVERSAL TYPE RESTRICTION (OWL allValuesFrom) ===

OWL RULE: owl:allValuesFrom means every value of that property MUST be
          of the specified class. Type safety, not existence guarantee.

REASONING: Can assume type of traversal result without explicit check.
CONTRAST: someValuesFrom = "path exists"; allValuesFrom = "values are typed".
          Zero results on allValuesFrom does NOT mean query error.


=== YOUR TASK ===

Given the ONTOLOGY STRUCTURE and INFORMATION NEED below, apply these
patterns to produce a ROUTING ANALYSIS:

1. Identify the source entity type and target information type.
   If INSTANCE CONTEXT is provided, use the grounded rdf:type (Pattern 0).
   If not provided for a named individual, flag that types must be resolved first.
2. Trace the routing path from source to target using domain/range
   declarations (Pattern 1). Show each hop with its DIRECTION:
   - FORWARD if starting type is in domain (starting node = subject).
   - BACKWARD if starting type is in range (starting node = object).
3. Flag any hierarchy expansions needed (Pattern 2) -- where a property
   is on a subclass, not the parent.
4. For inverse property pairs (Pattern 3), provide BOTH forward and
   backward SPARQL forms. Flag that only one direction may be
   materialized in the data.
5. Flag any existential guarantees (Pattern 4) -- paths guaranteed to
   have results.
6. Flag any disjointness pruning opportunities (Pattern 5).
7. Flag any universal type restrictions (Pattern 6) -- values guaranteed
   to be of a specific type.

For EACH routing hop, cite the specific axiom and direction:
  "madeBySensor: domain=Observation, range=Sensor (BACKWARD from Sensor)"

End with a ROUTING PLAN: the sequence of SPARQL triple patterns the
main agent should use, in order. For hops with inverse pairs, show
both directions.
"""


# ---------------------------------------------------------------------------
# Ontology structure extraction (adapted from rdfs_instruct.py)
# ---------------------------------------------------------------------------

def _short_name(uri) -> str:
    s = str(uri)
    if "#" in s:
        return s.split("#")[-1]
    return s.rsplit("/", 1)[-1]


def extract_ontology_structure(g: Graph) -> str:
    """Convert rdflib.Graph to routing-relevant text for RDFS sub-agent."""
    sections = []

    routes = []
    for p in sorted(g.subjects(RDF.type, OWL.ObjectProperty)):
        if not isinstance(p, URIRef):
            continue
        dom = g.value(p, RDFS.domain)
        rng = g.value(p, RDFS.range)
        if dom and rng and isinstance(dom, URIRef) and isinstance(rng, URIRef):
            routes.append(f"  {_short_name(p)}: {_short_name(dom)} -> {_short_name(rng)}")
    sections.append(f"ROUTING PATHS (object properties with domain -> range) [{len(routes)}]:")
    sections.extend(routes)

    _routed = {str(p) for p in g.subjects(RDF.type, OWL.ObjectProperty)
               if isinstance(p, URIRef)
               and g.value(p, RDFS.domain) and isinstance(g.value(p, RDFS.domain), URIRef)
               and g.value(p, RDFS.range) and isinstance(g.value(p, RDFS.range), URIRef)}

    dt_props = []
    for p in sorted(g.subjects(RDF.type, OWL.DatatypeProperty)):
        if not isinstance(p, URIRef):
            continue
        dom = g.value(p, RDFS.domain)
        rng = g.value(p, RDFS.range)
        if dom and isinstance(dom, URIRef):
            dt_props.append(f"  {_short_name(p)}: {_short_name(dom)} -> {_short_name(rng) if rng else 'literal'}")
    sections.append(f"\nDATATYPE PROPERTIES (domain -> literal type) [{len(dt_props)}]:")
    sections.extend(dt_props)

    hierarchy: dict[str, list[str]] = defaultdict(list)
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            hierarchy[_short_name(o)].append(_short_name(s))
    sections.append("\nSUBCLASS HIERARCHIES (parent: [children]):")
    for parent in sorted(hierarchy, key=lambda p: len(hierarchy[p]), reverse=True):
        children = sorted(hierarchy[parent])
        if len(children) >= 2:
            sections.append(f"  {parent} ({len(children)}): {', '.join(children)}")

    inverses = [(s, o) for s, _, o in g.triples((None, OWL.inverseOf, None))
                if isinstance(s, URIRef) and isinstance(o, URIRef)]
    if inverses:
        sections.append("\nINVERSE PROPERTIES (owl:inverseOf):")
        for s, o in inverses:
            sections.append(f"  {_short_name(s)} <-> {_short_name(o)}")

    seen = set()
    restrictions = []
    for cls in g.subjects(RDFS.subClassOf, None):
        if not isinstance(cls, URIRef):
            continue
        for restr in g.objects(cls, RDFS.subClassOf):
            if not isinstance(restr, BNode):
                continue
            on_prop = g.value(restr, OWL.onProperty)
            some_val = g.value(restr, OWL.someValuesFrom)
            if on_prop and some_val:
                key = (_short_name(cls), _short_name(on_prop), _short_name(some_val))
                if key not in seen:
                    seen.add(key)
                    restrictions.append(f"  {key[0]}: every instance has {key[1]} -> {key[2]}")
    if restrictions:
        sections.append("\nEXISTENTIAL GUARANTEES (owl:someValuesFrom restrictions):")
        sections.extend(restrictions)

    return "\n".join(sections)


def build_rdfs_sub_agent_prompt(
    ontology_summary: str,
    information_need: str,
    instance_context: str | None = None,
) -> str:
    """Assemble RDFS reasoning sub-agent prompt."""
    parts = [f"{RDFS_INSTRUCT_PATTERNS}\n", f"ONTOLOGY STRUCTURE:\n{ontology_summary}\n\n"]
    if instance_context:
        parts.append(f"INSTANCE CONTEXT (grounded types from data):\n{instance_context}\n\n")
    parts.append(
        f"INFORMATION NEED: {information_need}\n\n"
        "Apply the RDFS reasoning patterns above. For each routing hop,\n"
        "cite the specific axiom (property name, domain, range). End with\n"
        "a ROUTING PLAN listing the SPARQL triple patterns in order.\n"
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------

def make_rdfs_routes_tool(ep: FabricEndpoint) -> Callable[[str], str]:
    """Return analyze_rdfs_routes(information_need) bound to ep's tbox_graph.

    If ep.tbox_graph is None, returns a stub that explains the TBox is absent.
    Otherwise, pre-computes the ontology summary at factory time and calls
    dspy.settings.lm at each invocation to run the RDFS sub-agent.
    """
    if ep.tbox_graph is None:
        def analyze_rdfs_routes(information_need: str) -> str:  # noqa: E306
            """Analyze RDFS routing paths. No TBox graph available for this endpoint."""
            return (
                "TBox not available: no ontology graph loaded for this endpoint. "
                "Use sparql_query() with GRAPH ?g { ?s ?p ?o } to discover properties."
            )
        return analyze_rdfs_routes

    ont_summary = extract_ontology_structure(ep.tbox_graph)

    def analyze_rdfs_routes(information_need: str) -> str:
        """Analyze RDFS/OWL routing paths to guide SPARQL construction.

        Applies 7 RDFS/OWL reasoning patterns (domain/range routing,
        hierarchy expansion, inverse pairs, OWL restrictions) to the
        loaded ontology and returns a ROUTING PLAN with SPARQL triple
        patterns for the given information need.
        """
        import dspy
        lm = dspy.settings.lm
        if lm is None:
            return "No LLM configured for RDFS route analysis."
        prompt = build_rdfs_sub_agent_prompt(ont_summary, information_need)
        try:
            responses = lm(messages=[{"role": "user", "content": prompt}])
            if isinstance(responses, list) and responses:
                return str(responses[0])
            return str(responses)
        except Exception as e:
            return f"RDFS analysis error: {e}"

    return analyze_rdfs_routes
```

### Step 4: Run tests to confirm they pass

```bash
cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric
~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_fabric_rdfs_routes.py -v
```

Expected: 4 PASS

### Step 5: Run full unit suite

```bash
~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v
```

Expected: all previously passing tests still pass (61 total: 57 existing + 4 new)

### Step 6: Commit

```bash
cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric
git add agents/fabric_rdfs_routes.py tests/pytest/unit/test_fabric_rdfs_routes.py
git commit -m "$(cat <<'EOF'
[Agent: Claude] feat: make_rdfs_routes_tool — RDFS sub-agent backed by ep.tbox_graph

Adapts PDDL-Instruct methodology (rdfs_instruct from ontology-agent-kr)
for fabric RLM agents. Factory pre-computes ontology summary from
ep.tbox_graph; each call invokes dspy.settings.lm for RDFS routing analysis.

4 TDD unit tests; graceful fallback when tbox_graph is None.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Wire into `agents/__init__.py` and Experiment Runner

**Files:**
- Modify: `agents/__init__.py`
- Modify: `experiments/fabric_navigation/run_experiment.py`

---

### Step 1: Write failing test for phase4 features

Add to `tests/pytest/unit/test_tbox_lift_harness.py`:

```python
# --- Phase 4 feature tests ---------------------------------------------------

def test_phase4_features_exist():
    from experiments.fabric_navigation.run_experiment import PHASE_FEATURES
    assert "phase4a-no-rdfs-routes" in PHASE_FEATURES
    assert "phase4b-rdfs-routes" in PHASE_FEATURES


def test_phase4b_has_rdfs_routes_feature():
    from experiments.fabric_navigation.run_experiment import PHASE_FEATURES
    assert "rdfs-routes" in PHASE_FEATURES["phase4b-rdfs-routes"]
    assert "tbox-graph-paths" in PHASE_FEATURES["phase4b-rdfs-routes"]


def test_phase4a_matches_phase3b_minus_rdfs():
    from experiments.fabric_navigation.run_experiment import PHASE_FEATURES
    phase3b = set(PHASE_FEATURES["phase3b-tbox-paths"])
    phase4a = set(PHASE_FEATURES["phase4a-no-rdfs-routes"])
    # phase4a should be identical to phase3b (rdfs-routes not in either)
    assert "rdfs-routes" not in phase4a
    assert phase4a == phase3b
```

Run to confirm failure:
```bash
~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_tbox_lift_harness.py::test_phase4_features_exist -v
```

Expected: FAIL — KeyError on phase4a-no-rdfs-routes

### Step 2: Add `make_rdfs_routes_tool` export to `agents/__init__.py`

Edit `agents/__init__.py` — add to the existing imports line:

```python
from agents.fabric_rdfs_routes import make_rdfs_routes_tool
```

Full updated file:
```python
"""cogitarelink-fabric agent tools — RLM integration with fabric endpoints."""
from agents.fabric_discovery import discover_endpoint, FabricEndpoint, ShapeSummary, ExampleSummary
from agents.fabric_query import make_fabric_query_tool
from agents.fabric_validate import validate_result, ValidationResult, make_validate_tool
from agents.fabric_rdfs_routes import make_rdfs_routes_tool


def __getattr__(name):
    """Lazy import for dspy-dependent symbols."""
    if name in ("run_fabric_query", "FabricQueryResult"):
        from agents.fabric_agent import run_fabric_query, FabricQueryResult
        globals()["run_fabric_query"] = run_fabric_query
        globals()["FabricQueryResult"] = FabricQueryResult
        return globals()[name]
    raise AttributeError(f"module 'agents' has no attribute {name}")
```

### Step 3: Add Phase 4 entries + rdfs-routes tool to `run_experiment.py`

**3a: Add to `PHASE_FEATURES`** (after the phase3b entry, before the closing `}`):

```python
    "phase4a-no-rdfs-routes": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths",
    ],
    "phase4b-rdfs-routes": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths", "rdfs-routes",
    ],
```

**3b: Add import** at top of file (with other agents imports):

```python
from agents.fabric_rdfs_routes import make_rdfs_routes_tool
```

**3c: Extend `rlm_factory()`** to conditionally add `analyze_rdfs_routes`:

Replace the current `rlm_factory` function:

```python
def rlm_factory() -> dspy.RLM:
    features = PHASE_FEATURES[args.phase]
    tools = [make_fabric_query_tool(ep)]
    if "rdfs-routes" in features:
        tools.append(make_rdfs_routes_tool(ep))
    return dspy.RLM(
        FabricQuery,
        tools=tools,
        max_iterations=args.max_iterations,
        verbose=args.verbose,
    )
```

### Step 4: Run phase4 feature tests

```bash
~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_tbox_lift_harness.py -v
```

Expected: all 16 tests PASS (13 existing + 3 new)

### Step 5: Run full unit suite

```bash
~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v
```

Expected: 64 tests PASS

### Step 6: Commit

```bash
git add agents/__init__.py experiments/fabric_navigation/run_experiment.py \
        tests/pytest/unit/test_tbox_lift_harness.py
git commit -m "$(cat <<'EOF'
[Agent: Claude] feat: wire rdfs_routes tool into experiment runner (phase4a/4b)

- agents/__init__.py: export make_rdfs_routes_tool
- run_experiment.py: phase4a (control=phase3b) + phase4b (+ rdfs-routes tool)
- rlm_factory: adds analyze_rdfs_routes to tools when rdfs-routes feature enabled
- 3 TDD tests for phase4 features

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Run Phase 4 Experiments (Integration)

> **Requires:** Docker stack running + `ANTHROPIC_API_KEY` set + ~$0.80 budget

**Files:**
- Output: `experiments/fabric_navigation/results/phase4a-no-rdfs-routes-<timestamp>.json`
- Output: `experiments/fabric_navigation/results/phase4b-rdfs-routes-<timestamp>.json`

### Step 1: Verify Docker stack is running

```bash
docker compose -f /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric/docker-compose.yml ps
curl -s http://localhost:8080/.well-known/void | head -5
```

Expected: `fabric-node` and `oxigraph` containers up; VoID returned.

If stack is down:
```bash
cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric
docker compose up -d
sleep 5
```

### Step 2: Run Phase 4a (control — Phase 3b features, no rdfs_routes tool)

```bash
cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric
~/uvws/.venv/bin/python experiments/fabric_navigation/run_experiment.py \
    --tasks experiments/fabric_navigation/tasks/phase3-sio-tbox.json \
    --phase phase4a-no-rdfs-routes \
    --output experiments/fabric_navigation/results/ \
    --model anthropic/claude-sonnet-4-6 \
    --max-iterations 10
```

Expected output: 6 tasks, score likely 1.0 (same as phase3b), ~5 mean iterations, ~$0.36 cost.

### Step 3: Run Phase 4b (treatment — + rdfs_routes tool)

```bash
~/uvws/.venv/bin/python experiments/fabric_navigation/run_experiment.py \
    --tasks experiments/fabric_navigation/tasks/phase3-sio-tbox.json \
    --phase phase4b-rdfs-routes \
    --output experiments/fabric_navigation/results/ \
    --model anthropic/claude-sonnet-4-6 \
    --max-iterations 10
```

Expected: score 1.0 with potentially fewer iterations on SIO tasks where agent calls `analyze_rdfs_routes`.

### Step 4: Commit results

```bash
cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric
git add experiments/fabric_navigation/results/phase4*.json \
        experiments/fabric_navigation/trajectories/phase4*.jsonl
git commit -m "$(cat <<'EOF'
[Agent: Claude] experiment: phase4 rdfs_routes tool lift measurements

phase4a (control): <score>/<n> tasks, <mean> mean iter, $<cost>
phase4b (treatment + rdfs_routes): <score>/<n> tasks, <mean> mean iter, $<cost>

Fill in actual values from experiment output.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## File Summary

| File | Action | Task |
|---|---|---|
| `agents/fabric_rdfs_routes.py` | **New**: RDFS_INSTRUCT_PATTERNS + extract/build functions + tool factory | 1 |
| `tests/pytest/unit/test_fabric_rdfs_routes.py` | **New**: 4 TDD unit tests | 1 |
| `agents/__init__.py` | Edit: add `make_rdfs_routes_tool` export | 2 |
| `experiments/fabric_navigation/run_experiment.py` | Edit: phase4 entries + rlm_factory extension | 2 |
| `tests/pytest/unit/test_tbox_lift_harness.py` | Edit: 3 phase4 feature tests | 2 |
| `experiments/fabric_navigation/results/phase4*.json` | Output: experiment results | 3 |

**No changes to:** `fabric_agent.py`, `fabric_discovery.py`, `fabric_query.py`, `fabric_validate.py`, `docker-compose.yml`, task JSON files.

## Full Verification

```bash
# Unit tests (no Docker)
~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v
# Expected: 64 tests PASS

# Integration tests (needs Docker)
~/uvws/.venv/bin/python -m pytest tests/pytest/integration/ -v -k "not validate"
```
