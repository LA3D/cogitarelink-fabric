"""Test fabric:graphPurpose and GraphPurposeScheme in fabric ontology."""
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, OWL, RDFS, XSD

FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")


def _load_fabric_ontology():
    g = Graph()
    g.parse("ontology/fabric.ttl", format="turtle")
    return g


def test_graph_purpose_is_object_property():
    g = _load_fabric_ontology()
    assert (FABRIC.graphPurpose, RDF.type, OWL.ObjectProperty) in g


def test_graph_purpose_has_range_graph_purpose_class():
    g = _load_fabric_ontology()
    assert (FABRIC.graphPurpose, RDFS.range, FABRIC.GraphPurpose) in g


def test_graph_purpose_class_is_skos_concept():
    g = _load_fabric_ontology()
    assert (FABRIC.GraphPurpose, RDF.type, OWL.Class) in g
    assert (FABRIC.GraphPurpose, RDFS.subClassOf, SKOS.Concept) in g


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


def test_graph_purpose_scheme_has_three_concepts():
    g = _load_fabric_ontology()
    assert (FABRIC.GraphPurposeScheme, RDF.type, SKOS.ConceptScheme) in g
    tops = list(g.objects(FABRIC.GraphPurposeScheme, SKOS.hasTopConcept))
    assert len(tops) == 3
    top_uris = {str(t) for t in tops}
    assert str(FABRIC.InstancesPurpose) in top_uris
    assert str(FABRIC.SchemaPurpose) in top_uris
    assert str(FABRIC.MetadataPurpose) in top_uris


def test_graph_purpose_individuals_have_notation():
    g = _load_fabric_ontology()
    for ind, expected in [
        (FABRIC.InstancesPurpose, "instances"),
        (FABRIC.SchemaPurpose, "schema"),
        (FABRIC.MetadataPurpose, "metadata"),
    ]:
        notation = str(g.value(ind, SKOS.notation))
        assert notation == expected, f"{ind} should have skos:notation '{expected}', got '{notation}'"


def test_odrl_alignment_on_authorization():
    g = _load_fabric_ontology()
    ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
    assert (FABRIC.AgentAuthorizationCredential, RDFS.subClassOf, ODRL.Policy) in g
    assert (FABRIC.permittedGraphs, RDFS.subPropertyOf, ODRL.target) in g


def test_dprod_alignment():
    g = _load_fabric_ontology()
    DPROD = Namespace("https://ekgf.github.io/dprod/")
    assert (FABRIC.publishesDataProduct, RDF.type, OWL.ObjectProperty) in g
    assert (FABRIC.publishesDataProduct, RDFS.range, DPROD.DataProduct) in g
