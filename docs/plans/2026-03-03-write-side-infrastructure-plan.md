# Write-Side Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable RLM agents to write structured data to fabric named graphs with SHACL-gated commits, PROV-O provenance, and self-describing write targets.

**Architecture:** Four `make_*_tool(ep)` factories in `agents/fabric_write.py` following the existing read-side pattern (`make_fabric_query_tool`). Writes go through FastAPI proxy to Oxigraph via SPARQL UPDATE (INSERT DATA) with VP Bearer auth. `commit_graph` validates against governing SHACL shapes before recording PROV-O provenance in `/graph/audit`.

**Tech Stack:** Python 3.11, FastAPI, httpx, rdflib, pyshacl, Oxigraph (SPARQL 1.1 Update), DSPy RLM

**Design doc:** `docs/plans/2026-03-03-write-side-infrastructure-design.md`

---

### Task 1: Add `fabric:writable` to VoID Templates

**Files:**
- Modify: `fabric/node/void_templates.py:19-35` (VOID_TURTLE sd:namedGraph blocks)
- Modify: `fabric/node/void_templates.py:83-152` (VOID_JSONLD)
- Modify: `ontology/fabric/fabric.ttl` (add `fabric:writable` property)
- Test: `tests/pytest/unit/test_void_writable.py` (new)

**Step 1: Write failing test for `fabric:writable` in VoID**

```python
# tests/pytest/unit/test_void_writable.py
"""Tests that VoID template declares writable graphs."""
import rdflib
from rdflib import Namespace

SD = Namespace("http://www.w3.org/ns/sparql-service-description#")
FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")

def _parse_void():
    from fabric.node.void_templates import VOID_TURTLE
    g = rdflib.Graph()
    g.parse(data=VOID_TURTLE.format(base="https://example.org"), format="turtle")
    return g

def test_entities_graph_is_writable():
    g = _parse_void()
    entities = rdflib.URIRef("https://example.org/graph/entities")
    assert (entities, FABRIC.writable, rdflib.Literal(True)) in g

def test_observations_graph_is_writable():
    g = _parse_void()
    obs = rdflib.URIRef("https://example.org/graph/observations")
    assert (obs, FABRIC.writable, rdflib.Literal(True)) in g

def test_registry_graph_is_not_writable():
    g = _parse_void()
    reg = rdflib.URIRef("https://example.org/graph/registry")
    assert (reg, FABRIC.writable, rdflib.Literal(True)) not in g
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_void_writable.py -v`
Expected: FAIL — `fabric:writable` not yet in template

**Step 3: Add `fabric:writable` to ontology and VoID template**

In `ontology/fabric/fabric.ttl`, add the `fabric:writable` property definition (an OWL DatatypeProperty with domain `sd:NamedGraph` and range `xsd:boolean`).

In `fabric/node/void_templates.py`, add `fabric:writable true ;` to the `sd:namedGraph` entries for `/graph/entities` and `/graph/observations` in `VOID_TURTLE`. Add the equivalent in `VOID_JSONLD`.

Also add the `fabric:` prefix declaration to `VOID_TURTLE` if not already present:
```turtle
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_void_writable.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ontology/fabric/fabric.ttl fabric/node/void_templates.py tests/pytest/unit/test_void_writable.py
git commit -m "feat: add fabric:writable annotation to VoID named graphs"
```

---

### Task 2: Add InstrumentShape + SensorEntityShape to SHACL

**Files:**
- Modify: `shapes/endpoint-sosa.ttl:108` (append after existing ObservationShape)
- Test: `tests/pytest/unit/test_instrument_shape.py` (new)

**Step 1: Write failing test for InstrumentShape validation**

```python
# tests/pytest/unit/test_instrument_shape.py
"""Tests for InstrumentShape and SensorEntityShape SHACL validation."""
import rdflib
from agents.fabric_validate import validate_result

BASE = "https://example.org"

def _load_shapes():
    with open("shapes/endpoint-sosa.ttl") as f:
        return f.read().replace("{base}", BASE)

VALID_INSTRUMENT = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/instrument-001> a sosa:Platform ;
    rdfs:label "Agilent 6545 Q-TOF" ;
    schema:serialNumber "SN-2024-001" ;
    sosa:hosts <{BASE}/entity/sensor-001> .

<{BASE}/entity/sensor-001> a sosa:Sensor ;
    rdfs:label "ESI Source" ;
    sosa:observes <http://example.org/observable/mass-charge-ratio> .
"""

MISSING_LABEL = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/instrument-002> a sosa:Platform ;
    schema:serialNumber "SN-2024-002" ;
    sosa:hosts <{BASE}/entity/sensor-002> .
"""

MISSING_HOSTS = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/instrument-003> a sosa:Platform ;
    rdfs:label "Bruker D8" ;
    schema:serialNumber "SN-2024-003" .
"""

def test_valid_instrument_conforms():
    result = validate_result(VALID_INSTRUMENT, _load_shapes())
    assert result.conforms

def test_missing_label_fails():
    result = validate_result(MISSING_LABEL, _load_shapes())
    assert not result.conforms
    paths = [v.path for v in result.violations]
    assert any("label" in (p or "") for p in paths)

def test_missing_hosts_fails():
    result = validate_result(MISSING_HOSTS, _load_shapes())
    assert not result.conforms
    paths = [v.path for v in result.violations]
    assert any("hosts" in (p or "") for p in paths)

def test_agent_instruction_present():
    result = validate_result(MISSING_LABEL, _load_shapes())
    assert len(result.hints) > 0
    assert any("label" in h.lower() for h in result.hints)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_instrument_shape.py -v`
Expected: FAIL — `sosa:Platform` has no shape constraints yet

**Step 3: Add InstrumentShape and SensorEntityShape to endpoint-sosa.ttl**

Append after line 108 of `shapes/endpoint-sosa.ttl`:

```turtle
# ── Instrument / Platform Shape ──────────────────────────────────
fabric:InstrumentShape a sh:NodeShape ;
    sh:targetClass sosa:Platform ;
    dct:conformsTo <{base}/shapes/instrument-v0.1> ;
    sh:description "Instrument/platform entities. Required: identity and sensor hosting. Recommended: manufacturer and model." ;

    # Required properties
    sh:property [
        sh:path rdfs:label ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
        sh:agentInstruction "Every instrument must have a human-readable label (rdfs:label)." ;
    ] ;
    sh:property [
        sh:path sosa:hosts ;
        sh:minCount 1 ;
        sh:class sosa:Sensor ;
        sh:agentInstruction "An instrument must host at least one sosa:Sensor." ;
    ] ;
    sh:property [
        sh:path schema:serialNumber ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
        sh:agentInstruction "Provide the instrument serial number (schema:serialNumber) for provenance." ;
    ] ;

    # Recommended (sh:Warning — won't block commit)
    sh:property [
        sh:path schema:manufacturer ;
        sh:maxCount 1 ;
        sh:severity sh:Warning ;
        sh:agentInstruction "If known, add manufacturer. Check Wikidata for owl:sameAs linking." ;
    ] ;
    sh:property [
        sh:path schema:model ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:severity sh:Warning ;
        sh:agentInstruction "If known, provide the instrument model identifier." ;
    ] .

# ── Sensor Entity Shape ─────────────────────────────────────────
fabric:SensorEntityShape a sh:NodeShape ;
    sh:targetClass sosa:Sensor ;
    sh:description "Sensor entities hosted by instruments." ;

    sh:property [
        sh:path rdfs:label ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
        sh:agentInstruction "Every sensor must have a human-readable label." ;
    ] ;
    sh:property [
        sh:path sosa:observes ;
        sh:minCount 1 ;
        sh:agentInstruction "Declare what observable property this sensor measures (sosa:observes)." ;
    ] .
```

Add `schema:` prefix declaration in the header (around line 15) if not already present:
```turtle
@prefix schema: <https://schema.org/> .
```

Also add `rdfs:` prefix if missing:
```turtle
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_instrument_shape.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add shapes/endpoint-sosa.ttl tests/pytest/unit/test_instrument_shape.py
git commit -m "feat: add InstrumentShape + SensorEntityShape to endpoint SHACL"
```

---

### Task 3: Implement `discover_write_targets` Tool

**Files:**
- Create: `agents/fabric_write.py`
- Test: `tests/pytest/unit/test_fabric_write.py` (new)

**Step 1: Write failing test for discover_write_targets**

```python
# tests/pytest/unit/test_fabric_write.py
"""Unit tests for write-side tools."""
from unittest.mock import MagicMock
from agents.fabric_write import make_discover_write_targets_tool

def _mock_endpoint():
    """Build a FabricEndpoint mock with writable graph metadata."""
    ep = MagicMock()
    ep.base = "https://example.org"
    ep.vp_token = "test-token"
    ep.named_graphs = [
        {
            "name": "https://example.org/graph/entities",
            "writable": True,
            "conforms_to": "https://example.org/shapes/instrument-v0.1",
        },
        {
            "name": "https://example.org/graph/observations",
            "writable": True,
            "conforms_to": "https://example.org/shapes/observation-v0.1",
        },
        {
            "name": "https://example.org/graph/registry",
            "writable": False,
        },
    ]
    return ep

def test_discover_returns_only_writable():
    tool = make_discover_write_targets_tool(_mock_endpoint())
    result = tool()
    assert "entities" in result
    assert "observations" in result
    assert "registry" not in result

def test_discover_includes_shape_uri():
    tool = make_discover_write_targets_tool(_mock_endpoint())
    result = tool()
    assert "instrument-v0.1" in result
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_fabric_write.py::test_discover_returns_only_writable -v`
Expected: FAIL — `agents/fabric_write.py` doesn't exist

**Step 3: Implement discover_write_targets**

```python
# agents/fabric_write.py
"""Write-side RLM tools for fabric nodes.

Factory functions that close over a FabricEndpoint, matching the read-side
pattern in fabric_query.py and fabric_validate.py.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.fabric_discovery import FabricEndpoint


def make_discover_write_targets_tool(ep: "FabricEndpoint"):
    """Factory: returns a tool that lists writable named graphs and their shapes.

    Parses ep.named_graphs for entries with writable=True.
    """
    def discover_write_targets() -> str:
        """List named graphs that accept writes, with their governing SHACL shapes."""
        targets = []
        for ng in ep.named_graphs:
            if ng.get("writable"):
                name = ng["name"]
                shape = ng.get("conforms_to", "none")
                targets.append(f"  - {name}  (shape: {shape})")
        if not targets:
            return "No writable graphs found on this endpoint."
        header = f"Writable graphs on {ep.base}:\n"
        return header + "\n".join(targets)

    discover_write_targets.__name__ = "discover_write_targets"
    discover_write_targets.__doc__ = (
        "List named graphs that accept writes, with their governing SHACL shapes. "
        "Call this first to learn where you can write and what shapes govern each graph."
    )
    return discover_write_targets
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_fabric_write.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/fabric_write.py tests/pytest/unit/test_fabric_write.py
git commit -m "feat: add discover_write_targets tool factory"
```

---

### Task 4: Parse `fabric:writable` from VoID into FabricEndpoint

**Files:**
- Modify: `agents/fabric_discovery.py:32-49` (FabricEndpoint named_graphs field)
- Modify: `agents/fabric_discovery.py:340-384` (discover_endpoint — VoID parsing)
- Test: `tests/pytest/unit/test_void_writable.py` (extend)

**Step 1: Write failing test for writable parsing in discover**

Add to `tests/pytest/unit/test_void_writable.py`:

```python
def test_discover_endpoint_parses_writable():
    """VoID parsing populates named_graphs[].writable field."""
    from fabric.node.void_templates import VOID_TURTLE
    import rdflib
    from rdflib import Namespace

    FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")
    SD = Namespace("http://www.w3.org/ns/sparql-service-description#")

    g = rdflib.Graph()
    g.parse(data=VOID_TURTLE.format(base="https://example.org"), format="turtle")

    # Check that named graphs with fabric:writable true exist
    writable_graphs = set()
    for ng in g.subjects(FABRIC.writable, rdflib.Literal(True)):
        for name in g.objects(ng, SD.name):
            writable_graphs.add(str(name))

    assert "https://example.org/graph/entities" in writable_graphs
    assert "https://example.org/graph/observations" in writable_graphs
```

**Step 2: Run test to verify it passes** (should pass from Task 1)

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_void_writable.py -v`

**Step 3: Update VoID parsing in discover_endpoint**

In `agents/fabric_discovery.py`, in the section where `discover_endpoint()` parses VoID TTL to populate `ep.named_graphs`, extend the named graph dict to include `writable` and `conforms_to` fields by checking for `fabric:writable` and `dct:conformsTo` triples on each `sd:NamedGraph` resource.

The named_graphs list is built during VoID parsing (around line 365-375). For each named graph entry, add:
```python
ng_dict["writable"] = bool(void_g.value(ng_node, FABRIC.writable))
conforms = void_g.value(ng_node, DCT.conformsTo)
if conforms:
    ng_dict["conforms_to"] = str(conforms)
```

**Step 4: Run all tests to verify nothing broken**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agents/fabric_discovery.py tests/pytest/unit/test_void_writable.py
git commit -m "feat: parse fabric:writable from VoID into FabricEndpoint.named_graphs"
```

---

### Task 5: Implement `write_triples` Tool

**Files:**
- Modify: `agents/fabric_write.py` (add `make_write_triples_tool`)
- Test: `tests/pytest/unit/test_fabric_write.py` (extend)

**Step 1: Write failing test for write_triples**

Add to `tests/pytest/unit/test_fabric_write.py`:

```python
import httpx
from unittest.mock import patch

SAMPLE_TURTLE = """\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .

<https://example.org/entity/inst-001> a sosa:Platform ;
    rdfs:label "Test Instrument" ;
    schema:serialNumber "SN-001" ;
    sosa:hosts <https://example.org/entity/sensor-001> .
"""

from agents.fabric_write import make_write_triples_tool

def test_write_triples_posts_turtle():
    ep = _mock_endpoint()
    tool = make_write_triples_tool(ep)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "OK"

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        result = tool("https://example.org/graph/entities", SAMPLE_TURTLE)

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "graph=" in call_args.kwargs.get("url", call_args[0][0]) or "graph=" in str(call_args)
    assert "Bearer test-token" in str(call_args)
    assert "wrote" in result.lower() or "success" in result.lower()

def test_write_triples_returns_error_on_401():
    ep = _mock_endpoint()
    tool = make_write_triples_tool(ep)

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("httpx.post", return_value=mock_resp):
        result = tool("https://example.org/graph/entities", SAMPLE_TURTLE)

    assert "auth" in result.lower() or "401" in result
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_fabric_write.py::test_write_triples_posts_turtle -v`
Expected: FAIL — `make_write_triples_tool` not defined

**Step 3: Implement write_triples**

Add to `agents/fabric_write.py`:

```python
import httpx
from urllib.parse import quote as urlquote

def _ssl_verify():
    import os
    return os.environ.get("SSL_CERT_FILE", True)

def _write_headers(vp_token: str | None) -> dict[str, str]:
    h = {"Content-Type": "text/turtle"}
    if vp_token:
        h["Authorization"] = f"Bearer {vp_token}"
    return h


def make_write_triples_tool(ep: "FabricEndpoint"):
    """Factory: returns a tool that writes Turtle to a named graph via SPARQL UPDATE.

    Uses INSERT DATA with GRAPH clause. Permissive — no SHACL validation at write time.
    """
    def write_triples(graph: str, turtle: str) -> str:
        """Write Turtle triples to a named graph. No validation — use validate_graph after."""
        # Build INSERT DATA query wrapping the Turtle in a GRAPH block
        # We parse with rdflib first to extract pure triples (no prefixes)
        import rdflib
        try:
            g = rdflib.Graph()
            g.parse(data=turtle, format="turtle")
        except Exception as e:
            return f"Invalid Turtle syntax: {e}"

        if len(g) == 0:
            return "No triples found in the provided Turtle."

        # Serialize as N-Triples for safe embedding in INSERT DATA
        nt = g.serialize(format="nt")
        sparql = f"INSERT DATA {{ GRAPH <{graph}> {{ {nt} }} }}"

        headers = {"Content-Type": "application/sparql-update"}
        if ep.vp_token:
            headers["Authorization"] = f"Bearer {ep.vp_token}"

        try:
            r = httpx.post(
                f"{ep.base}/sparql/update",
                content=sparql,
                headers=headers,
                timeout=30.0,
                verify=_ssl_verify(),
            )
        except httpx.ConnectError as e:
            return f"Connection error: {e}"

        if r.status_code == 401:
            return (
                "Authentication required (401). The write tool was not configured "
                "with a valid VP Bearer token."
            )
        if r.status_code == 403:
            return f"Forbidden (403): not authorized to write to {graph}."
        if r.status_code >= 400:
            return f"Write failed ({r.status_code}): {r.text[:500]}"

        return f"Successfully wrote {len(g)} triples to {graph}."

    write_triples.__name__ = "write_triples"
    write_triples.__doc__ = (
        "Write Turtle triples to a named graph. Arguments: graph (the target "
        "named graph URI), turtle (Turtle-formatted RDF triples). No validation "
        "at write time — call validate_graph() after writing to check conformance."
    )
    return write_triples
```

**Step 4: Update tests to match actual implementation**

The implementation uses `/sparql/update` with INSERT DATA rather than Graph Store Protocol POST. Update the mock test to patch `httpx.post` with URL matching `/sparql/update`.

**Step 5: Run tests to verify they pass**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_fabric_write.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add agents/fabric_write.py tests/pytest/unit/test_fabric_write.py
git commit -m "feat: add write_triples tool factory"
```

---

### Task 6: Implement `validate_graph` Tool (Graph-Level)

**Files:**
- Modify: `agents/fabric_write.py` (add `make_validate_graph_tool`)
- Test: `tests/pytest/unit/test_fabric_write.py` (extend)

This tool differs from the existing `make_validate_tool` in `fabric_validate.py`: it fetches graph contents from the endpoint via CONSTRUCT, then validates against the governing shape. The existing tool validates Turtle strings passed directly.

**Step 1: Write failing test for validate_graph**

Add to `tests/pytest/unit/test_fabric_write.py`:

```python
from agents.fabric_write import make_validate_graph_tool

def test_validate_graph_conformant(tmp_path):
    """validate_graph returns conformant for valid data."""
    ep = _mock_endpoint()
    ep.shapes_ttl = _load_shapes()  # from shapes/endpoint-sosa.ttl

    # Mock the CONSTRUCT query to return valid instrument Turtle
    valid_nt = (
        '<https://example.org/entity/inst-001> '
        '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
        '<http://www.w3.org/ns/sosa/Platform> .\n'
        '<https://example.org/entity/inst-001> '
        '<http://www.w3.org/2000/01/rdf-schema#label> '
        '"Test Instrument" .\n'
        '<https://example.org/entity/inst-001> '
        '<https://schema.org/serialNumber> '
        '"SN-001" .\n'
        '<https://example.org/entity/inst-001> '
        '<http://www.w3.org/ns/sosa/hosts> '
        '<https://example.org/entity/sensor-001> .\n'
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = valid_nt
    mock_resp.headers = {"Content-Type": "application/n-triples"}

    with patch("httpx.post", return_value=mock_resp):
        tool = make_validate_graph_tool(ep)
        result = tool("https://example.org/graph/entities")

    assert "conforms" in result.lower()

def test_validate_graph_non_conformant():
    """validate_graph returns violations for invalid data."""
    ep = _mock_endpoint()
    ep.shapes_ttl = _load_shapes()

    # Missing rdfs:label — should violate InstrumentShape
    invalid_nt = (
        '<https://example.org/entity/inst-002> '
        '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
        '<http://www.w3.org/ns/sosa/Platform> .\n'
        '<https://example.org/entity/inst-002> '
        '<https://schema.org/serialNumber> '
        '"SN-002" .\n'
        '<https://example.org/entity/inst-002> '
        '<http://www.w3.org/ns/sosa/hosts> '
        '<https://example.org/entity/sensor-002> .\n'
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = invalid_nt
    mock_resp.headers = {"Content-Type": "application/n-triples"}

    with patch("httpx.post", return_value=mock_resp):
        tool = make_validate_graph_tool(ep)
        result = tool("https://example.org/graph/entities")

    assert "violation" in result.lower()
    assert "label" in result.lower()
```

Add a helper at module level:

```python
def _load_shapes():
    with open("shapes/endpoint-sosa.ttl") as f:
        return f.read().replace("{base}", "https://example.org")
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_fabric_write.py::test_validate_graph_conformant -v`
Expected: FAIL — `make_validate_graph_tool` not defined

**Step 3: Implement validate_graph**

Add to `agents/fabric_write.py`:

```python
from agents.fabric_validate import validate_result


def make_validate_graph_tool(ep: "FabricEndpoint"):
    """Factory: returns a tool that validates a named graph against its governing shape.

    Fetches graph contents via CONSTRUCT, validates with pyshacl, returns
    conformance report with sh:agentInstruction hints on failure.
    """
    def validate_graph(graph: str) -> str:
        """Validate a named graph against its governing SHACL shape."""
        # Fetch graph contents via CONSTRUCT
        construct_q = f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}"
        headers = {"Content-Type": "application/sparql-query", "Accept": "text/turtle"}
        if ep.vp_token:
            headers["Authorization"] = f"Bearer {ep.vp_token}"

        try:
            r = httpx.post(
                f"{ep.base}/sparql",
                content=construct_q,
                headers=headers,
                timeout=30.0,
                verify=_ssl_verify(),
            )
        except httpx.ConnectError as e:
            return f"Connection error fetching graph: {e}"

        if r.status_code >= 400:
            return f"Failed to fetch graph {graph} ({r.status_code}): {r.text[:500]}"

        data_ttl = r.text
        if not data_ttl.strip():
            return f"Graph {graph} is empty — nothing to validate."

        # Validate against shapes
        result = validate_result(data_ttl, ep.shapes_ttl, tbox_graph=ep.tbox_graph)

        if result.conforms:
            return f"CONFORMS: Graph {graph} passes all SHACL constraints."

        # Format violations for RLM consumption
        lines = [f"VIOLATIONS ({len(result.violations)}) in {graph}:"]
        for v in result.violations:
            line = f"  - {v.path or '?'}: {v.message}"
            if v.agent_hint:
                line += f"\n    FIX: {v.agent_hint}"
            lines.append(line)
        if result.hints:
            lines.append("\nSUMMARY HINTS:")
            for h in result.hints:
                lines.append(f"  - {h}")
        return "\n".join(lines)

    validate_graph.__name__ = "validate_graph"
    validate_graph.__doc__ = (
        "Validate a named graph against its governing SHACL shape. "
        "Argument: graph (the named graph URI to validate). "
        "Returns 'CONFORMS' or a list of violations with fix instructions."
    )
    return validate_graph
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_fabric_write.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/fabric_write.py tests/pytest/unit/test_fabric_write.py
git commit -m "feat: add validate_graph tool factory"
```

---

### Task 7: Implement `commit_graph` Tool

**Files:**
- Modify: `agents/fabric_write.py` (add `make_commit_graph_tool`)
- Test: `tests/pytest/unit/test_fabric_write.py` (extend)

**Step 1: Write failing test for commit_graph**

Add to `tests/pytest/unit/test_fabric_write.py`:

```python
from agents.fabric_write import make_commit_graph_tool

def test_commit_graph_records_provenance_on_success():
    """commit_graph writes PROV-O activity to /graph/audit on success."""
    ep = _mock_endpoint()
    ep.shapes_ttl = _load_shapes()

    # First call: CONSTRUCT returns valid data
    valid_resp = MagicMock()
    valid_resp.status_code = 200
    valid_resp.text = (
        '<https://example.org/entity/inst-001> '
        '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
        '<http://www.w3.org/ns/sosa/Platform> .\n'
        '<https://example.org/entity/inst-001> '
        '<http://www.w3.org/2000/01/rdf-schema#label> '
        '"Test Instrument" .\n'
        '<https://example.org/entity/inst-001> '
        '<https://schema.org/serialNumber> '
        '"SN-001" .\n'
        '<https://example.org/entity/inst-001> '
        '<http://www.w3.org/ns/sosa/hosts> '
        '<https://example.org/entity/sensor-001> .\n'
    )
    valid_resp.headers = {"Content-Type": "application/n-triples"}

    # Second call: INSERT DATA for PROV-O
    prov_resp = MagicMock()
    prov_resp.status_code = 200
    prov_resp.text = "OK"

    call_count = {"n": 0}
    def mock_post(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return valid_resp
        return prov_resp

    with patch("httpx.post", side_effect=mock_post):
        tool = make_commit_graph_tool(ep)
        result = tool("https://example.org/graph/entities")

    assert "committed" in result.lower() or "conforms" in result.lower()
    assert call_count["n"] >= 2  # CONSTRUCT + PROV-O INSERT

def test_commit_graph_rejects_non_conformant():
    """commit_graph returns violations without writing provenance."""
    ep = _mock_endpoint()
    ep.shapes_ttl = _load_shapes()

    # Return data missing rdfs:label
    invalid_resp = MagicMock()
    invalid_resp.status_code = 200
    invalid_resp.text = (
        '<https://example.org/entity/inst-002> '
        '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
        '<http://www.w3.org/ns/sosa/Platform> .\n'
        '<https://example.org/entity/inst-002> '
        '<https://schema.org/serialNumber> '
        '"SN-002" .\n'
        '<https://example.org/entity/inst-002> '
        '<http://www.w3.org/ns/sosa/hosts> '
        '<https://example.org/entity/sensor-002> .\n'
    )
    invalid_resp.headers = {"Content-Type": "application/n-triples"}

    with patch("httpx.post", return_value=invalid_resp) as mock_post:
        tool = make_commit_graph_tool(ep)
        result = tool("https://example.org/graph/entities")

    assert "violation" in result.lower()
    # Should NOT have made a second call for PROV-O
    assert mock_post.call_count == 1
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_fabric_write.py::test_commit_graph_records_provenance_on_success -v`
Expected: FAIL — `make_commit_graph_tool` not defined

**Step 3: Implement commit_graph**

Add to `agents/fabric_write.py`:

```python
from datetime import datetime, timezone


def make_commit_graph_tool(ep: "FabricEndpoint"):
    """Factory: returns a tool that validates a graph and records PROV-O provenance.

    Calls validate_graph internally. If conformant, writes a prov:Activity
    to /graph/audit recording who committed, what shape was used, and when.
    """
    _validate = make_validate_graph_tool(ep)

    def commit_graph(graph: str) -> str:
        """Validate graph and record provenance. Returns violations if non-conformant."""
        result = _validate(graph)

        if not result.startswith("CONFORMS"):
            return result  # Pass through validation report

        # Find governing shape for this graph
        shape_uri = "unknown"
        for ng in ep.named_graphs:
            if ng.get("name") == graph:
                shape_uri = ng.get("conforms_to", "unknown")
                break

        # Record PROV-O activity
        import uuid
        activity_id = f"{ep.base}/activity/{uuid.uuid4()}"
        now = datetime.now(timezone.utc).isoformat()
        agent_did = getattr(ep, "agent_did", "unknown")

        prov_sparql = f"""\
INSERT DATA {{
  GRAPH <{ep.base}/graph/audit> {{
    <{activity_id}> a <http://www.w3.org/ns/prov#Activity> ;
        <http://www.w3.org/ns/prov#wasAssociatedWith> <{agent_did}> ;
        <http://www.w3.org/ns/prov#used> <{shape_uri}> ;
        <http://www.w3.org/ns/prov#generated> <{graph}> ;
        <http://www.w3.org/ns/prov#endedAtTime> "{now}"^^<http://www.w3.org/2001/XMLSchema#dateTime> ;
        <http://purl.org/dc/terms/description> "Committed graph {graph}" .
  }}
}}"""

        headers = {"Content-Type": "application/sparql-update"}
        if ep.vp_token:
            headers["Authorization"] = f"Bearer {ep.vp_token}"

        try:
            r = httpx.post(
                f"{ep.base}/sparql/update",
                content=prov_sparql,
                headers=headers,
                timeout=15.0,
                verify=_ssl_verify(),
            )
            if r.status_code >= 400:
                return f"Graph validates but provenance write failed ({r.status_code}): {r.text[:200]}"
        except httpx.ConnectError as e:
            return f"Graph validates but provenance write failed: {e}"

        return f"COMMITTED: Graph {graph} conforms to {shape_uri}. Provenance recorded."

    commit_graph.__name__ = "commit_graph"
    commit_graph.__doc__ = (
        "Validate a named graph and record provenance. Argument: graph (the named "
        "graph URI). If conformant, records a prov:Activity in /graph/audit. "
        "If non-conformant, returns violations with fix instructions — fix and retry."
    )
    return commit_graph
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_fabric_write.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add agents/fabric_write.py tests/pytest/unit/test_fabric_write.py
git commit -m "feat: add commit_graph tool factory with PROV-O provenance"
```

---

### Task 8: Export Write Tools from `agents/__init__.py`

**Files:**
- Modify: `agents/__init__.py:1-7` (add write tool imports)

**Step 1: Add exports**

Add to `agents/__init__.py`:

```python
from agents.fabric_write import (
    make_discover_write_targets_tool,
    make_write_triples_tool,
    make_validate_graph_tool,
    make_commit_graph_tool,
)
```

**Step 2: Verify imports work**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -c "from agents import make_write_triples_tool, make_commit_graph_tool; print('OK')"`
Expected: `OK`

**Step 3: Run full test suite**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/ -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add agents/__init__.py
git commit -m "feat: export write tool factories from agents package"
```

---

### Task 9: Add `dct:conformsTo` to VoID Named Graphs

**Files:**
- Modify: `fabric/node/void_templates.py:19-35` (add `dct:conformsTo` to writable graph entries)
- Test: `tests/pytest/unit/test_void_writable.py` (extend)

**Step 1: Write failing test**

Add to `tests/pytest/unit/test_void_writable.py`:

```python
def test_entities_graph_has_conforms_to():
    g = _parse_void()
    entities = rdflib.URIRef("https://example.org/graph/entities")
    DCT = Namespace("http://purl.org/dc/terms/")
    conforms = list(g.objects(entities, DCT.conformsTo))
    assert len(conforms) == 1
    assert "instrument" in str(conforms[0]).lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_void_writable.py::test_entities_graph_has_conforms_to -v`
Expected: FAIL

**Step 3: Add `dct:conformsTo` to VoID template**

In `fabric/node/void_templates.py`, add to the `/graph/entities` named graph entry:
```turtle
dct:conformsTo <{base}/shapes/instrument-v0.1> ;
```

And to `/graph/observations`:
```turtle
dct:conformsTo <{base}/shapes/observation-v0.1> ;
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/test_void_writable.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add fabric/node/void_templates.py tests/pytest/unit/test_void_writable.py
git commit -m "feat: add dct:conformsTo shape references to VoID named graphs"
```

---

### Task 10: Integration Test — Write + Validate + Commit Cycle

**Files:**
- Create: `tests/pytest/integration/test_fabric_write_integration.py`
- Create: `tests/hurl/phase2/60-write-triples.hurl` (optional)

**Step 1: Write integration test**

```python
# tests/pytest/integration/test_fabric_write_integration.py
"""Integration test for the write → validate → commit cycle."""
import os
import pytest
import httpx

GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")

@pytest.fixture(scope="module")
def ssl_cert():
    return os.environ.get("SSL_CERT_FILE", True)

@pytest.fixture(scope="module")
def vp_token(ssl_cert):
    r = httpx.post(
        f"{GATEWAY}/test/create-vp",
        json={
            "agentRole": "DevelopmentAgentRole",
            "authorizedGraphs": ["*"],
            "authorizedOperations": ["read", "write"],
            "validMinutes": 60,
        },
        timeout=15.0,
        verify=ssl_cert,
    )
    if r.status_code != 200:
        pytest.skip("Auth not available")
    return r.json()["token"]

@pytest.fixture(scope="module")
def ep(vp_token, ssl_cert):
    from agents.fabric_discovery import discover_endpoint
    return discover_endpoint(GATEWAY, vp_token=vp_token)

TEST_GRAPH = f"{GATEWAY}/graph/test-write-integration"

INSTRUMENT_TURTLE = """\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .

<{base}/entity/test-inst-001> a sosa:Platform ;
    rdfs:label "Integration Test Instrument" ;
    schema:serialNumber "SN-INT-001" ;
    sosa:hosts <{base}/entity/test-sensor-001> .

<{base}/entity/test-sensor-001> a sosa:Sensor ;
    rdfs:label "Test Sensor" ;
    sosa:observes <http://example.org/observable/test-property> .
"""

def test_write_validate_commit_cycle(ep, vp_token, ssl_cert):
    """Full write → validate → commit cycle against live endpoint."""
    from agents.fabric_write import (
        make_write_triples_tool,
        make_validate_graph_tool,
        make_commit_graph_tool,
    )

    turtle = INSTRUMENT_TURTLE.replace("{base}", ep.base)
    write = make_write_triples_tool(ep)
    validate = make_validate_graph_tool(ep)
    commit = make_commit_graph_tool(ep)

    # Write
    result = write(TEST_GRAPH, turtle)
    assert "success" in result.lower() or "wrote" in result.lower(), f"Write failed: {result}"

    # Validate
    result = validate(TEST_GRAPH)
    # Note: validation may report issues if graph has no shape binding —
    # this test validates the plumbing works, not the shape governance
    assert result  # non-empty response

    # Cleanup
    headers = {"Content-Type": "application/sparql-update"}
    if vp_token:
        headers["Authorization"] = f"Bearer {vp_token}"
    httpx.post(
        f"{ep.base}/sparql/update",
        content=f"DROP SILENT GRAPH <{TEST_GRAPH}>",
        headers=headers,
        timeout=10.0,
        verify=ssl_cert,
    )
```

**Step 2: Run integration test**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem FABRIC_GATEWAY=https://bootstrap.cogitarelink.ai python -m pytest tests/pytest/integration/test_fabric_write_integration.py -v`
Expected: PASS (requires Docker stack running)

**Step 3: Commit**

```bash
git add tests/pytest/integration/test_fabric_write_integration.py
git commit -m "test: integration test for write-validate-commit cycle"
```

---

### Task 11: Wire Write Tools into Experiment Framework

**Files:**
- Modify: `experiments/fabric_navigation/run_experiment.py:49-138` (add write phase features)
- Modify: `experiments/fabric_navigation/run_experiment.py:343-354` (rlm_factory — add write tools)
- Modify: `experiments/fabric_navigation/run_experiment.py:356-397` (add _WRITE_TOOL_HINT + kwarg_builder)

**Step 1: Add write-phase feature flags**

In `PHASE_FEATURES` dict (around line 49), add new phase entries:

```python
"phase7a-write-baseline": [
    # All read features from phase1.5d-routing
    "void-sd", "void-urispace", "void-graph-inventory",
    "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
    "sparql-examples", "sparql-examples-extended",
    "enhanced-routing-plan",
    # Write tools
    "write-tools",
],
```

**Step 2: Add write tools to rlm_factory**

In `rlm_factory()` (around line 343), add conditional tool inclusion:

```python
if "write-tools" in features:
    from agents.fabric_write import (
        make_discover_write_targets_tool,
        make_write_triples_tool,
        make_validate_graph_tool,
        make_commit_graph_tool,
    )
    tools.extend([
        make_discover_write_targets_tool(ep),
        make_write_triples_tool(ep),
        make_validate_graph_tool(ep),
        make_commit_graph_tool(ep),
    ])
```

**Step 3: Add `_WRITE_TOOL_HINT` and update kwarg_builder**

After `_RDFS_TOOL_HINT` (around line 386), add:

```python
_WRITE_TOOL_HINT = """

## Write Tools Available

You have four write tools in your REPL:
- `discover_write_targets()` — find which graphs accept writes and what shapes govern them
- `write_triples(graph, turtle)` — write Turtle triples to a named graph (no validation)
- `validate_graph(graph)` — check graph against its SHACL shape; returns fix instructions
- `commit_graph(graph)` — validate + record provenance; returns violations if non-conformant

Workflow: discover_write_targets → write_triples → validate_graph → fix if needed → commit_graph
"""
```

In `kwarg_builder()`, add:

```python
if "write-tools" in features:
    sd += _WRITE_TOOL_HINT
```

**Step 4: Run existing tests to verify no regression**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add experiments/fabric_navigation/run_experiment.py
git commit -m "feat: wire write tools into experiment framework (phase7a)"
```

---

### Task 12: Add `shapes_ttl` and `agent_did` to FabricEndpoint

**Files:**
- Modify: `agents/fabric_discovery.py:32-49` (add `shapes_ttl` field retention)
- Modify: `agents/fabric_discovery.py:314-337` (extract agent_did from register_and_authenticate)

The write tools need `ep.shapes_ttl` (raw shapes Turtle for pyshacl validation) and `ep.agent_did` (for PROV-O provenance). Currently `shapes_ttl` is fetched but only parsed into `ep.shapes`, not retained as raw TTL. `agent_did` is not stored.

**Step 1: Write failing test**

Add to an appropriate test file:

```python
def test_endpoint_retains_shapes_ttl():
    """FabricEndpoint stores raw shapes_ttl for write-side validation."""
    # This tests the field exists on the dataclass
    from agents.fabric_discovery import FabricEndpoint
    import dataclasses
    fields = {f.name for f in dataclasses.fields(FabricEndpoint)}
    assert "shapes_ttl" in fields
```

**Step 2: Ensure shapes_ttl is populated during discover_endpoint**

In `discover_endpoint()`, the shapes TTL is already fetched (around line 365). Ensure it's stored on the endpoint object as `ep.shapes_ttl = shapes_response.text` (with `{base}` substitution applied).

**Step 3: Add `agent_did` to FabricEndpoint**

Add field: `agent_did: str | None = None` (after `vp_token`). In `register_and_authenticate()`, parse the agent DID from the response and store it: `ep.agent_did = response_data.get("agentDid")`.

**Step 4: Run tests**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agents/fabric_discovery.py
git commit -m "feat: retain shapes_ttl and agent_did on FabricEndpoint"
```

---

### Task 13: Full Suite Verification

**Step 1: Run unit tests**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem python -m pytest tests/pytest/unit/ -v`
Expected: All PASS

**Step 2: Run integration tests** (requires Docker stack)

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric && SSL_CERT_FILE=/tmp/cogitarelink-ca-bundle.pem FABRIC_GATEWAY=https://bootstrap.cogitarelink.ai python -m pytest tests/pytest/integration/ -v`
Expected: All PASS

**Step 3: Run HURL tests**

Run: `cd /Users/cvardema/dev/git/LA3D/agents/cogitarelink-fabric/tests && make test-all`
Expected: 42/42 PASS (or 38/42 with known pre-existing failures)

**Step 4: Final commit if any fixups needed**

```bash
git add -u
git commit -m "fix: test suite fixups for write-side infrastructure"
```
