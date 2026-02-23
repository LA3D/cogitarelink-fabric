"""Unit tests for fabric_rdfs_routes — no Docker, no network."""
from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

from agents.fabric_discovery import FabricEndpoint


def _make_ep(tbox) -> FabricEndpoint:
    return FabricEndpoint(
        base="http://localhost:8080",
        sparql_url="http://localhost:8080/sparql",
        void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
        tbox_graph=tbox,
    )


def _tiny_tbox() -> Graph:
    """Minimal OWL graph: one ObjectProperty with domain/range."""
    g = Graph()
    SIO = "http://semanticscience.org/resource/"
    prop = URIRef(SIO + "has-attribute")
    obs  = URIRef("http://www.w3.org/ns/sosa/Observation")
    mv   = URIRef(SIO + "MeasuredValue")
    g.add((prop, RDF.type, OWL.ObjectProperty))
    g.add((prop, RDFS.domain, obs))
    g.add((prop, RDFS.range, mv))
    return g


def test_no_tbox_returns_stub():
    from agents.fabric_rdfs_routes import make_rdfs_routes_tool
    ep = _make_ep(None)
    tool = make_rdfs_routes_tool(ep)
    result = tool("anything")
    assert "no" in result.lower() or "tbox" in result.lower() or "not available" in result.lower()


def test_with_tbox_returns_callable():
    from agents.fabric_rdfs_routes import make_rdfs_routes_tool
    ep = _make_ep(_tiny_tbox())
    tool = make_rdfs_routes_tool(ep)
    assert callable(tool)
    assert tool.__name__ == "analyze_rdfs_routes"


def test_tool_calls_lm_with_rdfs_prompt():
    from agents.fabric_rdfs_routes import make_rdfs_routes_tool
    ep = _make_ep(_tiny_tbox())
    tool = make_rdfs_routes_tool(ep)

    mock_lm = MagicMock(return_value=["ROUTING PLAN: ?x sio:has-attribute ?mv ."])

    with patch("dspy.settings") as mock_settings:
        mock_settings.lm = mock_lm
        result = tool("What is the range of sio:has-attribute?")

    assert mock_lm.called
    call_kwargs = mock_lm.call_args
    messages = call_kwargs[1].get("messages") or (call_kwargs[0][0] if call_kwargs[0] else None)
    if messages:
        prompt_text = messages[0]["content"] if isinstance(messages, list) else str(messages)
        assert "RDFS" in prompt_text or "ROUTING" in prompt_text
        assert "sio:has-attribute" in prompt_text
    assert "ROUTING PLAN" in result


def test_tool_no_lm_configured():
    from agents.fabric_rdfs_routes import make_rdfs_routes_tool
    ep = _make_ep(_tiny_tbox())
    tool = make_rdfs_routes_tool(ep)

    with patch("dspy.settings") as mock_settings:
        mock_settings.lm = None
        result = tool("What is the range of sio:has-attribute?")

    assert "no" in result.lower() or "llm" in result.lower() or "configured" in result.lower()
