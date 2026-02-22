# Placeholder — unit tests grow as logic worth isolating is extracted from main.py.
# Phase 1 acceptance layer is HURL (HTTP integration); unit tests cover pure functions.
# Note: fabric.node.main requires fastapi/httpx (Docker container deps, not global venv).
# Tests here use only stdlib + rdflib/pyshacl (available in ~/uvws/.venv).


def test_void_turtle_contains_required_terms():
    """VoID Turtle template correctly interpolates base URL."""
    VOID_TURTLE = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .

<{base}/.well-known/void>
    a void:Dataset ;
    void:sparqlEndpoint <{base}/sparql> .
"""
    rendered = VOID_TURTLE.format(base="http://example.org")
    assert "http://example.org/.well-known/void" in rendered
    assert "void:sparqlEndpoint" in rendered
    assert "http://example.org/sparql" in rendered


def test_shapes_file_contains_required_shacl_terms():
    """SHACL shapes file exists and contains required terms."""
    import pathlib
    root = pathlib.Path(__file__).parent.parent.parent.parent
    shapes = root / "shapes" / "endpoint-sosa.ttl"
    assert shapes.exists(), f"shapes file missing: {shapes}"
    content = shapes.read_text()
    assert "sh:NodeShape" in content
    assert "sh:targetClass" in content
    assert "sh:agentInstruction" in content
