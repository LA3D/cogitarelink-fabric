# Phase 7: Catalog Discovery Experiments — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Phase 7 experiments testing whether the RLM agent can discover and query external SPARQL endpoints (QLever PubChem/Wikidata/OSM) via fabric catalog metadata.

**Architecture:** Extend `FabricEndpoint` with catalog-derived `ExternalService` entries. Add `query_external_sparql` tool that queries QLever endpoints directly from the host (bypassing Oxigraph SERVICE federation which is blocked by Docker networking). Wire into existing experiment harness via new phase7a/7b feature flags.

**Tech Stack:** Python 3.12, rdflib 7.6, httpx 0.28, dspy 3.1, existing experiment harness infrastructure.

**Python environment for tests:** `~/uvws/.venv/bin/python -m pytest`

---

## Task 1: Fix PubChem Template Examples

The existing `external-endpoints.ttl.template` has PubChem example queries that don't return results against QLever because they use shorthand SIO class names instead of CHEMINF codes. Fix before building anything on top.

**Files:**
- Modify: `fabric/node/external-endpoints.ttl.template`

**Step 1: Update PubChem example queries to use correct predicates**

Replace the PubChem examples. The key issue: QLever PubChem doesn't have `compound:Compound` as a type or `rdfs:label` on compounds. Compounds are at `http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID{n}` with attributes via `sio:SIO_000008` → typed blank nodes → `sio:SIO_000300`.

In `fabric/node/external-endpoints.ttl.template`, replace the two PubChem `spex:SparqlExample` blocks:

```turtle
    spex:SparqlExample [
        a spex:SparqlSelectExecutable ;
        rdfs:label "Lookup molecular formula by CID" ;
        spex:query """PREFIX sio: <http://semanticscience.org/resource/>
SELECT ?formula WHERE {
  <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID2244> sio:SIO_000008 ?attr .
  ?attr a sio:CHEMINF_000042 ; sio:SIO_000300 ?formula .
} LIMIT 5"""
    ] ;
    spex:SparqlExample [
        a spex:SparqlSelectExecutable ;
        rdfs:label "Get compound properties by CID" ;
        spex:query """PREFIX sio: <http://semanticscience.org/resource/>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT ?attrType ?val WHERE {
  <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID2244> sio:SIO_000008 ?attr .
  ?attr a ?attrType ; sio:SIO_000300 ?val .
} LIMIT 20"""
    ] .
```

**Step 2: Rebuild Docker and verify template loads**

Run:
```bash
cd ~/dev/git/LA3D/agents/cogitarelink-fabric
docker compose build fabric-node && docker compose up -d
sleep 15
curl -s http://localhost:8080/.well-known/catalog -H "Accept: text/turtle" | grep -c "CHEMINF_000042"
```
Expected: `1` (the new example query is present in the catalog)

**Step 3: Run existing tests to verify no breakage**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_external_endpoints.py -v`
Expected: all 12 tests pass (template structure unchanged, only query content changed)

**Step 4: Commit**

```bash
git add fabric/node/external-endpoints.ttl.template
git commit -m "fix: correct PubChem QLever example queries to use full SIO/CHEMINF IRIs"
```

---

## Task 2: Catalog Parsing in fabric_discovery.py — Tests

Add unit tests for the new `_parse_catalog` function and `ExternalService` dataclass before writing the implementation.

**Files:**
- Create: `tests/pytest/unit/test_catalog_discovery.py`

**Step 1: Write failing tests**

Create `tests/pytest/unit/test_catalog_discovery.py`:

```python
"""Unit tests for catalog discovery — _parse_catalog and ExternalService."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

import pytest

# Sample catalog Turtle — minimal version of what /.well-known/catalog returns
# after D29 external endpoint attestation loads dcat:DataService entries.
CATALOG_TTL = """
@prefix dct:    <http://purl.org/dc/terms/> .
@prefix dcat:   <http://www.w3.org/ns/dcat#> .
@prefix void:   <http://rdfs.org/ns/void#> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .
@prefix spex:   <https://purl.expasy.org/sparql-examples/ontology#> .
@prefix sh:     <http://www.w3.org/ns/shacl#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

<http://localhost:8080/external/qlever-pubchem> a dcat:DataService ;
    dct:title "QLever PubChem SPARQL Endpoint" ;
    dct:description "PubChem RDF via QLever" ;
    dcat:endpointURL <https://qlever.cs.uni-freiburg.de/api/pubchem> ;
    void:vocabulary <http://semanticscience.org/resource/> ;
    fabric:vouchedBy <did:webvh:abc:localhost> ;
    spex:SparqlExample [
        a spex:SparqlSelectExecutable ;
        rdfs:label "Lookup molecular formula by CID" ;
        spex:query "SELECT ?formula WHERE { <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID2244> <http://semanticscience.org/resource/SIO_000008> ?attr . ?attr a <http://semanticscience.org/resource/CHEMINF_000042> ; <http://semanticscience.org/resource/SIO_000300> ?formula . } LIMIT 5"
    ] .

<http://localhost:8080/external/qlever-wikidata> a dcat:DataService ;
    dct:title "QLever Wikidata SPARQL Endpoint" ;
    dct:description "Wikidata via QLever" ;
    dcat:endpointURL <https://qlever.cs.uni-freiburg.de/api/wikidata> ;
    void:vocabulary <http://www.wikidata.org/prop/direct/> ;
    fabric:vouchedBy <did:webvh:abc:localhost> .

# Also include a dcat:Dataset to ensure we skip non-DataService entries
<http://localhost:8080/graph/observations> a dcat:Dataset ;
    dct:title "Observations" .
"""

EMPTY_CATALOG = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct:  <http://purl.org/dc/terms/> .
<http://localhost:8080/graph/observations> a dcat:Dataset ;
    dct:title "Observations" .
"""


class TestParseCatalog:
    def test_import(self):
        from agents.fabric_discovery import _parse_catalog, ExternalService

    def test_returns_list_of_external_service(self):
        from agents.fabric_discovery import _parse_catalog, ExternalService
        services = _parse_catalog(CATALOG_TTL)
        assert isinstance(services, list)
        assert all(isinstance(s, ExternalService) for s in services)

    def test_finds_two_data_services(self):
        from agents.fabric_discovery import _parse_catalog
        services = _parse_catalog(CATALOG_TTL)
        assert len(services) == 2

    def test_skips_dcat_dataset(self):
        from agents.fabric_discovery import _parse_catalog
        services = _parse_catalog(CATALOG_TTL)
        titles = [s.title for s in services]
        assert "Observations" not in titles

    def test_pubchem_endpoint_url(self):
        from agents.fabric_discovery import _parse_catalog
        services = _parse_catalog(CATALOG_TTL)
        pubchem = next(s for s in services if "PubChem" in s.title)
        assert pubchem.endpoint_url == "https://qlever.cs.uni-freiburg.de/api/pubchem"

    def test_wikidata_endpoint_url(self):
        from agents.fabric_discovery import _parse_catalog
        services = _parse_catalog(CATALOG_TTL)
        wd = next(s for s in services if "Wikidata" in s.title)
        assert wd.endpoint_url == "https://qlever.cs.uni-freiburg.de/api/wikidata"

    def test_pubchem_has_example(self):
        from agents.fabric_discovery import _parse_catalog
        services = _parse_catalog(CATALOG_TTL)
        pubchem = next(s for s in services if "PubChem" in s.title)
        assert len(pubchem.examples) == 1
        assert "CHEMINF_000042" in pubchem.examples[0].sparql

    def test_wikidata_no_examples(self):
        from agents.fabric_discovery import _parse_catalog
        services = _parse_catalog(CATALOG_TTL)
        wd = next(s for s in services if "Wikidata" in s.title)
        assert len(wd.examples) == 0

    def test_pubchem_description(self):
        from agents.fabric_discovery import _parse_catalog
        services = _parse_catalog(CATALOG_TTL)
        pubchem = next(s for s in services if "PubChem" in s.title)
        assert pubchem.description == "PubChem RDF via QLever"

    def test_pubchem_vocabularies(self):
        from agents.fabric_discovery import _parse_catalog
        services = _parse_catalog(CATALOG_TTL)
        pubchem = next(s for s in services if "PubChem" in s.title)
        assert "http://semanticscience.org/resource/" in pubchem.vocabularies

    def test_empty_catalog_returns_empty(self):
        from agents.fabric_discovery import _parse_catalog
        services = _parse_catalog(EMPTY_CATALOG)
        assert services == []


class TestRoutingPlanWithExternalServices:
    def test_routing_plan_includes_external_section(self):
        from agents.fabric_discovery import FabricEndpoint, ExternalService, ExampleSummary
        ep = FabricEndpoint(
            base="http://localhost:8080",
            sparql_url="http://localhost:8080/sparql",
            void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
            external_services=[
                ExternalService(
                    title="QLever PubChem",
                    endpoint_url="https://qlever.cs.uni-freiburg.de/api/pubchem",
                    description="PubChem RDF",
                    vocabularies=["http://semanticscience.org/resource/"],
                    examples=[ExampleSummary(label="test", comment="", sparql="SELECT 1", target="")],
                ),
            ],
        )
        rp = ep.routing_plan
        assert "External SPARQL Services" in rp
        assert "QLever PubChem" in rp
        assert "qlever.cs.uni-freiburg.de/api/pubchem" in rp
        assert "SELECT 1" in rp

    def test_routing_plan_omits_section_when_no_services(self):
        from agents.fabric_discovery import FabricEndpoint
        ep = FabricEndpoint(
            base="http://localhost:8080",
            sparql_url="http://localhost:8080/sparql",
            void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
        )
        rp = ep.routing_plan
        assert "External SPARQL Services" not in rp
```

**Step 2: Run tests to verify they fail**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_catalog_discovery.py -v`
Expected: FAIL — `ImportError: cannot import name '_parse_catalog' from 'agents.fabric_discovery'`

**Step 3: Commit failing tests**

```bash
git add tests/pytest/unit/test_catalog_discovery.py
git commit -m "test: RED — catalog discovery unit tests for _parse_catalog + ExternalService"
```

---

## Task 3: Catalog Parsing in fabric_discovery.py — Implementation

Make the tests from Task 2 pass by adding `ExternalService`, `_parse_catalog`, and extending `FabricEndpoint.routing_plan`.

**Files:**
- Modify: `agents/fabric_discovery.py`

**Step 1: Add ExternalService dataclass and _parse_catalog function**

At the top of `agents/fabric_discovery.py`, after the existing `ExampleSummary` dataclass (~line 29), add:

```python
@dataclass
class ExternalService:
    title: str
    endpoint_url: str
    description: str
    vocabularies: list[str] = field(default_factory=list)
    examples: list[ExampleSummary] = field(default_factory=list)
```

Add `external_services` field to `FabricEndpoint` (after `vocab_graph_map`, ~line 48):

```python
    external_services: list[ExternalService] = field(default_factory=list)
```

Add the `_parse_catalog` function after the existing `_parse_examples` function (~line 248):

```python
DCAT = Namespace("http://www.w3.org/ns/dcat#")
FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")


def _parse_catalog(ttl: str) -> list[ExternalService]:
    """Extract dcat:DataService entries from catalog Turtle."""
    g = Graph()
    g.parse(data=ttl, format="turtle")
    services = []
    for s in g.subjects(RDF.type, DCAT.DataService):
        title = str(g.value(s, DCTERMS.title) or "")
        url = str(g.value(s, DCAT.endpointURL) or "")
        desc = str(g.value(s, DCTERMS.description) or "")
        vocabs = [str(v) for v in g.objects(s, VOID.vocabulary)]
        examples = []
        for ex_node in g.objects(s, SPEX.SparqlExample):
            label = str(g.value(ex_node, RDFS.label) or "")
            sparql = str(g.value(ex_node, SPEX.query) or "")
            if sparql:
                examples.append(ExampleSummary(label=label, comment="", sparql=sparql, target=""))
        if url:
            services.append(ExternalService(
                title=title, endpoint_url=url, description=desc,
                vocabularies=vocabs, examples=examples,
            ))
    return services
```

**Step 2: Extend routing_plan property**

In the `routing_plan` property of `FabricEndpoint`, after the SPARQL Examples block (before the final `return`), add:

```python
        if self.external_services:
            lines.append("")
            lines.append(f"External SPARQL Services ({len(self.external_services)}):")
            lines.append("  Use query_external_sparql(endpoint_url, query) to query these.")
            for svc in self.external_services:
                lines.append(f"")
                lines.append(f"  {svc.title}")
                lines.append(f"    URL: {svc.endpoint_url}")
                lines.append(f"    Description: {svc.description}")
                if svc.vocabularies:
                    lines.append(f"    Vocabularies: {', '.join(svc.vocabularies)}")
                for ex in svc.examples:
                    lines.append(f'    Example: "{ex.label}"')
                    for sparql_line in ex.sparql.strip().splitlines():
                        lines.append(f"      {sparql_line}")
```

**Step 3: Run tests to verify they pass**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_catalog_discovery.py -v`
Expected: all 13 tests PASS

**Step 4: Run full test suite for regression**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v`
Expected: all 205+ tests pass

**Step 5: Commit**

```bash
git add agents/fabric_discovery.py
git commit -m "feat: add ExternalService dataclass, _parse_catalog, and catalog routing plan section"
```

---

## Task 4: External Query Tool — Tests

Add unit tests for `make_external_query_tool` before implementing it.

**Files:**
- Create: `tests/pytest/unit/test_external_query_tool.py`

**Step 1: Write failing tests**

Create `tests/pytest/unit/test_external_query_tool.py`:

```python
"""Unit tests for make_external_query_tool — external SPARQL endpoint querying."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

import pytest
from unittest.mock import patch, MagicMock
from agents.fabric_discovery import FabricEndpoint, ExternalService, ExampleSummary


def _ep_with_services(urls=None):
    """Build a FabricEndpoint with external_services for testing."""
    if urls is None:
        urls = ["https://qlever.cs.uni-freiburg.de/api/pubchem"]
    services = [
        ExternalService(title=f"svc-{i}", endpoint_url=u, description="test", vocabularies=[], examples=[])
        for i, u in enumerate(urls)
    ]
    return FabricEndpoint(
        base="http://localhost:8080",
        sparql_url="http://localhost:8080/sparql",
        void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
        external_services=services,
    )


class TestMakeExternalQueryTool:
    def test_import(self):
        from agents.fabric_query import make_external_query_tool

    def test_returns_callable(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services()
        fn = make_external_query_tool(ep)
        assert callable(fn)

    def test_function_name(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services()
        fn = make_external_query_tool(ep)
        assert fn.__name__ == "query_external_sparql"

    def test_rejects_unlisted_url(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://allowed.example.org/sparql"])
        fn = make_external_query_tool(ep)
        result = fn("https://evil.example.org/sparql", "SELECT 1")
        assert "not in catalog" in result.lower() or "not allowed" in result.lower()

    def test_accepts_listed_url(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://qlever.cs.uni-freiburg.de/api/pubchem"])
        fn = make_external_query_tool(ep)
        # Mock httpx to avoid real network call
        mock_resp = MagicMock()
        mock_resp.text = '{"head":{"vars":["x"]},"results":{"bindings":[]}}'
        mock_resp.raise_for_status = MagicMock()
        with patch("agents.fabric_query.httpx.post", return_value=mock_resp):
            result = fn("https://qlever.cs.uni-freiburg.de/api/pubchem", "SELECT 1")
        assert "bindings" in result

    def test_truncates_large_results(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://example.org/sparql"])
        fn = make_external_query_tool(ep, max_chars=100)
        mock_resp = MagicMock()
        mock_resp.text = "x" * 200
        mock_resp.raise_for_status = MagicMock()
        with patch("agents.fabric_query.httpx.post", return_value=mock_resp):
            result = fn("https://example.org/sparql", "SELECT 1")
        assert "truncated" in result
        assert len(result) < 200

    def test_follows_redirects(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://example.org/sparql"])
        fn = make_external_query_tool(ep)
        mock_resp = MagicMock()
        mock_resp.text = '{"head":{"vars":[]},"results":{"bindings":[]}}'
        mock_resp.raise_for_status = MagicMock()
        with patch("agents.fabric_query.httpx.post", return_value=mock_resp) as mock_post:
            fn("https://example.org/sparql", "SELECT 1")
            call_kwargs = mock_post.call_args
            assert call_kwargs.kwargs.get("follow_redirects") is True

    def test_surfaces_http_errors(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://example.org/sparql"])
        fn = make_external_query_tool(ep)
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.raise_for_status.side_effect = Exception("HTTP 500")
        with patch("agents.fabric_query.httpx.post", return_value=mock_resp):
            result = fn("https://example.org/sparql", "SELECT 1")
        assert "error" in result.lower()

    def test_no_services_means_all_rejected(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services([])
        fn = make_external_query_tool(ep)
        result = fn("https://example.org/sparql", "SELECT 1")
        assert "not in catalog" in result.lower() or "not allowed" in result.lower()
```

**Step 2: Run tests to verify they fail**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_external_query_tool.py -v`
Expected: FAIL — `ImportError: cannot import name 'make_external_query_tool'`

**Step 3: Commit failing tests**

```bash
git add tests/pytest/unit/test_external_query_tool.py
git commit -m "test: RED — external query tool unit tests"
```

---

## Task 5: External Query Tool — Implementation

Make the tests from Task 4 pass.

**Files:**
- Modify: `agents/fabric_query.py`

**Step 1: Add make_external_query_tool**

At the end of `agents/fabric_query.py` (after `make_fabric_query_tool`), add:

```python
def make_external_query_tool(
    ep: FabricEndpoint,
    max_chars: int = 10_000,
) -> Callable:
    """Return a query_external_sparql(endpoint_url, query) function for catalog-listed endpoints.

    Only allows URLs that appear in ep.external_services (safety gate).
    Follows redirects (QLever returns 308). Same error-surfacing pattern as sparql_query.
    """
    allowed = {svc.endpoint_url for svc in ep.external_services}

    def query_external_sparql(endpoint_url: str, query: str) -> str:
        """Execute SPARQL against an external endpoint listed in the fabric catalog.
        Returns JSON results. Only catalog-listed endpoint URLs are allowed."""
        if endpoint_url not in allowed:
            return (
                f"Error: endpoint {endpoint_url} not in catalog. "
                f"Allowed endpoints: {', '.join(sorted(allowed)) or 'none'}"
            )
        try:
            r = httpx.post(
                endpoint_url,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30.0,
                follow_redirects=True,
            )
            r.raise_for_status()
            txt = r.text
            if len(txt) > max_chars:
                return txt[:max_chars] + f"\n... truncated ({len(txt)} total chars)."
            return txt
        except httpx.HTTPStatusError as e:
            return f"External SPARQL error (HTTP {e.response.status_code}): {e.response.text[:500]}"
        except Exception as e:
            return f"External SPARQL error: {e}"
    return query_external_sparql
```

**Step 2: Run tests to verify they pass**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_external_query_tool.py -v`
Expected: all 9 tests PASS

**Step 3: Run full test suite for regression**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v`
Expected: all tests pass

**Step 4: Commit**

```bash
git add agents/fabric_query.py
git commit -m "feat: add make_external_query_tool for catalog-listed external SPARQL endpoints"
```

---

## Task 6: Harness Metrics — External Query Tracking

Add `used_external_query` counter to `FabricMetrics` and extract it from trajectory.

**Files:**
- Modify: `experiments/fabric_navigation/dspy_eval_harness.py`

**Step 1: Add field to FabricMetrics**

In `FabricMetrics` dataclass (~line 42), add after `final_named_graph`:

```python
    external_query_attempts: int          # calls to query_external_sparql
    external_endpoints_queried: list[str] # distinct external endpoint URLs targeted
```

**Step 2: Extract external query metrics in _extract_fabric_metrics**

In `_extract_fabric_metrics` (~line 129), add tracking variables after existing ones:

```python
    external_attempts = 0
    external_endpoints: list[str] = []
```

Inside the loop, add detection (after the `sparql_query` detection block):

```python
        # Did agent call query_external_sparql?
        if 'query_external_sparql' in code:
            external_attempts += 1
            # Extract endpoint URL from call: query_external_sparql("https://...", ...)
            import re as _re
            url_match = _re.search(r'query_external_sparql\(\s*["\']([^"\']+)["\']', code)
            if url_match and url_match.group(1) not in external_endpoints:
                external_endpoints.append(url_match.group(1))
```

In the `return FabricMetrics(...)` call, add the new fields:

```python
        external_query_attempts=external_attempts,
        external_endpoints_queried=external_endpoints,
```

**Step 3: Add meanExternalQueries to AggregateStats**

In `AggregateStats` dataclass (~line 79), add:

```python
    meanExternalQueries: float
```

In `compute_aggregate_stats` (~line 232), add before the `return`:

```python
    mean_ext = statistics.mean([r.fabric.external_query_attempts for r in fabric_results]) if fabric_results else 0.0
```

And add `meanExternalQueries=mean_ext` to the return.

**Step 4: Run full test suite**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v`
Expected: all tests pass (no tests directly depend on FabricMetrics construction args)

**Step 5: Commit**

```bash
git add experiments/fabric_navigation/dspy_eval_harness.py
git commit -m "feat: add external_query_attempts metric to FabricMetrics"
```

---

## Task 7: Phase 7 Task File

Create the 6 experiment tasks as JSON.

**Files:**
- Create: `experiments/fabric_navigation/tasks/phase7-catalog.json`

**Step 1: Create task file**

Create `experiments/fabric_navigation/tasks/phase7-catalog.json`:

```json
[
  {
    "id": "pubchem-molecular-formula",
    "query": "What is the molecular formula of aspirin (PubChem CID 2244)?",
    "context": "http://localhost:8080",
    "expected": ["C9H8O4"],
    "metadata": {
      "description": "Pure external: agent must discover PubChem endpoint from catalog, construct SPARQL using sio:SIO_000008 -> CHEMINF_000042 -> sio:SIO_000300 pattern.",
      "task_type": "external",
      "target_endpoint": "pubchem"
    }
  },
  {
    "id": "wikidata-potentiostat-manufacturer",
    "query": "Who manufactures potentiostats? Use Wikidata to find instrument manufacturers.",
    "context": "http://localhost:8080",
    "expected": ["Metrohm", "Gamry", "Bio-Logic"],
    "metadata": {
      "description": "Pure external: agent must discover Wikidata endpoint from catalog, adapt manufacturer example query with wdt:P176.",
      "task_type": "external",
      "target_endpoint": "wikidata"
    }
  },
  {
    "id": "osm-notre-dame-location",
    "query": "Find the University of Notre Dame in OpenStreetMap data.",
    "context": "http://localhost:8080",
    "expected": ["Notre Dame"],
    "metadata": {
      "description": "Pure external: agent must discover OSM endpoint from catalog, use osmkey:name FILTER CONTAINS pattern.",
      "task_type": "external",
      "target_endpoint": "osm"
    }
  },
  {
    "id": "obs-compound-formula",
    "query": "What is the molecular formula of the compound measured in observation obs-p7-001?",
    "context": "http://localhost:8080",
    "expected": ["C9H8O4"],
    "metadata": {
      "setup": {
        "type": "sparql_insert",
        "graph": "http://localhost:8080/graph/observations",
        "extra_graphs": ["http://localhost:8080/graph/entities"],
        "data": [
          {
            "subject": "http://localhost:8080/entity/obs-p7-001",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-cv-p7",
            "sosa:hasSimpleResult": "0.45",
            "sosa:resultTime": "2026-02-26T09:00:00Z",
            "sio:is-about": "http://localhost:8080/entity/compound-aspirin-p7"
          },
          {
            "record_type": "sensor",
            "graph": "http://localhost:8080/graph/entities",
            "subject": "http://localhost:8080/entity/sensor-cv-p7",
            "rdfs:label": "CV Potentiostat P7"
          },
          {
            "record_type": "sensor",
            "graph": "http://localhost:8080/graph/entities",
            "subject": "http://localhost:8080/entity/compound-aspirin-p7",
            "rdfs:label": "Aspirin (CID 2244)"
          }
        ]
      },
      "description": "Mixed: agent must query local for observation -> is-about -> compound label, extract CID 2244, then query PubChem for molecular formula. The compound entity has label with CID hint.",
      "task_type": "mixed",
      "target_endpoint": "pubchem"
    }
  },
  {
    "id": "obs-sensor-manufacturer",
    "query": "Who manufactured the sensor used in observation obs-p7-002?",
    "context": "http://localhost:8080",
    "expected": ["Metrohm Autolab"],
    "metadata": {
      "setup": {
        "type": "sparql_insert",
        "graph": "http://localhost:8080/graph/observations",
        "extra_graphs": ["http://localhost:8080/graph/entities"],
        "data": [
          {
            "subject": "http://localhost:8080/entity/obs-p7-002",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-potentiostat-p7",
            "sosa:hasSimpleResult": "1.23",
            "sosa:resultTime": "2026-02-26T10:00:00Z"
          },
          {
            "record_type": "sensor",
            "graph": "http://localhost:8080/graph/entities",
            "subject": "http://localhost:8080/entity/sensor-potentiostat-p7",
            "rdfs:label": "PGSTAT204 Potentiostat"
          }
        ]
      },
      "description": "Mixed: agent queries local to find sensor label, then may query Wikidata for manufacturer info. Answer (Metrohm Autolab) is NOT in local data — agent must use Wikidata to find that PGSTAT204 is made by Metrohm Autolab.",
      "task_type": "mixed",
      "target_endpoint": "wikidata"
    }
  },
  {
    "id": "obs-lab-location",
    "query": "Where is the laboratory that hosts the sensor from observation obs-p7-003?",
    "context": "http://localhost:8080",
    "expected": ["Notre Dame"],
    "metadata": {
      "setup": {
        "type": "sparql_insert",
        "graph": "http://localhost:8080/graph/observations",
        "extra_graphs": ["http://localhost:8080/graph/entities"],
        "data": [
          {
            "subject": "http://localhost:8080/entity/obs-p7-003",
            "sosa:madeBySensor": "http://localhost:8080/entity/sensor-eis-p7",
            "sosa:hasSimpleResult": "542.8",
            "sosa:resultTime": "2026-02-26T11:00:00Z"
          },
          {
            "record_type": "sensor",
            "graph": "http://localhost:8080/graph/entities",
            "subject": "http://localhost:8080/entity/sensor-eis-p7",
            "rdfs:label": "EIS Spectrometer P7",
            "sosa:isHostedBy": "http://localhost:8080/entity/platform-ndechem-p7",
            "sosa:isHostedBy-label": "Notre Dame Electrochemistry Lab"
          }
        ]
      },
      "description": "Mixed: agent queries local sensor -> isHostedBy -> platform label. Answer (Notre Dame) is available locally. Agent may optionally enrich via OSM.",
      "task_type": "mixed",
      "target_endpoint": "osm"
    }
  }
]
```

**Step 2: Validate JSON syntax**

Run: `python3 -c "import json; json.load(open('experiments/fabric_navigation/tasks/phase7-catalog.json'))" && echo "Valid JSON"`
Expected: `Valid JSON`

**Step 3: Commit**

```bash
git add experiments/fabric_navigation/tasks/phase7-catalog.json
git commit -m "feat: add Phase 7 catalog discovery task definitions (6 tasks)"
```

---

## Task 8: Wire Phase 7 into run_experiment.py

Add phase7a/7b feature flags and wire catalog discovery + external query tool into the experiment runner.

**Files:**
- Modify: `experiments/fabric_navigation/run_experiment.py`

**Step 1: Add phase7 entries to PHASE_FEATURES**

In `PHASE_FEATURES` dict (~line 47), add after the `phase6b-rdfs-routes` entry:

```python
    "phase7a-no-catalog": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths",
    ],
    "phase7b-catalog": [
        "void-sd", "void-urispace", "void-graph-inventory",
        "shacl-prefixes", "shacl-class-pattern", "shacl-agent-hints",
        "sparql-examples", "sparql-examples-extended", "enhanced-routing-plan",
        "tbox-graph-paths",
        "catalog-in-sd", "external-query-tool",
    ],
```

**Step 2: Add import for make_external_query_tool**

At the top (~line 37), add to the existing imports:

```python
from agents.fabric_query import make_fabric_query_tool, make_external_query_tool
```

**Step 3: Add catalog fetch + import for _parse_catalog**

At the top (~line 36), add:

```python
from agents.fabric_discovery import discover_endpoint, _parse_catalog
```

(Replace the existing `from agents.fabric_discovery import discover_endpoint` line.)

**Step 4: Wire catalog into main()**

In `main()`, after `ep = discover_endpoint(GATEWAY)` (~line 316), add:

```python
    # Fetch catalog for phase7 — parse external services
    features = PHASE_FEATURES[args.phase]
    if 'catalog-in-sd' in features:
        try:
            import httpx as _httpx
            cat_r = _httpx.get(f"{GATEWAY}/.well-known/catalog",
                               headers={"Accept": "text/turtle"}, timeout=10.0)
            cat_r.raise_for_status()
            ep.external_services = _parse_catalog(cat_r.text)
            log.info("Catalog: %d external services", len(ep.external_services))
        except Exception as exc:
            log.warning("Catalog fetch failed: %s", exc)
```

**Step 5: Wire external query tool into rlm_factory**

In `rlm_factory()` (~line 318), after the existing `if "rdfs-routes"` block, add:

```python
        if "external-query-tool" in features:
            tools.append(make_external_query_tool(ep))
```

**Step 6: Add external tool hint to kwarg_builder**

Define the hint string (after `_RDFS_TOOL_HINT`, ~line 361):

```python
    _EXTERNAL_TOOL_HINT = (
        "\n\nEXTERNAL QUERY TOOL (call from REPL code):\n"
        "  query_external_sparql(endpoint_url: str, query: str) -> str\n"
        "    Queries an external SPARQL endpoint listed in the catalog above.\n"
        "    Only catalog-listed endpoint URLs are allowed.\n"
        "    Returns JSON SPARQL results. Follows HTTP redirects.\n"
        "\n"
        "    Example:\n"
        "      result = query_external_sparql(\n"
        "          'https://qlever.cs.uni-freiburg.de/api/pubchem',\n"
        "          'PREFIX sio: <http://semanticscience.org/resource/>\\n'\n"
        "          'SELECT ?val WHERE { <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID2244> sio:SIO_000008 ?a . ?a sio:SIO_000300 ?val } LIMIT 5'\n"
        "      )\n"
        "      print(result)\n"
    )
```

In `kwarg_builder` (~line 363), after the `rdfs-routes` hint block, add:

```python
        if 'external-query-tool' in features:
            sd = sd + _EXTERNAL_TOOL_HINT
```

**Step 7: Run a dry validation that phases parse**

Run:
```bash
~/uvws/.venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from experiments.fabric_navigation.run_experiment import PHASE_FEATURES
assert 'phase7a-no-catalog' in PHASE_FEATURES
assert 'phase7b-catalog' in PHASE_FEATURES
assert 'catalog-in-sd' in PHASE_FEATURES['phase7b-catalog']
assert 'external-query-tool' in PHASE_FEATURES['phase7b-catalog']
print('Phase 7 features validated')
"
```
Expected: `Phase 7 features validated`

**Step 8: Run full test suite**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v`
Expected: all tests pass

**Step 9: Commit**

```bash
git add experiments/fabric_navigation/run_experiment.py
git commit -m "feat: wire Phase 7 catalog discovery into experiment runner"
```

---

## Task 9: Integration Verification — Docker + Dry Run

Verify the full stack works end-to-end: Docker rebuild with fixed templates, catalog accessible, dry-run both phases.

**Files:**
- None modified — this is verification only

**Step 1: Docker rebuild**

```bash
cd ~/dev/git/LA3D/agents/cogitarelink-fabric
docker compose down -v && docker compose build && docker compose up -d
```

Wait for bootstrap:
```bash
sleep 20
docker compose logs fabric-node 2>&1 | tail -5
```
Expected: logs show bootstrap complete, "External endpoints (QLever Wikidata/PubChem/OSM): loaded"

**Step 2: Verify catalog has corrected examples**

```bash
curl -s http://localhost:8080/.well-known/catalog -H "Accept: text/turtle" | grep "CHEMINF_000042"
```
Expected: the corrected PubChem query appears

**Step 3: Run existing test suites**

```bash
~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v
make -C tests test-all
```
Expected: all unit tests pass, all HURL tests pass

**Step 4: Verify external query tool works against live QLever**

```bash
~/uvws/.venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from agents.fabric_discovery import discover_endpoint, _parse_catalog, ExternalService
from agents.fabric_query import make_external_query_tool
import httpx

ep = discover_endpoint('http://localhost:8080')
cat = httpx.get('http://localhost:8080/.well-known/catalog', headers={'Accept': 'text/turtle'}, timeout=10.0)
ep.external_services = _parse_catalog(cat.text)
print(f'External services: {len(ep.external_services)}')

fn = make_external_query_tool(ep)

# Test PubChem
result = fn('https://qlever.cs.uni-freiburg.de/api/pubchem',
    'PREFIX sio: <http://semanticscience.org/resource/> SELECT ?val WHERE { <http://rdf.ncbi.nlm.nih.gov/pubchem/compound/CID2244> sio:SIO_000008 ?attr . ?attr a sio:CHEMINF_000042 ; sio:SIO_000300 ?val } LIMIT 1')
print(f'PubChem: {result[:200]}')

# Test Wikidata
result = fn('https://qlever.cs.uni-freiburg.de/api/wikidata',
    'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT ?item ?label WHERE { ?item rdfs:label \"potentiostat\"@en } LIMIT 3')
print(f'Wikidata: {result[:200]}')
"
```
Expected: prints 3 external services, PubChem returns molecular formula, Wikidata returns results

**Step 5: Commit (if any Docker/template fixes were needed)**

Only if fixes were required — otherwise skip.

---

## Task 10: Run Phase 7 Experiments

Execute both experiment phases and analyze results.

**Files:**
- None modified — this is experiment execution

**Step 1: Run phase7a (control — no catalog)**

```bash
cd ~/dev/git/LA3D/agents/cogitarelink-fabric
~/uvws/.venv/bin/python experiments/fabric_navigation/run_experiment.py \
    --tasks experiments/fabric_navigation/tasks/phase7-catalog.json \
    --phase phase7a-no-catalog \
    --output experiments/fabric_navigation/results/ \
    --model anthropic/claude-sonnet-4-6 \
    --max-iterations 15 \
    --verbose
```

Expected: pure external tasks score 0.0, mixed tasks with local answers may score higher.

**Step 2: Run phase7b (treatment — catalog + external tool)**

```bash
~/uvws/.venv/bin/python experiments/fabric_navigation/run_experiment.py \
    --tasks experiments/fabric_navigation/tasks/phase7-catalog.json \
    --phase phase7b-catalog \
    --output experiments/fabric_navigation/results/ \
    --model anthropic/claude-sonnet-4-6 \
    --max-iterations 15 \
    --verbose
```

Expected: all 6 tasks score 1.0 if catalog discovery works.

**Step 3: Compare results**

```bash
~/uvws/.venv/bin/python -c "
import json, glob
files = sorted(glob.glob('experiments/fabric_navigation/results/phase7*.json'))
for f in files:
    data = json.load(open(f))
    agg = data['aggregate']
    print(f'{data[\"fabric_phase\"]:25s} score={agg[\"meanScore\"]:.3f} iter={agg[\"meanIterations\"]:.1f} sparql={agg[\"meanSparqlAttempts\"]:.1f} ext={agg.get(\"meanExternalQueries\", 0):.1f}')
    for r in data['results']:
        ext = r.get('fabric', {}).get('external_query_attempts', 0)
        print(f'  {r[\"taskId\"]:35s} score={r[\"score\"]:.1f} iter={r[\"iterations\"]} ext_queries={ext}')
"
```

**Step 4: Commit results**

```bash
git add experiments/fabric_navigation/results/phase7*.json
git add experiments/fabric_navigation/trajectories/phase7*.jsonl
git commit -m "results: Phase 7 catalog discovery experiment results"
```

---

## Dependency Graph

```
1 (fix templates)
  → 2 (catalog tests RED) → 3 (catalog impl GREEN)
  → 4 (ext tool tests RED) → 5 (ext tool impl GREEN)
  → 6 (metrics)
  → 7 (task file)
  → 8 (wiring — depends on 3, 5, 6, 7)
    → 9 (integration verification — depends on 1, 8)
      → 10 (run experiments — depends on 9)
```

Tasks 2-3, 4-5, 6, and 7 can run in parallel after Task 1.
