"""Test fabric:graphPurpose is declared in fabric ontology."""
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, OWL, RDFS, XSD

FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


def _load_fabric_ontology():
    g = Graph()
    g.parse("ontology/fabric.ttl", format="turtle")
    return g


def test_graph_purpose_is_datatype_property():
    g = _load_fabric_ontology()
    assert (FABRIC.graphPurpose, RDF.type, OWL.DatatypeProperty) in g


def test_graph_purpose_has_range_xsd_string():
    g = _load_fabric_ontology()
    assert (FABRIC.graphPurpose, RDFS.range, XSD.string) in g


def test_graph_purpose_has_label():
    g = _load_fabric_ontology()
    label = g.value(FABRIC.graphPurpose, RDFS.label)
    assert label is not None
    assert "graph purpose" in str(label).lower()


def test_graph_purpose_has_definition():
    g = _load_fabric_ontology()
    defn = g.value(FABRIC.graphPurpose, SKOS.definition)
    assert defn is not None
    assert "D9" in str(defn) or "four-layer" in str(defn).lower()
