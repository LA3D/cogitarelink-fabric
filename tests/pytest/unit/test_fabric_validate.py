"""Unit tests for SHACL validation tool (no Docker needed)."""
import pytest
from agents.fabric_validate import validate_result, ValidationResult, make_validate_tool
from agents.fabric_discovery import FabricEndpoint


SHAPES_TTL = """\
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix sosa:  <http://www.w3.org/ns/sosa/> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .

fabric:ObservationShape
    a sh:NodeShape ;
    sh:targetClass sosa:Observation ;
    sh:agentInstruction "Query /graph/observations for sosa:Observation instances." ;
    sh:property [
        sh:path sosa:hasSimpleResult ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
    ] ;
    sh:property [
        sh:path sosa:resultTime ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:dateTime ;
    ] .
"""

VALID_OBS_TTL = """\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

<urn:obs:1> a sosa:Observation ;
    sosa:hasSimpleResult "23.5"^^xsd:double ;
    sosa:resultTime "2026-02-22T12:00:00Z"^^xsd:dateTime .
"""

INVALID_OBS_TTL = """\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

<urn:obs:2> a sosa:Observation ;
    sosa:hasSimpleResult "23.5"^^xsd:double .
"""


def test_valid_observation_conforms():
    r = validate_result(VALID_OBS_TTL, SHAPES_TTL)
    assert r.conforms is True
    assert len(r.violations) == 0


def test_missing_result_time_violates():
    r = validate_result(INVALID_OBS_TTL, SHAPES_TTL)
    assert r.conforms is False
    assert len(r.violations) >= 1
    paths = [v.path for v in r.violations if v.path]
    assert any("resultTime" in p for p in paths)


def test_agent_hints_extracted():
    r = validate_result(INVALID_OBS_TTL, SHAPES_TTL)
    assert r.conforms is False
    assert len(r.hints) >= 1
    assert any("/graph/observations" in h for h in r.hints)


def test_make_validate_tool_returns_string():
    ep = FabricEndpoint(
        base="http://localhost:8080",
        sparql_url="http://localhost:8080/sparql",
        void_ttl="", profile_ttl="",
        shapes_ttl=SHAPES_TTL,
        examples_ttl="",
    )
    tool = make_validate_tool(ep)
    assert callable(tool)
    result_str = tool(VALID_OBS_TTL)
    assert "CONFORMS" in result_str
    result_str = tool(INVALID_OBS_TTL)
    assert "VIOLATIONS" in result_str
