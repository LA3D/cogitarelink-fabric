"""Test fabric:writable annotations in VoID and _parse_void extraction."""
from rdflib import Graph, Namespace, Literal, XSD

VOID = Namespace("http://rdfs.org/ns/void#")
FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")
DCT = Namespace("http://purl.org/dc/terms/")


def test_void_turtle_has_fabric_prefix():
    from fabric.node.void_templates import VOID_TURTLE
    assert "@prefix fabric:" in VOID_TURTLE


def test_void_turtle_observations_writable():
    from fabric.node.void_templates import VOID_TURTLE
    ttl = VOID_TURTLE.format(base="http://localhost:8080")
    g = Graph()
    g.parse(data=ttl, format="turtle")
    for subset in g.objects(predicate=VOID.subset):
        ep = g.value(subset, VOID.sparqlGraphEndpoint)
        if ep and "observations" in str(ep):
            w = g.value(subset, FABRIC.writable)
            assert w is not None, "/graph/observations must have fabric:writable"
            assert w.toPython() is True
            return
    assert False, "observations subset not found"


def test_void_turtle_entities_writable():
    from fabric.node.void_templates import VOID_TURTLE
    ttl = VOID_TURTLE.format(base="http://localhost:8080")
    g = Graph()
    g.parse(data=ttl, format="turtle")
    for subset in g.objects(predicate=VOID.subset):
        ep = g.value(subset, VOID.sparqlGraphEndpoint)
        if ep and "entities" in str(ep):
            w = g.value(subset, FABRIC.writable)
            assert w is not None, "/graph/entities must have fabric:writable"
            assert w.toPython() is True
            return
    assert False, "entities subset not found"


def test_parse_void_extracts_writable_true():
    from agents.fabric_discovery import _parse_void
    ttl = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .

<http://x/.well-known/void>
    a void:Dataset ;
    void:sparqlEndpoint <http://x/sparql> ;
    void:subset [
        a void:Dataset ;
        dct:title "Observations" ;
        void:sparqlGraphEndpoint <http://x/graph/observations> ;
        fabric:writable true ;
    ] .
"""
    _, _, _, _, named_graphs = _parse_void(ttl)
    assert len(named_graphs) == 1
    assert named_graphs[0]["writable"] is True


def test_parse_void_writable_absent_defaults_false():
    from agents.fabric_discovery import _parse_void
    ttl = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .

<http://x/.well-known/void>
    a void:Dataset ;
    void:sparqlEndpoint <http://x/sparql> ;
    void:subset [
        a void:Dataset ;
        dct:title "ReadOnly" ;
        void:sparqlGraphEndpoint <http://x/graph/readonly> ;
    ] .
"""
    _, _, _, _, named_graphs = _parse_void(ttl)
    assert len(named_graphs) == 1
    assert named_graphs[0].get("writable") is False


def test_parse_void_mixed_writable():
    from agents.fabric_discovery import _parse_void
    ttl = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .

<http://x/.well-known/void>
    a void:Dataset ;
    void:sparqlEndpoint <http://x/sparql> ;
    void:subset [
        a void:Dataset ;
        dct:title "Observations" ;
        void:sparqlGraphEndpoint <http://x/graph/observations> ;
        fabric:writable true ;
    ] ;
    void:subset [
        a void:Dataset ;
        dct:title "Metadata" ;
        void:sparqlGraphEndpoint <http://x/graph/metadata> ;
    ] .
"""
    _, _, _, _, named_graphs = _parse_void(ttl)
    assert len(named_graphs) == 2
    obs = next(ng for ng in named_graphs if "observations" in ng["graph_uri"])
    meta = next(ng for ng in named_graphs if "metadata" in ng["graph_uri"])
    assert obs["writable"] is True
    assert meta["writable"] is False


def test_void_jsonld_has_writable():
    from fabric.node.void_templates import VOID_JSONLD
    import json
    raw = VOID_JSONLD.format(base="http://localhost:8080")
    data = json.loads(raw)
    void_entry = next(e for e in data["@graph"] if "void:subset" in e)
    for subset in void_entry["void:subset"]:
        title = subset.get("dct:title", "")
        if title in ("Observations", "Entities"):
            assert subset.get("fabric:writable") is True, \
                f"{title} subset in JSONLD must have fabric:writable: true"
