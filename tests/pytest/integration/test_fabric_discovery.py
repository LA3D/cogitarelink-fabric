"""Tier 1 integration tests: fabric endpoint discovery (Docker stack only)."""
import pytest
import httpx
from agents.fabric_discovery import ShapeSummary, ExampleSummary, FabricEndpoint

GATEWAY = "http://localhost:8080"


def test_fabric_endpoint_routing_plan_contains_basics():
    """FabricEndpoint.routing_plan renders endpoint, vocabs, shapes, examples."""
    ep = FabricEndpoint(
        base="http://localhost:8080",
        sparql_url="http://localhost:8080/sparql",
        void_ttl="",
        profile_ttl="",
        shapes_ttl="",
        examples_ttl="",
        vocabularies=["http://www.w3.org/ns/sosa/", "http://www.w3.org/2006/time#"],
        conforms_to="https://w3id.org/cogitarelink/fabric#CoreProfile",
        shapes=[
            ShapeSummary(
                name="ObservationShape",
                target_class="sosa:Observation",
                agent_instruction="Query /graph/observations for sosa:Observation instances.",
                properties=["hasSimpleResult", "resultTime", "observedProperty"],
            )
        ],
        examples=[
            ExampleSummary(
                label="List recent observations",
                comment="Returns observations ordered by time.",
                sparql="SELECT ?obs WHERE { ?obs a sosa:Observation }",
                target="http://localhost:8080/sparql",
            )
        ],
    )
    plan = ep.routing_plan
    assert "http://localhost:8080" in plan
    assert "sosa" in plan.lower()
    assert "ObservationShape" in plan
    assert "List recent observations" in plan
    assert "CoreProfile" in plan


def test_discover_endpoint():
    """discover_endpoint returns FabricEndpoint with all four layers populated."""
    from agents.fabric_discovery import discover_endpoint
    ep = discover_endpoint(GATEWAY)
    assert ep.base == GATEWAY
    assert ep.sparql_url == f"{GATEWAY}/sparql"
    assert "http://www.w3.org/ns/sosa/" in ep.vocabularies
    assert "http://www.w3.org/2006/time#" in ep.vocabularies
    assert "CoreProfile" in ep.conforms_to
    assert len(ep.void_ttl) > 0
    assert len(ep.profile_ttl) > 0
    assert len(ep.shapes_ttl) > 0
    assert len(ep.examples_ttl) > 0


def test_discover_parses_shapes():
    """discover_endpoint extracts ShapeSummary from SHACL."""
    from agents.fabric_discovery import discover_endpoint
    ep = discover_endpoint(GATEWAY)
    assert len(ep.shapes) >= 1
    obs_shape = next((s for s in ep.shapes if "Observation" in s.target_class), None)
    assert obs_shape is not None
    assert obs_shape.agent_instruction is not None
    assert len(obs_shape.properties) >= 1


def test_discover_parses_examples():
    """discover_endpoint extracts ExampleSummary from spex: catalog."""
    from agents.fabric_discovery import discover_endpoint
    ep = discover_endpoint(GATEWAY)
    assert len(ep.examples) >= 1
    assert any("observation" in e.label.lower() for e in ep.examples)
    assert all(e.sparql.strip() for e in ep.examples)


def test_routing_plan_readable():
    """routing_plan contains shapes, examples, vocabularies from live endpoint."""
    from agents.fabric_discovery import discover_endpoint
    ep = discover_endpoint(GATEWAY)
    plan = ep.routing_plan
    assert "sosa" in plan.lower()
    assert "SPARQL" in plan
    assert "Observation" in plan


def test_discover_bad_endpoint():
    """Non-existent endpoint raises ConnectError."""
    from agents.fabric_discovery import discover_endpoint
    with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
        discover_endpoint("http://localhost:9999")
