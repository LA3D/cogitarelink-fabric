"""Test VoID declares all L2 vocabulary namespaces."""
from rdflib import Graph, Namespace

VOID = Namespace("http://rdfs.org/ns/void#")

EXPECTED_VOCABS = {
    "http://www.w3.org/ns/sosa/",
    "http://www.w3.org/2006/time#",
    "http://www.w3.org/ns/prov#",
    "http://semanticscience.org/resource/",
}


def test_void_turtle_declares_all_vocabularies():
    from fabric.node.void_templates import VOID_TURTLE as _VOID_TURTLE
    ttl = _VOID_TURTLE.format(base="http://localhost:8080")
    g = Graph()
    g.parse(data=ttl, format="turtle")
    vocabs = {str(o) for o in g.objects(predicate=VOID.vocabulary)}
    for expected in EXPECTED_VOCABS:
        assert expected in vocabs, f"Missing void:vocabulary <{expected}>"


def test_void_jsonld_declares_all_vocabularies():
    import json
    from fabric.node.void_templates import VOID_JSONLD as _VOID_JSONLD
    doc = json.loads(_VOID_JSONLD.format(base="http://localhost:8080"))
    # JSON-LD uses @graph array; find the VoID dataset node
    graph = doc.get("@graph", [doc])
    void_node = next(
        (n for n in graph if "void:Dataset" in (n.get("@type") or []
         if isinstance(n.get("@type"), list) else [n.get("@type", "")])),
        doc,
    )
    vocab_list = void_node.get("void:vocabulary", [])
    vocab_iris = {v["@id"] for v in vocab_list}
    for expected in EXPECTED_VOCABS:
        assert expected in vocab_iris, f"Missing void:vocabulary <{expected}>"
