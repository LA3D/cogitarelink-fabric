# SD Routing Annotations + SIO Schema Fix — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the SIO schema gap (missing `rdfs:range xsd:float` on `sio:has-value`), add `fabric:graphPurpose` routing annotations to the VoID/SD so agents know which tool to use per graph, and update experiment globalDocs with tool selection heuristics.

**Architecture:** Four changes across the stack: (1) single triple added to `sio.ttl`, (2) new `fabric:graphPurpose` DatatypeProperty in `fabric.ttl`, (3) routing annotations + `rdfs:comment` on every named graph in `void_templates.py` (both Turtle and JSON-LD), (4) globalDocs in `global-docs.ts` updated with tool selection heuristic referencing SD graph purposes.

**Tech Stack:** Python (rdflib for tests), TypeScript (vitest for JS tests), Turtle RDF

---

### Task 1: Fix SIO schema gap — add `rdfs:range xsd:float` to `sio:has-value`

**Files:**
- Modify: `ontology/sio.ttl:94-97`

**Step 1: Write the failing test**

Create `tests/pytest/unit/test_sio_has_value_range.py`:

```python
"""Test sio:has-value has rdfs:range xsd:float (Phase 2.5b schema gap fix)."""
from rdflib import Graph, Namespace, URIRef, XSD

SIO = Namespace("http://semanticscience.org/resource/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")


def test_sio_has_value_has_float_range():
    g = Graph()
    g.parse("ontology/sio.ttl", format="turtle")
    ranges = list(g.objects(SIO["has-value"], RDFS.range))
    assert URIRef(str(XSD.float)) in [URIRef(str(r)) for r in ranges], \
        "sio:has-value must have rdfs:range xsd:float"


def test_sio_has_value_is_datatype_property():
    from rdflib.namespace import OWL, RDF
    g = Graph()
    g.parse("ontology/sio.ttl", format="turtle")
    types = list(g.objects(SIO["has-value"], RDF.type))
    assert OWL.DatatypeProperty in types
```

**Step 2: Run test to verify it fails**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_sio_has_value_range.py -v`
Expected: `test_sio_has_value_has_float_range` FAILS (range not declared), `test_sio_has_value_is_datatype_property` PASSES.

**Step 3: Add the missing triple**

In `ontology/sio.ttl`, change lines 94-97 from:

```turtle
sio:has-value a owl:DatatypeProperty ;             # SIO_000300
    rdfs:label "has value"@en ;
    rdfs:comment "Relates an attribute to its value."@en ;
    rdfs:domain sio:Attribute .
```

to:

```turtle
sio:has-value a owl:DatatypeProperty ;             # SIO_000300
    rdfs:label "has value"@en ;
    rdfs:comment "Relates an attribute to its value."@en ;
    rdfs:domain sio:Attribute ;
    rdfs:range xsd:float .
```

**Step 4: Run test to verify it passes**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_sio_has_value_range.py -v`
Expected: Both PASS.

**Step 5: Commit**

```bash
git add ontology/sio.ttl tests/pytest/unit/test_sio_has_value_range.py
git commit -m "[Agent: Claude] fix: add rdfs:range xsd:float to sio:has-value (Phase 2.5b schema gap)"
```

---

### Task 2: Add `fabric:graphPurpose` property to fabric vocabulary

**Files:**
- Modify: `ontology/fabric.ttl:441-448`

**Step 1: Write the failing test**

Create `tests/pytest/unit/test_fabric_graph_purpose.py`:

```python
"""Test fabric:graphPurpose property exists in fabric vocabulary."""
from rdflib import Graph, Namespace, URIRef, XSD
from rdflib.namespace import RDF, OWL, RDFS

FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")


def test_graph_purpose_is_datatype_property():
    g = Graph()
    g.parse("ontology/fabric.ttl", format="turtle")
    types = list(g.objects(FABRIC.graphPurpose, RDF.type))
    assert OWL.DatatypeProperty in types, "fabric:graphPurpose must be owl:DatatypeProperty"


def test_graph_purpose_has_label():
    g = Graph()
    g.parse("ontology/fabric.ttl", format="turtle")
    labels = list(g.objects(FABRIC.graphPurpose, RDFS.label))
    assert len(labels) >= 1, "fabric:graphPurpose must have rdfs:label"


def test_graph_purpose_has_range_string():
    g = Graph()
    g.parse("ontology/fabric.ttl", format="turtle")
    ranges = list(g.objects(FABRIC.graphPurpose, RDFS.range))
    assert URIRef(str(XSD.string)) in [URIRef(str(r)) for r in ranges], \
        "fabric:graphPurpose must have rdfs:range xsd:string"
```

**Step 2: Run test to verify it fails**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_fabric_graph_purpose.py -v`
Expected: All 3 FAIL (property doesn't exist yet).

**Step 3: Add `fabric:graphPurpose` to fabric.ttl**

Insert before the `# END OF VOCABULARY` block (after `fabric:writable`, before line 442):

```turtle
fabric:graphPurpose
    a owl:DatatypeProperty ;
    rdfs:label        "graph purpose"@en ;
    skos:definition   "Classifies a named graph by its role in the D9 four-layer KR architecture. Values: 'instances' (L3-L4 data — query with SPARQL), 'schema' (L2 TBox — navigate with JSON-LD or SPARQL CONSTRUCT), 'metadata' (administrative/provenance). Guides agent tool selection in heterogeneous fabrics."@en ;
    rdfs:range        xsd:string ;
    rdfs:isDefinedBy  <https://w3id.org/cogitarelink/fabric> ;
    dct:created       "2026-03-11"^^xsd:date .
```

Also update the version comment at the end to `Version: 0.4.0  |  Date: 2026-03-11` and increment `voaf:propertyNumber` from `"12"` to `"13"`.

**Step 4: Run test to verify it passes**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_fabric_graph_purpose.py -v`
Expected: All 3 PASS.

**Step 5: Commit**

```bash
git add ontology/fabric.ttl tests/pytest/unit/test_fabric_graph_purpose.py
git commit -m "[Agent: Claude] feat: add fabric:graphPurpose property to vocabulary (D31 routing)"
```

---

### Task 3: Add routing annotations to VoID Turtle template

**Files:**
- Modify: `fabric/node/void_templates.py:17-72` (VOID_TURTLE named graphs section)

**Step 1: Write the failing test**

Create `tests/pytest/unit/test_void_graph_purpose.py`:

```python
"""Test fabric:graphPurpose routing annotations on VoID named graphs."""
from rdflib import Graph, Namespace, Literal, XSD

SD = Namespace("http://www.w3.org/ns/sparql-service-description#")
FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")

BASE = "https://bootstrap.cogitarelink.ai"


def _parse():
    from fabric.node.void_templates import VOID_TURTLE
    g = Graph()
    g.parse(data=VOID_TURTLE.format(base=BASE), format="turtle")
    return g


def _get_ng(g, substring):
    """Find the blank node for a named graph whose sd:name contains substring."""
    for s in g.subjects(SD.name, None):
        name = str(g.value(s, SD.name))
        if substring in name:
            return s
    return None


def test_observations_graph_has_purpose_instances():
    g = _parse()
    ng = _get_ng(g, "/graph/observations")
    assert ng is not None
    purpose = g.value(ng, FABRIC.graphPurpose)
    assert purpose is not None, "/graph/observations must have fabric:graphPurpose"
    assert str(purpose) == "instances"


def test_ontology_sio_has_purpose_schema():
    g = _parse()
    ng = _get_ng(g, "/ontology/sio")
    assert ng is not None
    purpose = g.value(ng, FABRIC.graphPurpose)
    assert purpose is not None, "/ontology/sio must have fabric:graphPurpose"
    assert str(purpose) == "schema"


def test_metadata_graph_has_purpose_metadata():
    g = _parse()
    ng = _get_ng(g, "/graph/metadata")
    assert ng is not None
    purpose = g.value(ng, FABRIC.graphPurpose)
    assert purpose is not None, "/graph/metadata must have fabric:graphPurpose"
    assert str(purpose) == "metadata"


def test_all_named_graphs_have_comment():
    g = _parse()
    for ng_node in g.subjects(SD.name, None):
        name = str(g.value(ng_node, SD.name))
        comment = g.value(ng_node, RDFS.comment)
        assert comment is not None, f"{name} sd:namedGraph must have rdfs:comment"


def test_observations_graph_comment_mentions_sparql():
    g = _parse()
    ng = _get_ng(g, "/graph/observations")
    comment = str(g.value(ng, RDFS.comment))
    assert "SPARQL" in comment or "sparql" in comment, \
        "Observations graph comment should mention SPARQL as access method"


def test_ontology_graph_comment_mentions_jsonld():
    g = _parse()
    ng = _get_ng(g, "/ontology/sosa")
    comment = str(g.value(ng, RDFS.comment))
    assert "JSON-LD" in comment or "json-ld" in comment or "dereference" in comment.lower(), \
        "Ontology graph comment should mention JSON-LD or dereference as access option"
```

**Step 2: Run test to verify it fails**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_void_graph_purpose.py -v`
Expected: All FAIL (no fabric:graphPurpose or rdfs:comment on named graphs).

**Step 3: Add routing annotations to VOID_TURTLE**

In `void_templates.py`, update each `sd:namedGraph` entry in `VOID_TURTLE` to include `fabric:graphPurpose` and `rdfs:comment`. The data graphs get `"instances"`, ontology graphs get `"schema"`, metadata gets `"metadata"`.

Replace the entire `sd:defaultDataset` block (lines 20-72) with:

```turtle
    sd:defaultDataset [
        a sd:Dataset ;
        sd:namedGraph [
            sd:name <{base}/graph/observations> ;
            dct:title "Observations" ;
            dct:conformsTo <https://w3id.org/cogitarelink/fabric#ObservationShape> ;
            fabric:graphPurpose "instances" ;
            rdfs:comment "Instance data: SOSA observations with measurement results. Query with SPARQL SELECT/CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/graph/entities> ;
            dct:title "Entities" ;
            dct:conformsTo <https://w3id.org/cogitarelink/fabric#EntityShape> ;
            dct:description "Sensor, platform, and observable-property descriptions (sosa:Sensor, sosa:Platform, sosa:ObservableProperty)." ;
            fabric:graphPurpose "instances" ;
            rdfs:comment "Instance data: sensor and platform descriptions. Query with SPARQL SELECT/CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/graph/metadata> ;
            dct:title "Metadata" ;
            dct:description "Node-level metadata, provenance records, and administrative triples." ;
            fabric:graphPurpose "metadata" ;
            rdfs:comment "Administrative metadata and provenance. Query with SPARQL when needed for audit trails." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/sosa> ;
            void:vocabulary <http://www.w3.org/ns/sosa/> ;
            prov:wasDerivedFrom <http://www.w3.org/ns/sosa/> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C SOSA ontology (cached). Explore with JSON-LD via /ontology/sosa or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/sio> ;
            void:vocabulary <http://semanticscience.org/resource/> ;
            prov:wasDerivedFrom <http://semanticscience.org/resource/> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "SIO ontology subset (cached). Explore with JSON-LD via /ontology/sio or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/prov> ;
            void:vocabulary <http://www.w3.org/ns/prov#> ;
            prov:wasDerivedFrom <http://www.w3.org/ns/prov#> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C PROV-O ontology (cached). Explore with JSON-LD via /ontology/prov or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/time> ;
            void:vocabulary <http://www.w3.org/2006/time#> ;
            prov:wasDerivedFrom <http://www.w3.org/2006/time#> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C OWL-Time ontology (cached). Explore with JSON-LD via /ontology/time or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/fabric> ;
            void:vocabulary <https://w3id.org/cogitarelink/fabric#> ;
            prov:wasDerivedFrom <https://w3id.org/cogitarelink/fabric#> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "Cogitarelink Fabric vocabulary (cached). Explore with JSON-LD via /ontology/fabric or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/prof> ;
            void:vocabulary <http://www.w3.org/ns/dx/prof/> ;
            prov:wasDerivedFrom <http://www.w3.org/ns/dx/prof/> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C Profiles Vocabulary (cached). Explore with JSON-LD via /ontology/prof or query with SPARQL CONSTRUCT." ;
        ] ;
        sd:namedGraph [
            sd:name <{base}/ontology/role> ;
            void:vocabulary <http://www.w3.org/ns/dx/prof/role/> ;
            prov:wasDerivedFrom <http://www.w3.org/ns/dx/prof/role/> ;
            fabric:graphPurpose "schema" ;
            rdfs:comment "W3C PROF role types (cached). Explore with JSON-LD via /ontology/role or query with SPARQL CONSTRUCT." ;
        ] ;
    ] .
```

Also add `rdfs:` prefix to the `@prefix` block at the top of `VOID_TURTLE` (line 8 area):

```turtle
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
```

**Step 4: Run test to verify it passes**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_void_graph_purpose.py -v`
Expected: All 6 PASS.

**Step 5: Run existing VoID tests to verify no regressions**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_void_*.py -v`
Expected: All existing tests PASS. Some may need minor updates if they count named graph properties or check exact structures.

**Step 6: Commit**

```bash
git add fabric/node/void_templates.py tests/pytest/unit/test_void_graph_purpose.py
git commit -m "[Agent: Claude] feat: add fabric:graphPurpose routing annotations to VoID SD"
```

---

### Task 4: Update VoID JSON-LD template with matching annotations

**Files:**
- Modify: `fabric/node/void_templates.py:122-210` (VOID_JSONLD section)

**Step 1: Write the failing test**

Add to `tests/pytest/unit/test_void_graph_purpose.py`:

```python
def test_jsonld_observations_has_graph_purpose():
    import json
    from fabric.node.void_templates import VOID_JSONLD
    doc = json.loads(VOID_JSONLD.format(base=BASE))
    service = [n for n in doc["@graph"] if "sd:Service" in str(n.get("@type", []))][0]
    ngs = service["sd:defaultDataset"]["sd:namedGraph"]
    obs = next(ng for ng in ngs if "graph/observations" in ng["sd:name"]["@id"])
    assert obs.get("fabric:graphPurpose") == "instances"


def test_jsonld_ontology_has_graph_purpose():
    import json
    from fabric.node.void_templates import VOID_JSONLD
    doc = json.loads(VOID_JSONLD.format(base=BASE))
    service = [n for n in doc["@graph"] if "sd:Service" in str(n.get("@type", []))][0]
    ngs = service["sd:defaultDataset"]["sd:namedGraph"]
    sio = next(ng for ng in ngs if "ontology/sio" in ng["sd:name"]["@id"])
    assert sio.get("fabric:graphPurpose") == "schema"


def test_jsonld_all_named_graphs_have_comment():
    import json
    from fabric.node.void_templates import VOID_JSONLD
    doc = json.loads(VOID_JSONLD.format(base=BASE))
    service = [n for n in doc["@graph"] if "sd:Service" in str(n.get("@type", []))][0]
    ngs = service["sd:defaultDataset"]["sd:namedGraph"]
    for ng in ngs:
        assert "rdfs:comment" in ng, f"Missing rdfs:comment on {ng['sd:name']['@id']}"
```

**Step 2: Run test to verify it fails**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_void_graph_purpose.py::test_jsonld_observations_has_graph_purpose -v`
Expected: FAIL.

**Step 3: Update VOID_JSONLD**

Add `"rdfs"` prefix to `@context`, then add `"fabric:graphPurpose"` and `"rdfs:comment"` to each named graph entry in the JSON-LD template. Match the Turtle values exactly.

**Step 4: Run all graph purpose tests**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_void_graph_purpose.py -v`
Expected: All 9 PASS.

**Step 5: Run all VoID tests for regressions**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/test_void_*.py -v`
Expected: All PASS.

**Step 6: Commit**

```bash
git add fabric/node/void_templates.py tests/pytest/unit/test_void_graph_purpose.py
git commit -m "[Agent: Claude] feat: add routing annotations to VoID JSON-LD template"
```

---

### Task 5: Update globalDocs with tool selection heuristic

**Files:**
- Modify: `experiments/node-rlm-fabric/global-docs.ts:39-96` (JSONLD_DOCS)

**Step 1: Write the failing test**

Add to `experiments/node-rlm-fabric/global-docs.test.ts` (create if needed):

```typescript
import { describe, it, expect } from "vitest";
import { JSONLD_DOCS, BASELINE_DOCS, getGlobalDocs } from "./global-docs.js";

describe("globalDocs tool selection heuristic", () => {
  it("JSONLD_DOCS mentions graphPurpose", () => {
    expect(JSONLD_DOCS).toContain("graphPurpose");
  });

  it("JSONLD_DOCS mentions schema graphs use JSON-LD", () => {
    expect(JSONLD_DOCS).toMatch(/schema.*JSON-LD|JSON-LD.*schema/i);
  });

  it("JSONLD_DOCS mentions instance graphs use SPARQL", () => {
    expect(JSONLD_DOCS).toMatch(/instance.*SPARQL|SPARQL.*instance/i);
  });

  it("BASELINE_DOCS does not mention graphPurpose", () => {
    expect(BASELINE_DOCS).not.toContain("graphPurpose");
  });

  it("getGlobalDocs returns JSONLD_DOCS for js-jsonld", () => {
    expect(getGlobalDocs("js-jsonld")).toBe(JSONLD_DOCS);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd experiments/node-rlm-fabric && npx vitest run global-docs.test.ts`
Expected: Tests about graphPurpose FAIL.

**Step 3: Update JSONLD_DOCS**

Replace the `### Discovery Strategy` section in `JSONLD_DOCS` with a version that includes a tool selection heuristic:

```typescript
### Tool Selection (read from service description)

The service description (from fetchVoID) annotates each named graph with fabric:graphPurpose:

- **"instances"** (e.g., /graph/observations, /graph/entities): Use comunica_query() with SPARQL SELECT
- **"schema"** (e.g., /ontology/sosa, /ontology/sio): Explore with fetchJsonLd() + jsonld.expand(), or query with comunica_query() SPARQL CONSTRUCT
- **"metadata"** (e.g., /graph/metadata): Query with comunica_query() when needed

### Discovery Strategy

1. Call fetchVoID() — read fabric:graphPurpose on each named graph to understand access patterns
2. Call fetchShapes() for data constraints and agent hints
3. Call fetchExamples() for query templates
4. For schema graphs (graphPurpose="schema"): use fetchJsonLd() to retrieve vocabulary as JSON-LD, then jsonld.expand() to see full property URIs, domains, ranges
5. For instance graphs (graphPurpose="instances"): use comunica_query() with SPARQL informed by vocabulary structure
6. Use jsonld.frame() to extract specific patterns from vocabulary documents (e.g., all properties of a class)
```

**Step 4: Run test to verify it passes**

Run: `cd experiments/node-rlm-fabric && npx vitest run global-docs.test.ts`
Expected: All PASS.

**Step 5: Run all JS tests for regressions**

Run: `cd experiments/node-rlm-fabric && npx vitest run`
Expected: All 28 tests PASS.

**Step 6: Commit**

```bash
git add experiments/node-rlm-fabric/global-docs.ts experiments/node-rlm-fabric/global-docs.test.ts
git commit -m "[Agent: Claude] feat: add tool selection heuristic to globalDocs (D31 routing)"
```

---

### Task 6: Verify full stack and run existing test suites

**Step 1: Run all Python unit tests**

Run: `~/uvws/.venv/bin/python -m pytest tests/pytest/unit/ -v`
Expected: All PASS (existing + new tests).

**Step 2: Run all JS tests**

Run: `cd experiments/node-rlm-fabric && npx vitest run`
Expected: All PASS.

**Step 3: Verify VoID Turtle parses cleanly**

Run: `~/uvws/.venv/bin/python -c "from fabric.node.void_templates import VOID_TURTLE; from rdflib import Graph; g = Graph(); g.parse(data=VOID_TURTLE.format(base='https://bootstrap.cogitarelink.ai'), format='turtle'); print(f'{len(g)} triples, OK')"`
Expected: Prints triple count and "OK" without errors.

**Step 4: Verify VoID JSON-LD parses cleanly**

Run: `~/uvws/.venv/bin/python -c "from fabric.node.void_templates import VOID_JSONLD; import json; d = json.loads(VOID_JSONLD.format(base='https://bootstrap.cogitarelink.ai')); print(f'{len(d[\"@graph\"])} graph entries, OK')"`
Expected: Prints "3 graph entries, OK".

**Step 5: Final commit if any fixups needed**

Only if previous steps required adjustments.
