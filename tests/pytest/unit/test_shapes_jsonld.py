"""Tests for WU-5: Shapes + SPARQL examples JSON-LD content negotiation (D22, Phase 2.5a)."""
import json
import pytest


def test_turtle_to_jsonld_produces_valid_json():
    from fabric.node.main import _turtle_to_jsonld
    ttl = """
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    <urn:shape/Test> a sh:NodeShape ; rdfs:label "Test shape" .
    """
    result = json.loads(_turtle_to_jsonld(ttl, "meta"))
    assert "@context" in result
    assert "meta" in result["@context"]


def test_turtle_to_jsonld_preserves_triples():
    from fabric.node.main import _turtle_to_jsonld
    ttl = """
    @prefix sh: <http://www.w3.org/ns/shacl#> .
    <urn:shape/A> a sh:NodeShape .
    <urn:shape/B> a sh:PropertyShape .
    """
    result = json.loads(_turtle_to_jsonld(ttl, "meta"))
    graph = result.get("@graph", [result])
    ids = [n.get("@id", "") for n in (graph if isinstance(graph, list) else [graph])]
    assert "urn:shape/A" in ids or any("shape/A" in i for i in ids)


def test_turtle_to_jsonld_empty_graph():
    from fabric.node.main import _turtle_to_jsonld
    result = json.loads(_turtle_to_jsonld("", "meta"))
    assert "@context" in result


def test_shacl_shapes_file_exists():
    """SHACL shapes source file exists for serving."""
    import pathlib
    shapes_dir = pathlib.Path(__file__).parents[3] / "shapes"
    assert (shapes_dir / "endpoint-sosa.ttl").exists()


def test_sparql_examples_file_exists():
    """SPARQL examples source file exists for serving."""
    import pathlib
    sparql_dir = pathlib.Path(__file__).parents[3] / "sparql"
    assert (sparql_dir / "sosa-examples.ttl").exists()
