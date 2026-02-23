"""Test discovery parsing of void:uriSpace and SHACL property enhancements."""
from agents.fabric_discovery import _parse_void, _parse_shapes

VOID_TTL = """\
@prefix void: <http://rdfs.org/ns/void#> .
@prefix dct:  <http://purl.org/dc/terms/> .

<http://x/.well-known/void>
    a void:Dataset ;
    void:sparqlEndpoint <http://x/sparql> ;
    void:uriSpace "http://x/entity/" ;
    void:vocabulary <http://www.w3.org/ns/sosa/> ;
    dct:conformsTo <https://w3id.org/cogitarelink/fabric#CoreProfile> .
"""

SHAPES_TTL = """\
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix sosa:  <http://www.w3.org/ns/sosa/> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .

<http://x/.well-known/shacl>
    sh:declare [
        sh:prefix "sosa" ;
        sh:namespace "http://www.w3.org/ns/sosa/"^^xsd:anyURI ;
    ] .

fabric:TestShape
    a sh:NodeShape ;
    sh:targetClass sosa:Observation ;
    sh:property [
        sh:path sosa:madeBySensor ;
        sh:class sosa:Sensor ;
        sh:nodeKind sh:IRI ;
        sh:pattern "^http://x/entity/" ;
        sh:description "Sensor IRI in entity namespace." ;
    ] .
"""


def test_parse_void_extracts_uri_space():
    sparql_url, vocabs, conforms, uri_space, named_graphs = _parse_void(VOID_TTL)
    assert uri_space == "http://x/entity/"


def test_parse_void_returns_none_when_no_uri_space():
    ttl = """\
@prefix void: <http://rdfs.org/ns/void#> .
<http://x/.well-known/void> a void:Dataset ; void:sparqlEndpoint <http://x/sparql> .
"""
    _, _, _, uri_space, _ = _parse_void(ttl)
    assert uri_space is None


def test_parse_shapes_extracts_class_and_pattern():
    shapes = _parse_shapes(SHAPES_TTL)
    assert len(shapes) == 1
    s = shapes[0]
    # Find the madeBySensor property info
    sensor_props = [p for p in s.properties if "madeBySensor" in p]
    assert len(sensor_props) >= 1


def test_parse_shapes_extracts_prefix_declarations():
    from agents.fabric_discovery import _parse_prefix_declarations
    prefixes = _parse_prefix_declarations(SHAPES_TTL)
    assert "sosa" in prefixes
    assert prefixes["sosa"] == "http://www.w3.org/ns/sosa/"
