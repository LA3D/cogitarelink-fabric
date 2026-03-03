"""Integration test: SHACL validation against live fabric endpoint (Docker stack)."""
import os
import httpx
from agents.fabric_discovery import discover_endpoint
from tests.pytest.integration.conftest import _auth_headers

GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")


def test_validate_live_observation(vp_token):
    """Insert observation, CONSTRUCT it back, validate against endpoint shapes."""
    from agents.fabric_validate import validate_result
    sparql_insert = f"""
    PREFIX sosa: <http://www.w3.org/ns/sosa/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT DATA {{
        GRAPH <{GATEWAY}/graph/observations> {{
            <{GATEWAY}/entity/test-obs-validate> a sosa:Observation ;
                sosa:hasSimpleResult "42.0"^^xsd:double ;
                sosa:resultTime "2026-02-23T10:00:00Z"^^xsd:dateTime .
        }}
    }}
    """
    try:
        httpx.post(
            f"{GATEWAY}/sparql/update",
            data={"update": sparql_insert},
            headers=_auth_headers(vp_token, {"Content-Type": "application/x-www-form-urlencoded"}),
        ).raise_for_status()

        # CONSTRUCT the observation back as Turtle
        construct = f"""
        CONSTRUCT {{ ?s ?p ?o }}
        WHERE {{ GRAPH <{GATEWAY}/graph/observations> {{
            <{GATEWAY}/entity/test-obs-validate> ?p ?o .
            BIND(<{GATEWAY}/entity/test-obs-validate> AS ?s)
        }} }}
        """
        r = httpx.post(
            f"{GATEWAY}/sparql",
            data={"query": construct},
            headers=_auth_headers(vp_token, {"Accept": "text/turtle"}),
        )
        r.raise_for_status()
        data_ttl = r.text

        ep = discover_endpoint(GATEWAY, vp_token=vp_token)
        result = validate_result(data_ttl, ep.shapes_ttl, tbox_graph=ep.tbox_graph)
        assert result.conforms is True
    finally:
        httpx.post(
            f"{GATEWAY}/sparql/update",
            data={"update": f"DROP SILENT GRAPH <{GATEWAY}/graph/observations>"},
            headers=_auth_headers(vp_token, {"Content-Type": "application/x-www-form-urlencoded"}),
        )
