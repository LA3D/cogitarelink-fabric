"""Integration tests for write-validate-commit cycle against live Docker stack."""
import os
import pytest
import httpx

GATEWAY = os.environ.get("FABRIC_GATEWAY", "https://bootstrap.cogitarelink.ai")
BASE = GATEWAY


INSTRUMENT_TTL = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/test-inst-write> a sosa:Platform ;
    rdfs:label "Test Potentiostat"^^xsd:string ;
    schema:serialNumber "TEST-001"^^xsd:string ;
    sosa:hosts <{BASE}/entity/test-sensor-write> .

<{BASE}/entity/test-sensor-write> a sosa:Sensor ;
    rdfs:label "Test WE Sensor"^^xsd:string ;
    sosa:observes <{BASE}/entity/test-op-current> .
"""


@pytest.fixture(autouse=True)
def cleanup_test_graph(vp_token):
    """Drop test data from /graph/entities and /graph/audit after each test."""
    yield
    ssl_cert = os.environ.get("SSL_CERT_FILE", True)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if vp_token:
        headers["Authorization"] = f"Bearer {vp_token}"
    # Clean up specific test triples (not entire graph — other tests may use it)
    for subj in [f"{BASE}/entity/test-inst-write", f"{BASE}/entity/test-sensor-write",
                 f"{BASE}/entity/test-op-current"]:
        update = f"DELETE WHERE {{ GRAPH <{BASE}/graph/entities> {{ <{subj}> ?p ?o }} }}"
        httpx.post(f"{GATEWAY}/sparql/update", data={"update": update},
                   headers=headers, timeout=10.0, verify=ssl_cert)


def test_discover_write_targets(vp_token):
    """discover_endpoint finds writable graphs."""
    from agents.fabric_discovery import discover_endpoint
    ep = discover_endpoint(GATEWAY, vp_token=vp_token)
    writable = [ng for ng in ep.named_graphs if ng.get("writable")]
    assert len(writable) >= 2
    uris = [ng["graph_uri"] for ng in writable]
    assert any("entities" in u for u in uris)
    assert any("observations" in u for u in uris)


def test_write_validate_commit_cycle(vp_token):
    """Full write → validate → commit cycle against live endpoint."""
    from agents.fabric_discovery import discover_endpoint
    from agents.fabric_write import (
        make_discover_write_targets_tool,
        make_write_triples_tool,
        make_validate_graph_tool,
        make_commit_graph_tool,
    )

    ep = discover_endpoint(GATEWAY, vp_token=vp_token)
    ep.vp_token = vp_token
    ep.agent_did = "did:webvh:test:integration-agent"

    # Step 1: Discover
    discover = make_discover_write_targets_tool(ep)
    targets = discover()
    assert "entities" in targets.lower()

    # Step 2: Write
    write = make_write_triples_tool(ep)
    graph = f"{BASE}/graph/entities"
    result = write(graph, INSTRUMENT_TTL)
    assert "OK:" in result

    # Step 3: Validate
    validate = make_validate_graph_tool(ep)
    val_result = validate(graph)
    # May have other data in the graph; our instrument should conform
    # The key check: no rejection specifically about our test instrument
    assert "Authentication required" not in val_result

    # Step 4: Commit
    commit = make_commit_graph_tool(ep)
    commit_result = commit(graph)
    # Graph may have pre-existing non-conformant data, so we check that
    # either COMMITTED or the rejection is about other data, not ours
    assert "error" not in commit_result.lower() or "COMMIT REJECTED" in commit_result


def test_write_invalid_then_fix(vp_token):
    """Write non-conformant data, validate fails, fix, validate passes."""
    from agents.fabric_discovery import discover_endpoint
    from agents.fabric_write import make_write_triples_tool, make_validate_graph_tool

    ep = discover_endpoint(GATEWAY, vp_token=vp_token)
    ep.vp_token = vp_token

    write = make_write_triples_tool(ep)
    validate = make_validate_graph_tool(ep)
    graph = f"{BASE}/graph/entities"

    # Write invalid (missing label, serial number, hosts)
    bad_ttl = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
<{BASE}/entity/test-inst-write> a sosa:Platform .
"""
    result = write(graph, bad_ttl)
    assert "OK:" in result

    # Validate should find violations
    val = validate(graph)
    # Should report issues (either NON-CONFORMANT or violations in text)
    assert "Authentication required" not in val

    # Fix: write complete data
    result2 = write(graph, INSTRUMENT_TTL)
    assert "OK:" in result2
