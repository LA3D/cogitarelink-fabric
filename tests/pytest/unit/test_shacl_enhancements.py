"""Test SHACL shapes include prefix declarations and property type constraints."""
from pathlib import Path
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD

SH = Namespace("http://www.w3.org/ns/shacl#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
FABRIC = Namespace("https://w3id.org/cogitarelink/fabric#")

SHAPES_PATH = Path(__file__).parents[3] / "shapes" / "endpoint-sosa.ttl"


def _load_shapes(base: str = "http://localhost:8080") -> Graph:
    # Simulate serve-time {base} substitution (same as /.well-known/shacl endpoint)
    ttl = SHAPES_PATH.read_text().replace("{base}", base)
    g = Graph()
    g.parse(data=ttl, format="turtle")
    return g


def test_shacl_declares_sosa_prefix():
    """Shapes graph must declare sosa: prefix via sh:declare."""
    g = _load_shapes()
    declare_nodes = list(g.objects(predicate=SH.declare))
    prefixes = {}
    for node in declare_nodes:
        prefix = str(g.value(node, SH.prefix) or "")
        ns = str(g.value(node, SH.namespace) or "")
        if prefix:
            prefixes[prefix] = ns
    assert "sosa" in prefixes
    assert prefixes["sosa"] == "http://www.w3.org/ns/sosa/"


def test_observation_shape_has_made_by_sensor_property():
    """ObservationShape must declare sosa:madeBySensor with sh:class and sh:nodeKind."""
    g = _load_shapes()
    obs_shape = FABRIC.ObservationShape
    prop_nodes = list(g.objects(obs_shape, SH.property))
    sensor_props = [
        p for p in prop_nodes
        if g.value(p, SH.path) == SOSA.madeBySensor
    ]
    assert len(sensor_props) == 1, "Expected one sosa:madeBySensor property shape"
    sensor_prop = sensor_props[0]
    assert g.value(sensor_prop, SH["class"]) == SOSA.Sensor
    assert g.value(sensor_prop, SH.nodeKind) == SH.IRI


def test_made_by_sensor_has_pattern():
    """sosa:madeBySensor property shape must declare sh:pattern for entity URI namespace."""
    g = _load_shapes()
    obs_shape = FABRIC.ObservationShape
    for prop_node in g.objects(obs_shape, SH.property):
        if g.value(prop_node, SH.path) == SOSA.madeBySensor:
            pattern = str(g.value(prop_node, SH.pattern) or "")
            assert pattern.startswith("^http"), f"Expected URI pattern, got: {pattern}"
            assert "/entity/" in pattern
            return
    assert False, "sosa:madeBySensor property shape not found"


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
