"""Tier 2 integration tests: fabric SPARQL query tool (Docker stack only)."""
import json
from agents.fabric_discovery import discover_endpoint
from agents.fabric_query import make_fabric_query_tool

GATEWAY = "http://localhost:8080"


def test_sparql_query_tool_returns_json():
    """Tool executes SPARQL and returns JSON results."""
    ep = discover_endpoint(GATEWAY)
    query_fn = make_fabric_query_tool(ep)
    result = query_fn("SELECT * WHERE {} LIMIT 1")
    parsed = json.loads(result)
    assert "results" in parsed
    assert "bindings" in parsed["results"]


def test_sparql_query_with_sosa():
    """Tool can query SOSA vocabulary from TBox graph."""
    ep = discover_endpoint(GATEWAY)
    query_fn = make_fabric_query_tool(ep)
    result = query_fn(
        "PREFIX sosa: <http://www.w3.org/ns/sosa/> "
        "PREFIX owl: <http://www.w3.org/2002/07/owl#> "
        "ASK { GRAPH <http://localhost:8080/ontology/sosa> { sosa:Observation a owl:Class } }"
    )
    assert "true" in result.lower()


def test_sparql_error_surfaced_as_string():
    """Malformed SPARQL returns error string, not exception."""
    ep = discover_endpoint(GATEWAY)
    query_fn = make_fabric_query_tool(ep)
    result = query_fn("NOT VALID SPARQL")
    assert "error" in result.lower()


def test_sparql_result_bounded():
    """Results exceeding max_chars are truncated."""
    ep = discover_endpoint(GATEWAY)
    query_fn = make_fabric_query_tool(ep, max_chars=50)
    result = query_fn("SELECT * WHERE {} LIMIT 1")
    assert len(result) <= 200  # truncated + suffix message
