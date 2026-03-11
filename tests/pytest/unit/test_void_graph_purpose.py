"""Test fabric:graphPurpose annotations in VoID templates."""
import json

from rdflib import Graph, Namespace, URIRef

SD = Namespace("http://www.w3.org/ns/sparql-service-description#")
FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
VOID = Namespace("http://rdfs.org/ns/void#")

BASE = "http://localhost:8080"


def _parse_turtle():
    from fabric.node.void_templates import VOID_TURTLE
    g = Graph()
    g.parse(data=VOID_TURTLE.format(base=BASE), format="turtle")
    return g


def _named_graphs(g):
    """Return dict of graph URI -> blank node for sd:namedGraph entries."""
    result = {}
    for ng in g.objects(predicate=SD.namedGraph):
        name = g.value(ng, SD.name)
        if name:
            result[str(name)] = ng
    return result


def test_instance_graphs_have_purpose_instances():
    g = _parse_turtle()
    ngs = _named_graphs(g)
    for path in ["graph/observations", "graph/entities"]:
        uri = f"{BASE}/{path}"
        assert uri in ngs, f"{uri} must be declared as sd:namedGraph"
        purpose = str(g.value(ngs[uri], FABRIC.graphPurpose))
        assert purpose == "instances", f"{uri} should have graphPurpose 'instances', got '{purpose}'"


def test_schema_graphs_have_purpose_schema():
    g = _parse_turtle()
    ngs = _named_graphs(g)
    schema_paths = [
        "ontology/sosa", "ontology/sio", "ontology/prov", "ontology/time",
        "ontology/fabric", "ontology/prof", "ontology/role",
    ]
    for path in schema_paths:
        uri = f"{BASE}/{path}"
        assert uri in ngs, f"{uri} must be declared as sd:namedGraph"
        purpose = str(g.value(ngs[uri], FABRIC.graphPurpose))
        assert purpose == "schema", f"{uri} should have graphPurpose 'schema', got '{purpose}'"


def test_metadata_graph_has_purpose_metadata():
    g = _parse_turtle()
    ngs = _named_graphs(g)
    uri = f"{BASE}/graph/metadata"
    assert uri in ngs
    purpose = str(g.value(ngs[uri], FABRIC.graphPurpose))
    assert purpose == "metadata"


def test_all_named_graphs_have_rdfs_comment():
    g = _parse_turtle()
    ngs = _named_graphs(g)
    for uri, node in ngs.items():
        comment = g.value(node, RDFS.comment)
        assert comment is not None, f"{uri} must have rdfs:comment"
        assert len(str(comment)) > 10, f"{uri} rdfs:comment too short"


def test_schema_graph_comments_mention_jsonld():
    g = _parse_turtle()
    ngs = _named_graphs(g)
    for path in ["ontology/sosa", "ontology/sio", "ontology/prov"]:
        uri = f"{BASE}/{path}"
        comment = str(g.value(ngs[uri], RDFS.comment))
        assert "JSON-LD" in comment, f"{uri} comment should mention JSON-LD navigation"


def test_instance_graph_comments_mention_sparql():
    g = _parse_turtle()
    ngs = _named_graphs(g)
    for path in ["graph/observations", "graph/entities"]:
        uri = f"{BASE}/{path}"
        comment = str(g.value(ngs[uri], RDFS.comment))
        assert "SPARQL" in comment, f"{uri} comment should mention SPARQL"


def test_jsonld_template_has_graph_purpose():
    from fabric.node.void_templates import VOID_JSONLD
    doc = json.loads(VOID_JSONLD.format(base=BASE))
    graph = doc["@graph"]
    service = next(n for n in graph if "sd:Service" in n.get("@type", []))
    named_graphs = service["sd:defaultDataset"]["sd:namedGraph"]
    purposes_found = set()
    for ng in named_graphs:
        purpose = ng.get("fabric:graphPurpose")
        assert purpose is not None, f"Named graph {ng['sd:name']} must have fabric:graphPurpose"
        purposes_found.add(purpose)
    assert "instances" in purposes_found
    assert "schema" in purposes_found
    assert "metadata" in purposes_found


def test_jsonld_template_has_rdfs_comment():
    from fabric.node.void_templates import VOID_JSONLD
    doc = json.loads(VOID_JSONLD.format(base=BASE))
    graph = doc["@graph"]
    service = next(n for n in graph if "sd:Service" in n.get("@type", []))
    named_graphs = service["sd:defaultDataset"]["sd:namedGraph"]
    for ng in named_graphs:
        comment = ng.get("rdfs:comment")
        assert comment is not None, f"Named graph {ng['sd:name']} must have rdfs:comment"
