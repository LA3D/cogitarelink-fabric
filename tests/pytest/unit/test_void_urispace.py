"""Test that VoID self-description declares void:uriSpace."""
from rdflib import Graph, Namespace

VOID = Namespace("http://rdfs.org/ns/void#")

def test_void_turtle_declares_uri_space():
    """VoID Turtle must include void:uriSpace pointing to entity namespace."""
    # Simulate what main.py produces
    from fabric.node.void_templates import VOID_TURTLE as _VOID_TURTLE
    ttl = _VOID_TURTLE.format(base="http://localhost:8080")
    g = Graph()
    g.parse(data=ttl, format="turtle")
    uri_spaces = list(g.objects(predicate=VOID.uriSpace))
    assert len(uri_spaces) == 1
    assert str(uri_spaces[0]) == "http://localhost:8080/entity/"
