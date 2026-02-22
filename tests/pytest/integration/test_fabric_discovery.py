"""Tier 1 integration tests: fabric endpoint discovery (Docker stack only)."""
import pytest
from agents.fabric_discovery import ShapeSummary, ExampleSummary, FabricEndpoint


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
