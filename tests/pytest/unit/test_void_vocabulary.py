"""Tests for WU-4: void:vocabulary on ontology named graphs (D22, Phase 2.5a)."""
from rdflib import Graph, Namespace, URIRef


VOID = Namespace("http://rdfs.org/ns/void#")
SD = Namespace("http://www.w3.org/ns/sparql-service-description#")
PROV = Namespace("http://www.w3.org/ns/prov#")

BASE = "https://bootstrap.cogitarelink.ai"


def _parse_void_turtle():
    from fabric.node.void_templates import VOID_TURTLE
    g = Graph()
    g.parse(data=VOID_TURTLE.format(base=BASE), format="turtle")
    return g


def test_void_turtle_has_ontology_named_graphs():
    g = _parse_void_turtle()
    ontology_graphs = set()
    for ng in g.objects(predicate=SD.name):
        if "/ontology/" in str(ng):
            ontology_graphs.add(str(ng))
    assert f"{BASE}/ontology/sosa" in ontology_graphs
    assert f"{BASE}/ontology/sio" in ontology_graphs
    assert f"{BASE}/ontology/prov" in ontology_graphs
    assert f"{BASE}/ontology/time" in ontology_graphs
    assert f"{BASE}/ontology/fabric" in ontology_graphs


def test_void_turtle_ontology_graphs_have_vocabulary():
    g = _parse_void_turtle()
    for ng_uri in g.objects(predicate=SD.name):
        if "/ontology/" not in str(ng_uri):
            continue
        ng_node = None
        for s in g.subjects(SD.name, ng_uri):
            ng_node = s
        assert ng_node is not None, f"No blank node for {ng_uri}"
        vocabs = list(g.objects(ng_node, VOID.vocabulary))
        assert len(vocabs) == 1, f"{ng_uri} should have exactly one void:vocabulary"


def test_void_turtle_ontology_graphs_have_provenance():
    g = _parse_void_turtle()
    for ng_uri in g.objects(predicate=SD.name):
        if "/ontology/" not in str(ng_uri):
            continue
        ng_node = None
        for s in g.subjects(SD.name, ng_uri):
            ng_node = s
        derivations = list(g.objects(ng_node, PROV.wasDerivedFrom))
        assert len(derivations) == 1, f"{ng_uri} should have prov:wasDerivedFrom"


def test_void_turtle_sosa_vocabulary_correct():
    g = _parse_void_turtle()
    sosa_ng = URIRef(f"{BASE}/ontology/sosa")
    for s in g.subjects(SD.name, sosa_ng):
        vocabs = [str(v) for v in g.objects(s, VOID.vocabulary)]
        assert "http://www.w3.org/ns/sosa/" in vocabs


def test_void_jsonld_has_ontology_named_graphs():
    import json
    from fabric.node.void_templates import VOID_JSONLD
    doc = json.loads(VOID_JSONLD.format(base=BASE))
    service = [n for n in doc["@graph"] if "sd:Service" in str(n.get("@type", []))][0]
    named_graphs = service["sd:defaultDataset"]["sd:namedGraph"]
    graph_names = [ng["sd:name"]["@id"] for ng in named_graphs]
    assert f"{BASE}/ontology/sosa" in graph_names
    assert f"{BASE}/ontology/sio" in graph_names


def test_void_jsonld_ontology_graphs_have_vocabulary():
    import json
    from fabric.node.void_templates import VOID_JSONLD
    doc = json.loads(VOID_JSONLD.format(base=BASE))
    service = [n for n in doc["@graph"] if "sd:Service" in str(n.get("@type", []))][0]
    ontology_ngs = [ng for ng in service["sd:defaultDataset"]["sd:namedGraph"]
                    if "/ontology/" in ng["sd:name"]["@id"]]
    assert len(ontology_ngs) == 7
    for ng in ontology_ngs:
        assert "void:vocabulary" in ng, f"Missing void:vocabulary on {ng['sd:name']}"
        assert "prov:wasDerivedFrom" in ng, f"Missing prov:wasDerivedFrom on {ng['sd:name']}"
