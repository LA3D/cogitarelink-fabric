"""Test SPARQL examples include sensor discovery, entity lookup, and count."""
from pathlib import Path
from rdflib import Graph, Namespace
from rdflib.namespace import RDFS

SPEX = Namespace("https://purl.expasy.org/sparql-examples/ontology#")
SH = Namespace("http://www.w3.org/ns/shacl#")

EXAMPLES_PATH = Path(__file__).parents[3] / "sparql" / "sosa-examples.ttl"


def _load_examples() -> Graph:
    g = Graph()
    txt = EXAMPLES_PATH.read_text().replace("{base}", "http://localhost:8080")
    g.parse(data=txt, format="turtle")
    return g


def test_examples_include_sensor_discovery():
    g = _load_examples()
    labels = [str(l) for l in g.objects(predicate=RDFS.label)]
    assert any("sensor" in l.lower() and "discover" in l.lower() for l in labels), \
        f"Expected a sensor discovery example. Found: {labels}"


def test_examples_include_entity_lookup():
    g = _load_examples()
    labels = [str(l) for l in g.objects(predicate=RDFS.label)]
    assert any("entity" in l.lower() or "describe" in l.lower() or "lookup" in l.lower() for l in labels), \
        f"Expected an entity lookup example. Found: {labels}"


def test_examples_include_count():
    g = _load_examples()
    sparqls = [str(s) for s in g.objects(predicate=SH.select)]
    assert any("COUNT" in s for s in sparqls), \
        f"Expected a COUNT query. Found: {sparqls}"


def test_at_least_five_examples():
    g = _load_examples()
    examples = list(g.subjects(predicate=RDFS.label))
    assert len(examples) >= 5, f"Expected >= 5 examples, got {len(examples)}"
