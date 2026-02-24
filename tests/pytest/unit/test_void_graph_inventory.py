"""Test VoID declares named graph inventory."""
from rdflib import Graph, Namespace, URIRef

VOID = Namespace("http://rdfs.org/ns/void#")
DCT = Namespace("http://purl.org/dc/terms/")


def test_void_declares_observations_graph():
    from fabric.node.void_templates import VOID_TURTLE as _VOID_TURTLE
    ttl = _VOID_TURTLE.format(base="http://localhost:8080")
    g = Graph()
    g.parse(data=ttl, format="turtle")
    subsets = list(g.objects(predicate=VOID.subset))
    assert len(subsets) >= 1
    obs_graph_found = False
    for subset in subsets:
        endpoint = g.value(subset, VOID.sparqlGraphEndpoint)
        if endpoint and "observations" in str(endpoint):
            obs_graph_found = True
            title = str(g.value(subset, DCT.title) or "")
            assert title, "Named graph subset must have dct:title"
    assert obs_graph_found, "VoID must declare /graph/observations as a void:subset"


def test_discovery_extracts_named_graphs():
    from agents.fabric_discovery import _parse_void
    ttl = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .

<http://x/.well-known/void>
    a void:Dataset ;
    void:sparqlEndpoint <http://x/sparql> ;
    void:uriSpace "http://x/entity/" ;
    void:subset [
        a void:Dataset ;
        dct:title "Observations" ;
        void:sparqlGraphEndpoint <http://x/graph/observations> ;
    ] .
"""
    sparql_url, vocabs, conforms, uri_space, named_graphs = _parse_void(ttl)
    assert len(named_graphs) == 1
    assert named_graphs[0]["title"] == "Observations"
    assert named_graphs[0]["graph_uri"] == "http://x/graph/observations"
