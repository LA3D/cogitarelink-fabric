# L2 TBox Loading Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Load seven ontologies into Oxigraph named graphs via convention-based bootstrap, update VoID/CoreProfile declarations, and complete the routing plan TODO (show local graph paths).

**Architecture:** Bootstrap scans `ontology/*.ttl`, skips `*-profile.ttl`, and PUTs each file into `<{base}/ontology/{stem}>`. VoID declares `void:vocabulary` for data-relevant namespaces. `FabricEndpoint.vocab_graph_map` stores namespace-to-graph mappings so the routing plan renders `-> /ontology/{stem}` paths.

**Tech Stack:** Python 3.12, rdflib 7.6, httpx, pytest, Docker Compose (Oxigraph + FastAPI)

---

### Task 1: Copy and Download Ontology Files

**Files:**
- Create: `ontology/sosa.ttl` (copy from sibling repo)
- Create: `ontology/time.ttl` (download from W3C)
- Create: `ontology/prov.ttl` (copy from sibling repo)
- Create: `ontology/prof.ttl` (copy from sibling repo)
- Create: `ontology/role.ttl` (copy from sibling repo)
- Create: `ontology/sio.ttl` (copy from sibling repo)
- Delete: `ontology/sosa-tbox-stub.ttl`
- Rename: `ontology/fabric.ttl` -> `ontology/fabric.ttl`

**Step 1: Copy ontology files from sibling repos**

```bash
# Full SOSA (replaces 70-line stub)
cp ~/dev/git/LA3D/agents/ontology-agent-kr/experiments/rdfs_instruct/ontologies/sosa.ttl \
   ontology/sosa.ttl

# PROV-O (full consolidated W3C standard)
cp ~/dev/git/LA3D/agents/rlm/ontology/prov-o.ttl \
   ontology/prov.ttl

# PROF (W3C Profiles Vocabulary)
cp ~/dev/git/LA3D/agents/rlm/ontology/prof.ttl \
   ontology/prof.ttl

# Role (SKOS concept scheme for PROF roles)
cp ~/dev/git/LA3D/agents/rlm/ontology/role.ttl \
   ontology/role.ttl

# SIO subset (144 lines, curated for entity type reasoning)
cp ~/dev/git/LA3D/agents/ontology-agent-kr/ontology/sio_subset.ttl \
   ontology/sio.ttl
```

**Step 2: Download OWL-Time from W3C**

```bash
curl -L -H "Accept: text/turtle" -o ontology/time.ttl \
  "https://www.w3.org/2006/time"
```

If the W3C returns HTML instead of Turtle, try the GitHub source:
```bash
curl -L -o ontology/time.ttl \
  "https://raw.githubusercontent.com/w3c/sdw/gh-pages/time/rdf/time.ttl"
```

Verify it's valid Turtle:
```bash
python3 -c "from rdflib import Graph; g = Graph(); g.parse('ontology/time.ttl', format='turtle'); print(f'{len(g)} triples')"
```

**Step 3: Rename fabric.ttl to fabric.ttl**

```bash
git mv ontology/fabric.ttl ontology/fabric.ttl
```

**Step 4: Delete the stub**

```bash
git rm ontology/sosa-tbox-stub.ttl
```

**Step 5: Verify all files parse**

```bash
python3 -c "
from pathlib import Path
from rdflib import Graph
for f in sorted(Path('ontology').glob('*.ttl')):
    if f.name.endswith('-profile.ttl'):
        continue
    g = Graph()
    g.parse(str(f), format='turtle')
    print(f'{f.name}: {len(g)} triples')
"
```

Expected output (approximate):
```
fabric.ttl: ~150 triples
prof.ttl: ~60 triples
prov.ttl: ~900 triples
role.ttl: ~40 triples
sio.ttl: ~60 triples
sosa.ttl: ~200 triples
time.ttl: ~500 triples
```

**Step 6: Commit**

```bash
git add ontology/
git commit -m "[Agent: Claude] feat: add full L2 TBox ontologies (SOSA, OWL-Time, PROV-O, PROF, Role, SIO subset)

Replace 70-line SOSA stub with full W3C SOSA (424 lines).
Add OWL-Time (W3C download), PROV-O (consolidated), PROF, Role, SIO subset.
Rename fabric.ttl to fabric.ttl for convention auto-loading.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Update bootstrap.py for Convention Auto-Loading

**Files:**
- Modify: `fabric/node/bootstrap.py`
- Test: `tests/pytest/unit/test_bootstrap.py` (new)

**Step 1: Write the failing test**

Create `tests/pytest/unit/test_bootstrap.py`:

```python
"""Test bootstrap convention auto-loading."""
from pathlib import Path
from unittest.mock import patch, call
import importlib


def test_bootstrap_loads_all_ttl_files(tmp_path):
    """Bootstrap should load every *.ttl in ONTOLOGY_DIR except *-profile.ttl."""
    # Create test ontology files
    (tmp_path / "sosa.ttl").write_text("@prefix sosa: <http://www.w3.org/ns/sosa/> .\n")
    (tmp_path / "prov.ttl").write_text("@prefix prov: <http://www.w3.org/ns/prov#> .\n")
    (tmp_path / "fabric-core-profile.ttl").write_text("@prefix prof: <http://www.w3.org/ns/dx/prof/> .\n")

    loaded = []

    def fake_put(graph_uri, ttl, retries=2):
        loaded.append(graph_uri)

    with patch.dict("os.environ", {
        "ONTOLOGY_DIR": str(tmp_path),
        "NODE_BASE": "http://test:8080",
        "OXIGRAPH_URL": "http://fake:7878",
    }):
        import fabric.node.bootstrap as mod
        importlib.reload(mod)
        mod.put_graph = fake_put
        mod.main()

    assert "http://test:8080/ontology/sosa" in loaded
    assert "http://test:8080/ontology/prov" in loaded
    # Profile files must be skipped
    assert not any("profile" in g for g in loaded)


def test_bootstrap_skips_profile_files(tmp_path):
    """Files matching *-profile.ttl must not be loaded as named graphs."""
    (tmp_path / "fabric-core-profile.ttl").write_text("@prefix x: <http://x/> .\n")
    (tmp_path / "another-profile.ttl").write_text("@prefix y: <http://y/> .\n")

    loaded = []

    def fake_put(graph_uri, ttl, retries=2):
        loaded.append(graph_uri)

    with patch.dict("os.environ", {
        "ONTOLOGY_DIR": str(tmp_path),
        "NODE_BASE": "http://test:8080",
        "OXIGRAPH_URL": "http://fake:7878",
    }):
        import fabric.node.bootstrap as mod
        importlib.reload(mod)
        mod.put_graph = fake_put
        mod.main()

    assert len(loaded) == 0


def test_bootstrap_alphabetical_order(tmp_path):
    """Ontologies must load in alphabetical order for deterministic startup."""
    for name in ["zeta.ttl", "alpha.ttl", "mid.ttl"]:
        (tmp_path / name).write_text(f"@prefix x: <http://x/{name}/> .\n")

    loaded = []

    def fake_put(graph_uri, ttl, retries=2):
        loaded.append(graph_uri)

    with patch.dict("os.environ", {
        "ONTOLOGY_DIR": str(tmp_path),
        "NODE_BASE": "http://test:8080",
        "OXIGRAPH_URL": "http://fake:7878",
    }):
        import fabric.node.bootstrap as mod
        importlib.reload(mod)
        mod.put_graph = fake_put
        mod.main()

    stems = [g.rsplit("/", 1)[-1] for g in loaded]
    assert stems == ["alpha", "mid", "zeta"]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/pytest/unit/test_bootstrap.py -v
```

Expected: FAIL (bootstrap.py still hardcodes SOSA stub loading)

**Step 3: Write minimal implementation**

Replace `fabric/node/bootstrap.py` lines 35-42 (the `main()` function):

```python
def main() -> None:
    ttl_files = sorted(ONTOLOGY_DIR.glob("*.ttl"))
    if not ttl_files:
        print(f"WARNING: no .ttl files in {ONTOLOGY_DIR}", flush=True)
    for f in ttl_files:
        if f.name.endswith("-profile.ttl"):
            continue
        graph_uri = f"{NODE_BASE}/ontology/{f.stem}"
        try:
            print(f"Loading {f.name} into <{graph_uri}>...", flush=True)
            put_graph(graph_uri, f.read_text())
        except Exception as e:
            print(f"WARNING: failed to load {f.name}: {e}", flush=True)
    print("Bootstrap complete.", flush=True)
```

Also update the module docstring (line 2) to:
```python
"""Startup bootstrap: load TBox ontologies into Oxigraph via Graph Store HTTP Protocol."""
```

And remove the now-unused `TBOX_GRAPH` constant (line 11).

**Step 4: Run test to verify it passes**

```bash
pytest tests/pytest/unit/test_bootstrap.py -v
```

Expected: 3 PASS

**Step 5: Commit**

```bash
git add fabric/node/bootstrap.py tests/pytest/unit/test_bootstrap.py
git commit -m "[Agent: Claude] feat: convention auto-loading bootstrap for L2 TBox ontologies

Scan ontology/*.ttl, skip *-profile.ttl, load into <{base}/ontology/{stem}>.
Alphabetical order, non-fatal failures. Replaces hardcoded SOSA stub loading.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Update VoID Template with New Vocabularies

**Files:**
- Modify: `fabric/node/main.py:16-60` (VoID templates)
- Modify: `tests/pytest/unit/test_void_urispace.py`
- Test: `tests/pytest/unit/test_void_vocabularies.py` (new)

**Step 1: Write the failing test**

Create `tests/pytest/unit/test_void_vocabularies.py`:

```python
"""Test VoID declares all L2 vocabulary namespaces."""
from rdflib import Graph, Namespace, URIRef

VOID = Namespace("http://rdfs.org/ns/void#")

EXPECTED_VOCABS = {
    "http://www.w3.org/ns/sosa/",
    "http://www.w3.org/2006/time#",
    "http://www.w3.org/ns/prov#",
    "http://semanticscience.org/resource/",
}


def test_void_turtle_declares_all_vocabularies():
    from fabric.node.main import _VOID_TURTLE
    ttl = _VOID_TURTLE.format(base="http://localhost:8080")
    g = Graph()
    g.parse(data=ttl, format="turtle")
    vocabs = {str(o) for o in g.objects(predicate=VOID.vocabulary)}
    for expected in EXPECTED_VOCABS:
        assert expected in vocabs, f"Missing void:vocabulary <{expected}>"


def test_void_jsonld_declares_all_vocabularies():
    import json
    from fabric.node.main import _VOID_JSONLD
    doc = json.loads(_VOID_JSONLD.format(base="http://localhost:8080"))
    vocab_list = doc.get("void:vocabulary", [])
    vocab_iris = {v["@id"] for v in vocab_list}
    for expected in EXPECTED_VOCABS:
        assert expected in vocab_iris, f"Missing void:vocabulary <{expected}>"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/pytest/unit/test_void_vocabularies.py -v
```

Expected: FAIL (VoID only declares SOSA and OWL-Time currently)

**Step 3: Write minimal implementation**

In `fabric/node/main.py`, update `_VOID_TURTLE` (lines 16-35) to add the new vocabulary entries:

```python
_VOID_TURTLE = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

<{base}/.well-known/void>
    a void:Dataset ;
    dct:title "cogitarelink-fabric node"^^xsd:string ;
    void:sparqlEndpoint <{base}/sparql> ;
    void:uriSpace "{base}/entity/" ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ;
    void:vocabulary <http://www.w3.org/2006/time#> ;
    void:vocabulary <http://www.w3.org/ns/prov#> ;
    void:vocabulary <http://semanticscience.org/resource/> ;
    dct:conformsTo <https://w3id.org/cogitarelink/fabric#CoreProfile> ;
    void:subset [
        a void:Dataset ;
        dct:title "Observations" ;
        void:sparqlGraphEndpoint <{base}/graph/observations> ;
        dct:conformsTo <https://w3id.org/cogitarelink/fabric#ObservationShape> ;
    ] .
"""
```

Update `_VOID_JSONLD` (lines 37-60) similarly — add prov and sio to the vocabulary array:

```python
_VOID_JSONLD = """\
{{
  "@context": {{
    "void": "http://rdfs.org/ns/void#",
    "dct": "http://purl.org/dc/terms/"
  }},
  "@id": "{base}/.well-known/void",
  "@type": "void:Dataset",
  "dct:title": "cogitarelink-fabric node",
  "void:sparqlEndpoint": {{ "@id": "{base}/sparql" }},
  "void:uriSpace": "{base}/entity/",
  "void:vocabulary": [
    {{ "@id": "http://www.w3.org/ns/sosa/" }},
    {{ "@id": "http://www.w3.org/2006/time#" }},
    {{ "@id": "http://www.w3.org/ns/prov#" }},
    {{ "@id": "http://semanticscience.org/resource/" }}
  ],
  "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#CoreProfile" }},
  "void:subset": {{
    "@type": "void:Dataset",
    "dct:title": "Observations",
    "void:sparqlGraphEndpoint": {{ "@id": "{base}/graph/observations" }},
    "dct:conformsTo": {{ "@id": "https://w3id.org/cogitarelink/fabric#ObservationShape" }}
  }}
}}
"""
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/pytest/unit/test_void_vocabularies.py tests/pytest/unit/test_void_urispace.py tests/pytest/unit/test_void_graph_inventory.py -v
```

Expected: all PASS (existing tests should still pass since we only added vocabularies)

**Step 5: Commit**

```bash
git add fabric/node/main.py tests/pytest/unit/test_void_vocabularies.py
git commit -m "[Agent: Claude] feat: declare PROV-O and SIO vocabularies in VoID

Add void:vocabulary entries for prov: and sio: namespaces in both
Turtle and JSON-LD VoID templates.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Update CoreProfile with All L2 Resources

**Files:**
- Modify: `ontology/fabric-core-profile.ttl:28-45`

**Step 1: Write the failing test**

Create `tests/pytest/unit/test_core_profile.py`:

```python
"""Test CoreProfile declares all L2 TBox ontologies."""
from pathlib import Path
from rdflib import Graph, Namespace, URIRef

PROF = Namespace("http://www.w3.org/ns/dx/prof/")
ROLE = Namespace("http://www.w3.org/ns/dx/prof/role/")
FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")

PROFILE_PATH = Path(__file__).parents[3] / "ontology" / "fabric-core-profile.ttl"

EXPECTED_ARTIFACTS = {
    "http://www.w3.org/ns/sosa/",
    "http://www.w3.org/2006/time#",
    "http://www.w3.org/ns/prov#",
    "http://semanticscience.org/resource/",
}


def test_core_profile_declares_all_tbox_ontologies():
    g = Graph()
    g.parse(str(PROFILE_PATH), format="turtle")
    # Find all ResourceDescriptor with role:schema
    artifacts = set()
    for rd in g.subjects(PROF.hasRole, ROLE.schema):
        for art in g.objects(rd, PROF.hasArtifact):
            artifacts.add(str(art))
    for expected in EXPECTED_ARTIFACTS:
        assert expected in artifacts, f"CoreProfile missing prof:hasArtifact <{expected}>"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/pytest/unit/test_core_profile.py -v
```

Expected: FAIL (CoreProfile only declares SOSA and OWL-Time)

**Step 3: Write minimal implementation**

In `ontology/fabric-core-profile.ttl`, after the OWL-Time resource descriptor (line 44), add:

```turtle
    prof:hasResource [
        a prof:ResourceDescriptor ;
        rdfs:label "PROV-O ontology" ;
        dct:description "W3C PROV-O — provenance entities, activities, and agents." ;
        prof:hasRole role:schema ;
        prof:hasArtifact <http://www.w3.org/ns/prov#> ;
        dct:format <https://www.iana.org/assignments/media-types/text/turtle> ;
    ] ;
    prof:hasResource [
        a prof:ResourceDescriptor ;
        rdfs:label "SIO subset" ;
        dct:description "Semanticscience Integrated Ontology — curated subset for entity type reasoning." ;
        prof:hasRole role:schema ;
        prof:hasArtifact <http://semanticscience.org/resource/> ;
        dct:format <https://www.iana.org/assignments/media-types/text/turtle> ;
    ] ;
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/pytest/unit/test_core_profile.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add ontology/fabric-core-profile.ttl tests/pytest/unit/test_core_profile.py
git commit -m "[Agent: Claude] feat: declare PROV-O and SIO in CoreProfile L2 resources

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Update _COMPACT_PREFIXES and SHACL Prefix Declarations

**Files:**
- Modify: `agents/fabric_discovery.py:112-119` (_COMPACT_PREFIXES)
- Modify: `shapes/endpoint-sosa.ttl` (add sio and prov prefix declarations)

**Step 1: Write the failing test**

Add to `tests/pytest/unit/test_shacl_enhancements.py`:

```python
def test_shacl_declares_prov_prefix():
    """Shapes graph should declare prov: prefix via sh:declare."""
    g = _load_shapes()
    declare_nodes = list(g.objects(predicate=SH.declare))
    prefixes = {}
    for node in declare_nodes:
        prefix = str(g.value(node, SH.prefix) or "")
        ns = str(g.value(node, SH.namespace) or "")
        if prefix:
            prefixes[prefix] = ns
    assert "prov" in prefixes
    assert prefixes["prov"] == "http://www.w3.org/ns/prov#"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/pytest/unit/test_shacl_enhancements.py::test_shacl_declares_prov_prefix -v
```

Expected: FAIL

**Step 3: Write minimal implementation**

In `shapes/endpoint-sosa.ttl`, add `sh:declare` entries for prov and sio to the ontology subject's existing declarations:

```turtle
    ] , [
        sh:prefix "prov" ;
        sh:namespace "http://www.w3.org/ns/prov#"^^xsd:anyURI ;
    ] , [
        sh:prefix "sio" ;
        sh:namespace "http://semanticscience.org/resource/"^^xsd:anyURI ;
    ] .
```

In `agents/fabric_discovery.py`, add to `_COMPACT_PREFIXES` (line 112):

```python
_COMPACT_PREFIXES = {
    "http://www.w3.org/ns/sosa/": "sosa:",
    "http://www.w3.org/2006/time#": "time:",
    "http://www.w3.org/ns/shacl#": "sh:",
    "http://qudt.org/schema/qudt/": "qudt:",
    "http://www.w3.org/ns/prov#": "prov:",
    "http://semanticscience.org/resource/": "sio:",
    "https://w3id.org/cogitarelink/fabric#": "fabric:",
    "http://www.w3.org/ns/dx/prof/": "prof:",
}
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/pytest/unit/test_shacl_enhancements.py -v
```

Expected: all PASS

**Step 5: Commit**

```bash
git add shapes/endpoint-sosa.ttl agents/fabric_discovery.py tests/pytest/unit/test_shacl_enhancements.py
git commit -m "[Agent: Claude] feat: add prov/sio prefix declarations to SHACL and compact prefix map

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Add vocab_graph_map to FabricEndpoint and Routing Plan

**Files:**
- Modify: `agents/fabric_discovery.py:33-100` (FabricEndpoint + routing_plan)
- Modify: `agents/fabric_discovery.py:260-297` (discover_endpoint)
- Modify: `tests/pytest/unit/test_routing_plan_format.py`

**Step 1: Write the failing test**

Add to `tests/pytest/unit/test_routing_plan_format.py`:

```python
def test_routing_plan_shows_local_graph_paths():
    """When vocab_graph_map is populated, routing plan shows -> /ontology/{stem}."""
    ep = _make_endpoint()
    ep.vocab_graph_map = {
        "http://www.w3.org/ns/sosa/": "http://x/ontology/sosa",
    }
    plan = ep.routing_plan
    assert "-> /ontology/sosa" in plan


def test_routing_plan_without_graph_map_still_works():
    """When vocab_graph_map is empty, routing plan renders prefixes without paths."""
    ep = _make_endpoint()
    ep.vocab_graph_map = {}
    plan = ep.routing_plan
    assert "sosa:" in plan
    assert "->" not in plan.split("Local ontology cache")[1].split("Named graphs")[0]
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/pytest/unit/test_routing_plan_format.py -v
```

Expected: FAIL (FabricEndpoint has no vocab_graph_map field)

**Step 3: Write minimal implementation**

In `agents/fabric_discovery.py`, add the field to FabricEndpoint (after line 44):

```python
    vocab_graph_map: dict[str, str] = field(default_factory=dict)
```

Update `routing_plan` property (lines 64-67) to render the graph path:

```python
        if self.prefix_declarations:
            lines.append("Local ontology cache (no external dereferencing needed):")
            for prefix, ns in sorted(self.prefix_declarations.items()):
                graph_uri = self.vocab_graph_map.get(ns, "")
                if graph_uri:
                    # Extract path from full URI: http://x/ontology/sosa -> /ontology/sosa
                    path = "/" + graph_uri.split("/", 3)[-1] if "/" in graph_uri[8:] else graph_uri
                    lines.append(f"  {prefix}: <{ns}> -> {path}")
                else:
                    lines.append(f"  {prefix}: <{ns}>")
```

In `discover_endpoint()`, after the `_resolve_vocab_graphs` call (around line 281), build the vocab_graph_map by pairing each vocabulary with its discovered graph:

```python
    vocab_graph_map: dict[str, str] = {}
    tbox = None
    if sparql_url and vocabs:
        try:
            graph_uris = _resolve_vocab_graphs(sparql_url, vocabs)
            if graph_uris:
                tbox = _load_tbox(sparql_url, graph_uris)
                # Build vocab -> graph mapping from resolve results
                for vocab in vocabs:
                    for gu in graph_uris:
                        # Match vocab namespace to graph that contains its triples
                        # _resolve_vocab_graphs returns graphs in order of vocab queries
                        if vocab.rstrip("/#").rsplit("/", 1)[-1].lower() in gu.lower():
                            vocab_graph_map[vocab] = gu
                            break
        except (httpx.HTTPError, ValueError) as exc:
            log.debug("TBox loading failed: %s", exc)
```

**Note:** The matching heuristic above (checking if the vocab short name appears in the graph URI) works because of our naming convention (`sosa` namespace → `/ontology/sosa` graph). A more robust approach uses one STRSTARTS query per vocab and records which graph was found per namespace. Refactor `_resolve_vocab_graphs` to return `dict[str, str]` instead of `list[str]`:

Replace `_resolve_vocab_graphs` (lines 220-238) entirely:

```python
def _resolve_vocab_graphs(sparql_url: str, vocabs: list[str]) -> dict[str, str]:
    """Find named graphs containing triples whose subjects start with each vocabulary IRI.

    Returns: dict mapping vocabulary namespace -> graph URI.
    """
    mapping: dict[str, str] = {}
    all_graphs: list[str] = []
    for vocab in vocabs:
        if not _SAFE_IRI.match(vocab):
            log.warning("Skipping unsafe vocabulary IRI: %s", vocab)
            continue
        q = f'SELECT DISTINCT ?g WHERE {{ GRAPH ?g {{ ?s ?p ?o . FILTER(STRSTARTS(STR(?s), "{vocab}")) }} }}'
        r = httpx.post(
            sparql_url, data={"query": q},
            headers={"Accept": "application/sparql-results+json"},
            timeout=10.0,
        )
        r.raise_for_status()
        for binding in r.json().get("results", {}).get("bindings", []):
            uri = binding.get("g", {}).get("value", "")
            if uri:
                mapping[vocab] = uri
                if uri not in all_graphs:
                    all_graphs.append(uri)
    return mapping
```

Update `_load_tbox` call site in `discover_endpoint()` to use the mapping values:

```python
    vocab_graph_map: dict[str, str] = {}
    tbox = None
    if sparql_url and vocabs:
        try:
            vocab_graph_map = _resolve_vocab_graphs(sparql_url, vocabs)
            graph_uris = list(vocab_graph_map.values())
            if graph_uris:
                tbox = _load_tbox(sparql_url, graph_uris)
        except (httpx.HTTPError, ValueError) as exc:
            log.debug("TBox loading failed: %s", exc)
```

And pass `vocab_graph_map` to the FabricEndpoint constructor:

```python
    return FabricEndpoint(
        ...
        vocab_graph_map=vocab_graph_map,
        ...
    )
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/pytest/unit/test_routing_plan_format.py -v
```

Expected: all PASS (including existing tests)

**Step 5: Run full unit test suite**

```bash
pytest tests/pytest/unit/ -v
```

Expected: all PASS

**Step 6: Commit**

```bash
git add agents/fabric_discovery.py tests/pytest/unit/test_routing_plan_format.py
git commit -m "[Agent: Claude] feat: vocab_graph_map for routing plan local graph paths

Refactor _resolve_vocab_graphs to return dict[str, str] (namespace -> graph URI).
Add vocab_graph_map field to FabricEndpoint.
Routing plan now renders '-> /ontology/{stem}' when graph map is populated.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Update References to fabric.ttl

**Files:**
- Modify: any file referencing `fabric.ttl`

**Step 1: Search for references**

```bash
grep -rn "fabric-vocab" --include="*.py" --include="*.md" --include="*.yml" --include="*.ttl" .
```

Update any references found to point to `fabric.ttl` instead. This may include test files, documentation, or configuration.

**Step 2: Run full unit tests**

```bash
pytest tests/pytest/unit/ -v
```

Expected: all PASS

**Step 3: Commit (if changes were needed)**

```bash
git add -A
git commit -m "[Agent: Claude] chore: update references from fabric.ttl to fabric.ttl

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Docker Rebuild and Integration Test

**Files:**
- Test: manual Docker verification

**Step 1: Rebuild and restart Docker stack**

```bash
docker compose down
docker compose build --no-cache fabric-node
docker compose up -d
```

**Step 2: Wait for healthz**

```bash
for i in $(seq 1 30); do
  curl -sf http://localhost:8080/healthz && break
  sleep 1
done
```

**Step 3: Verify bootstrap loaded all ontology graphs**

```bash
# Check each expected named graph has triples
for graph in sosa time prov prof role sio fabric; do
  echo -n "$graph: "
  curl -s -X POST http://localhost:8080/sparql \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -H "Accept: application/sparql-results+json" \
    -d "query=SELECT (COUNT(*) AS ?n) WHERE { GRAPH <http://localhost:8080/ontology/$graph> { ?s ?p ?o } }" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['results']['bindings'][0]['n']['value'])"
done
```

Expected output (approximate):
```
sosa: 200+
time: 500+
prov: 900+
prof: 60+
role: 40+
sio: 60+
fabric: 150+
```

**Step 4: Verify VoID reflects new vocabularies**

```bash
curl -s http://localhost:8080/.well-known/void | grep "void:vocabulary"
```

Expected: four vocabulary entries

**Step 5: Verify docker logs show bootstrap loading all files**

```bash
docker compose logs fabric-node | grep "Loading"
```

Expected: seven "Loading X.ttl into..." lines

---

### Task 9: Integration Test — Discovery with Graph Map

**Files:**
- Modify: `tests/pytest/integration/test_fabric_discovery.py`

**Step 1: Write the failing test**

Add to `tests/pytest/integration/test_fabric_discovery.py`:

```python
def test_discover_populates_vocab_graph_map(fabric_url):
    """discover_endpoint should map vocabulary namespaces to local ontology graphs."""
    ep = discover_endpoint(fabric_url)
    assert len(ep.vocab_graph_map) >= 2, f"Expected vocab graph mappings, got: {ep.vocab_graph_map}"
    # SOSA namespace should map to /ontology/sosa graph
    sosa_graph = ep.vocab_graph_map.get("http://www.w3.org/ns/sosa/", "")
    assert "/ontology/sosa" in sosa_graph


def test_routing_plan_shows_graph_paths(fabric_url):
    """Routing plan should render '-> /ontology/sosa' when graphs are loaded."""
    ep = discover_endpoint(fabric_url)
    plan = ep.routing_plan
    assert "-> /ontology/sosa" in plan or "→ /ontology/sosa" in plan
```

**Step 2: Run test (requires Docker stack running)**

```bash
pytest tests/pytest/integration/test_fabric_discovery.py -v
```

Expected: all PASS (including existing discovery tests)

**Step 3: Commit**

```bash
git add tests/pytest/integration/test_fabric_discovery.py
git commit -m "[Agent: Claude] test: integration tests for vocab_graph_map and routing plan paths

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 10: Full Regression Test

**Step 1: Run all tests**

```bash
pytest tests/ -v
```

Expected: all existing tests + new tests pass. No regressions from replacing SOSA stub with full SOSA.

**Step 2: Check for test failures**

If any tests fail due to SOSA changes (full SOSA has more triples than stub), fix the tests to work with the full ontology. The most likely issue is `test_discover_loads_tbox` in integration tests — the triple count will be higher with full ontologies.

---

### Task 11: Experiment — Re-run Phase 1.5 with Full TBox

**Step 1: Re-run Phase 1.5 experiments**

Use the existing experiment harness from `experiments/fabric_navigation/`. The experiment should show whether the richer TBox context (more class labels, domain/range declarations, property descriptions) helps the agent navigate more efficiently, especially for layers 1.5b-d that were saturated with the stub.

```bash
cd experiments/fabric_navigation
# Run experiment phases (exact command depends on harness script)
```

**Step 2: Compare results to Phase 1.5 baseline**

Key metrics to compare:
- Iterations per task (was 3.0 across all layers)
- SPARQL queries per task (was 2.0)
- Recovery count (was 0)
- Cost per task

**Step 3: Commit results**

```bash
git add experiments/fabric_navigation/results/
git commit -m "[Agent: Claude] experiment: Phase 2 L2 TBox — re-run navigation with full ontologies

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## File Summary

| File | Action | Task |
|---|---|---|
| `ontology/sosa.ttl` | New (copy) | 1 |
| `ontology/time.ttl` | New (download) | 1 |
| `ontology/prov.ttl` | New (copy) | 1 |
| `ontology/prof.ttl` | New (copy) | 1 |
| `ontology/role.ttl` | New (copy) | 1 |
| `ontology/sio.ttl` | New (copy) | 1 |
| `ontology/fabric.ttl` | Rename from fabric.ttl | 1 |
| `ontology/sosa-tbox-stub.ttl` | Delete | 1 |
| `ontology/fabric-core-profile.ttl` | Edit (add resources) | 4 |
| `fabric/node/bootstrap.py` | Edit (convention auto-load) | 2 |
| `fabric/node/main.py` | Edit (VoID vocabularies) | 3 |
| `agents/fabric_discovery.py` | Edit (vocab_graph_map, _resolve_vocab_graphs, routing_plan) | 5, 6 |
| `shapes/endpoint-sosa.ttl` | Edit (prefix declarations) | 5 |
| `tests/pytest/unit/test_bootstrap.py` | New | 2 |
| `tests/pytest/unit/test_void_vocabularies.py` | New | 3 |
| `tests/pytest/unit/test_core_profile.py` | New | 4 |
| `tests/pytest/unit/test_shacl_enhancements.py` | Edit | 5 |
| `tests/pytest/unit/test_routing_plan_format.py` | Edit | 6 |
| `tests/pytest/integration/test_fabric_discovery.py` | Edit | 9 |

## Full Verification

```bash
# Unit tests (no Docker)
pytest tests/pytest/unit/ -v

# Integration tests (needs Docker stack running)
pytest tests/pytest/integration/ -v

# All tests
pytest tests/ -v
```
