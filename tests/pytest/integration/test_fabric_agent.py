"""Tier 3 integration tests: RLM agent end-to-end (Docker stack + LLM API).

Run with: ~/uvws/.venv/bin/python -m pytest tests/pytest/integration/test_fabric_agent.py -v -m llm
Requires: ANTHROPIC_API_KEY set, Docker stack running.
"""
import pytest
import httpx
from agents.fabric_discovery import discover_endpoint
from agents.fabric_agent import run_fabric_query

GATEWAY = "http://localhost:8080"


def _insert_test_observation(temp: float, sensor: str) -> None:
    """Insert a known observation into the fabric node for testing."""
    sparql_update = f"""
    PREFIX sosa: <http://www.w3.org/ns/sosa/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT DATA {{
        GRAPH <{GATEWAY}/graph/observations> {{
            <{GATEWAY}/entity/test-obs-agent> a sosa:Observation ;
                sosa:madeBySensor <{GATEWAY}/entity/{sensor}> ;
                sosa:hasSimpleResult "{temp}"^^xsd:double ;
                sosa:resultTime "2026-02-22T12:00:00Z"^^xsd:dateTime .
        }}
    }}
    """
    r = httpx.post(
        f"{GATEWAY}/sparql/update",
        data={"update": sparql_update},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    r.raise_for_status()


def _cleanup_test_observation() -> None:
    sparql_update = f"""
    DROP SILENT GRAPH <{GATEWAY}/graph/observations>
    """
    httpx.post(
        f"{GATEWAY}/sparql/update",
        data={"update": sparql_update},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


@pytest.mark.slow
@pytest.mark.llm
def test_agent_answers_from_self_description():
    """End-to-end: insert data, discover endpoint, RLM query, verify answer."""
    try:
        _insert_test_observation(temp=23.5, sensor="sensor-1")
        ep = discover_endpoint(GATEWAY)
        result = run_fabric_query(
            ep, "What temperature did sensor-1 measure?", verbose=True,
        )
        assert "23.5" in result.answer
        assert result.sparql is not None
        assert result.iterations > 0
        assert result.converged is True
    finally:
        _cleanup_test_observation()
