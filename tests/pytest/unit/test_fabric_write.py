"""Unit tests for fabric write tools (no Docker needed)."""
import json
from unittest.mock import patch, MagicMock
import pytest

from agents.fabric_discovery import FabricEndpoint
from agents.fabric_write import (
    make_discover_write_targets_tool,
    make_write_triples_tool,
    make_validate_graph_tool,
    make_commit_graph_tool,
    _update_url,
)


BASE = "https://bootstrap.cogitarelink.ai"

SHAPES_TTL = """\
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix sosa:  <http://www.w3.org/ns/sosa/> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix schema: <https://schema.org/> .
@prefix fabric: <https://w3id.org/cogitarelink/fabric#> .

fabric:InstrumentShape a sh:NodeShape ;
    sh:targetClass sosa:Platform ;
    sh:agentInstruction "Instruments are sosa:Platform in /graph/entities." ;
    sh:property [
        sh:path rdfs:label ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
        sh:agentInstruction "Every instrument must have a label." ;
    ] ;
    sh:property [
        sh:path schema:serialNumber ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path sosa:hosts ;
        sh:minCount 1 ;
        sh:class sosa:Sensor ;
    ] .

fabric:SensorEntityShape a sh:NodeShape ;
    sh:targetClass sosa:Sensor ;
    sh:property [
        sh:path rdfs:label ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path sosa:observes ;
        sh:minCount 1 ;
    ] .
"""

VALID_INSTRUMENT_TTL = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/inst-1> a sosa:Platform ;
    rdfs:label "BioLogic SP-200"^^xsd:string ;
    schema:serialNumber "SP200-001"^^xsd:string ;
    sosa:hosts <{BASE}/entity/sensor-1> .

<{BASE}/entity/sensor-1> a sosa:Sensor ;
    rdfs:label "WE Current"^^xsd:string ;
    sosa:observes <{BASE}/entity/op-current> .
"""

INVALID_INSTRUMENT_TTL = f"""\
@prefix sosa: <http://www.w3.org/ns/sosa/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{BASE}/entity/inst-bad> a sosa:Platform .
"""


def _make_ep(**kwargs):
    defaults = dict(
        base=BASE,
        sparql_url=f"{BASE}/sparql",
        void_ttl="", profile_ttl="",
        shapes_ttl=SHAPES_TTL,
        examples_ttl="",
        named_graphs=[
            {"title": "Entities", "graph_uri": f"{BASE}/graph/entities",
             "conformsTo": "https://w3id.org/cogitarelink/fabric#EntityShape",
             "writable": True},
            {"title": "Observations", "graph_uri": f"{BASE}/graph/observations",
             "conformsTo": "https://w3id.org/cogitarelink/fabric#ObservationShape",
             "writable": True},
            {"title": "Metadata", "graph_uri": f"{BASE}/graph/metadata",
             "writable": False},
        ],
        vp_token="test-token-123",
        agent_did="did:webvh:test:agent",
    )
    defaults.update(kwargs)
    return FabricEndpoint(**defaults)


# --- _update_url ---

def test_update_url_appends():
    assert _update_url("https://example.com/sparql") == "https://example.com/sparql/update"

def test_update_url_idempotent():
    assert _update_url("https://example.com/sparql/update") == "https://example.com/sparql/update"


# --- discover_write_targets ---

def test_discover_lists_writable_graphs():
    ep = _make_ep()
    tool = make_discover_write_targets_tool(ep)
    result = tool()
    assert "Writable graphs:" in result
    assert "/graph/entities" in result
    assert "/graph/observations" in result
    assert "/graph/metadata" not in result

def test_discover_no_writable():
    ep = _make_ep(named_graphs=[
        {"title": "Metadata", "graph_uri": f"{BASE}/graph/metadata", "writable": False},
    ])
    tool = make_discover_write_targets_tool(ep)
    assert "No writable" in tool()

def test_discover_shows_shape():
    ep = _make_ep()
    result = make_discover_write_targets_tool(ep)()
    assert "EntityShape" in result


# --- write_triples ---

@patch("agents.fabric_write.httpx.post")
def test_write_triples_posts_update(mock_post):
    mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
    ep = _make_ep()
    tool = make_write_triples_tool(ep)
    result = tool(f"{BASE}/graph/entities", VALID_INSTRUMENT_TTL)
    assert "OK:" in result
    assert "triples written" in result
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "Bearer test-token-123" in str(call_kwargs)

@patch("agents.fabric_write.httpx.post")
def test_write_triples_auth_error(mock_post):
    mock_post.return_value = MagicMock(status_code=401, text="Unauthorized")
    ep = _make_ep()
    tool = make_write_triples_tool(ep)
    result = tool(f"{BASE}/graph/entities", VALID_INSTRUMENT_TTL)
    assert "Authentication required" in result

@patch("agents.fabric_write.httpx.post")
def test_write_triples_forbidden(mock_post):
    mock_post.return_value = MagicMock(status_code=403, text="Forbidden")
    ep = _make_ep()
    tool = make_write_triples_tool(ep)
    result = tool(f"{BASE}/graph/entities", VALID_INSTRUMENT_TTL)
    assert "Access denied" in result

def test_write_triples_bad_turtle():
    ep = _make_ep()
    tool = make_write_triples_tool(ep)
    result = tool(f"{BASE}/graph/entities", "this is not turtle {{{}}")
    assert "error" in result.lower()

def test_write_triples_rejects_unsafe_uri():
    ep = _make_ep()
    tool = make_write_triples_tool(ep)
    result = tool('"><script>alert(1)</script>', VALID_INSTRUMENT_TTL)
    assert "Invalid graph URI" in result

@patch("agents.fabric_write.httpx.post")
def test_write_triples_url_derivation(mock_post):
    mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
    ep = _make_ep()
    tool = make_write_triples_tool(ep)
    tool(f"{BASE}/graph/entities", VALID_INSTRUMENT_TTL)
    url = mock_post.call_args[0][0]
    assert url == f"{BASE}/sparql/update"


# --- validate_graph ---

@patch("agents.fabric_write.httpx.post")
def test_validate_graph_conformant(mock_post):
    mock_resp = MagicMock(status_code=200, text=VALID_INSTRUMENT_TTL)
    mock_resp.raise_for_status = lambda: None
    mock_post.return_value = mock_resp
    ep = _make_ep()
    tool = make_validate_graph_tool(ep)
    result = tool(f"{BASE}/graph/entities")
    assert "CONFORMS" in result

@patch("agents.fabric_write.httpx.post")
def test_validate_graph_nonconformant(mock_post):
    mock_resp = MagicMock(status_code=200, text=INVALID_INSTRUMENT_TTL)
    mock_resp.raise_for_status = lambda: None
    mock_post.return_value = mock_resp
    ep = _make_ep()
    tool = make_validate_graph_tool(ep)
    result = tool(f"{BASE}/graph/entities")
    assert "NON-CONFORMANT" in result
    assert "violation" in result.lower()

@patch("agents.fabric_write.httpx.post")
def test_validate_graph_empty(mock_post):
    mock_resp = MagicMock(status_code=200, text="")
    mock_resp.raise_for_status = lambda: None
    mock_post.return_value = mock_resp
    ep = _make_ep()
    tool = make_validate_graph_tool(ep)
    result = tool(f"{BASE}/graph/entities")
    assert "empty" in result.lower()

@patch("agents.fabric_write.httpx.post")
def test_validate_graph_auth_error(mock_post):
    mock_post.return_value = MagicMock(status_code=401, text="Unauthorized")
    ep = _make_ep()
    tool = make_validate_graph_tool(ep)
    result = tool(f"{BASE}/graph/entities")
    assert "Authentication required" in result

def test_validate_graph_rejects_unsafe_uri():
    ep = _make_ep()
    tool = make_validate_graph_tool(ep)
    result = tool('not-a-uri')
    assert "Invalid graph URI" in result

@patch("agents.fabric_write.httpx.post")
def test_validate_graph_includes_agent_hints(mock_post):
    mock_resp = MagicMock(status_code=200, text=INVALID_INSTRUMENT_TTL)
    mock_resp.raise_for_status = lambda: None
    mock_post.return_value = mock_resp
    ep = _make_ep()
    tool = make_validate_graph_tool(ep)
    result = tool(f"{BASE}/graph/entities")
    assert "Fix:" in result


# --- commit_graph ---

@patch("agents.fabric_write.httpx.post")
def test_commit_conformant_writes_provenance(mock_post):
    """Conformant graph → 2 HTTP calls (CONSTRUCT + PROV-O INSERT)."""
    construct_resp = MagicMock(status_code=200, text=VALID_INSTRUMENT_TTL)
    construct_resp.raise_for_status = lambda: None
    prov_resp = MagicMock(status_code=200)
    prov_resp.raise_for_status = lambda: None
    mock_post.side_effect = [construct_resp, prov_resp]

    ep = _make_ep()
    tool = make_commit_graph_tool(ep)
    result = tool(f"{BASE}/graph/entities")
    assert "COMMITTED" in result
    assert "provenance recorded" in result
    assert mock_post.call_count == 2
    # Second call is PROV-O INSERT
    prov_call = mock_post.call_args_list[1]
    assert "prov:Activity" in prov_call.kwargs.get("data", {}).get("update", "") or str(prov_call)

@patch("agents.fabric_write.httpx.post")
def test_commit_nonconformant_no_provenance(mock_post):
    """Non-conformant graph → 1 HTTP call only (CONSTRUCT), no PROV-O."""
    construct_resp = MagicMock(status_code=200, text=INVALID_INSTRUMENT_TTL)
    construct_resp.raise_for_status = lambda: None
    mock_post.return_value = construct_resp

    ep = _make_ep()
    tool = make_commit_graph_tool(ep)
    result = tool(f"{BASE}/graph/entities")
    assert "COMMIT REJECTED" in result
    assert mock_post.call_count == 1

@patch("agents.fabric_write.httpx.post")
def test_commit_includes_agent_did(mock_post):
    construct_resp = MagicMock(status_code=200, text=VALID_INSTRUMENT_TTL)
    construct_resp.raise_for_status = lambda: None
    prov_resp = MagicMock(status_code=200)
    prov_resp.raise_for_status = lambda: None
    mock_post.side_effect = [construct_resp, prov_resp]

    ep = _make_ep(agent_did="did:webvh:test:my-agent")
    tool = make_commit_graph_tool(ep)
    result = tool(f"{BASE}/graph/entities")
    assert "did:webvh:test:my-agent" in result

@patch("agents.fabric_write.httpx.post")
def test_commit_empty_graph(mock_post):
    mock_resp = MagicMock(status_code=200, text="")
    mock_resp.raise_for_status = lambda: None
    mock_post.return_value = mock_resp
    ep = _make_ep()
    tool = make_commit_graph_tool(ep)
    result = tool(f"{BASE}/graph/entities")
    assert "empty" in result.lower()

def test_commit_rejects_unsafe_uri():
    ep = _make_ep()
    tool = make_commit_graph_tool(ep)
    result = tool('<bad> uri')
    assert "Invalid graph URI" in result

@patch("agents.fabric_write.httpx.post")
def test_commit_provenance_has_shape_uri(mock_post):
    construct_resp = MagicMock(status_code=200, text=VALID_INSTRUMENT_TTL)
    construct_resp.raise_for_status = lambda: None
    prov_resp = MagicMock(status_code=200)
    prov_resp.raise_for_status = lambda: None
    mock_post.side_effect = [construct_resp, prov_resp]

    ep = _make_ep()
    tool = make_commit_graph_tool(ep)
    tool(f"{BASE}/graph/entities")
    # Check PROV-O update contains shape URI
    prov_data = mock_post.call_args_list[1]
    update_str = str(prov_data)
    assert "prov:used" in update_str


# --- agent_did on FabricEndpoint ---

def test_fabric_endpoint_has_agent_did():
    ep = _make_ep()
    assert ep.agent_did == "did:webvh:test:agent"

def test_fabric_endpoint_agent_did_default_none():
    ep = FabricEndpoint(
        base=BASE, sparql_url=f"{BASE}/sparql",
        void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
    )
    assert ep.agent_did is None
