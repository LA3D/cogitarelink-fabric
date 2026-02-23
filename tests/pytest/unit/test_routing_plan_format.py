"""Test routing plan text renders both URI spaces clearly."""
from agents.fabric_discovery import FabricEndpoint, ShapeSummary, ExampleSummary


def _make_endpoint() -> FabricEndpoint:
    return FabricEndpoint(
        base="http://x",
        sparql_url="http://x/sparql",
        void_ttl="",
        profile_ttl="",
        shapes_ttl="",
        examples_ttl="",
        vocabularies=["http://www.w3.org/ns/sosa/"],
        conforms_to="https://w3id.org/cogitarelink/fabric#CoreProfile",
        uri_space="http://x/entity/",
        prefix_declarations={"sosa": "http://www.w3.org/ns/sosa/"},
        named_graphs=[{"title": "Observations", "graph_uri": "http://x/graph/observations"}],
        shapes=[ShapeSummary(
            name="ObservationShape",
            target_class="sosa:Observation",
            agent_instruction="hint text",
            properties=["sosa:madeBySensor class=sosa:Sensor nodeKind=IRI pattern=^http://x/entity/"],
        )],
        examples=[ExampleSummary(
            label="List recent observations",
            comment="Returns observations.",
            sparql="SELECT ?obs WHERE { ?obs a sosa:Observation }",
            target="http://x/sparql",
        )],
    )


def test_routing_plan_contains_entity_uri_space():
    ep = _make_endpoint()
    plan = ep.routing_plan
    assert "Entity URI space:" in plan
    assert "http://x/entity/" in plan


def test_routing_plan_contains_ontology_cache():
    ep = _make_endpoint()
    plan = ep.routing_plan
    assert "ontology" in plan.lower() or "Local" in plan
    assert "sosa:" in plan


def test_routing_plan_contains_named_graphs():
    ep = _make_endpoint()
    plan = ep.routing_plan
    assert "Named graphs:" in plan
    assert "observations" in plan.lower()


def test_routing_plan_shows_property_types():
    ep = _make_endpoint()
    plan = ep.routing_plan
    assert "class=sosa:Sensor" in plan or "sosa:Sensor" in plan


def test_routing_plan_without_uri_space_still_works():
    ep = _make_endpoint()
    ep.uri_space = None
    ep.prefix_declarations = {}
    ep.named_graphs = []
    plan = ep.routing_plan
    assert "Endpoint:" in plan
    assert "Entity URI space:" not in plan
