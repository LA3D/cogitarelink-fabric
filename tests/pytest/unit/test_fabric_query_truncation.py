"""Unit tests for sparql_query tool truncation hint (TDD — written before implementation)."""
from unittest.mock import patch, MagicMock
import httpx
import pytest

from agents.fabric_query import make_fabric_query_tool
from agents.fabric_discovery import FabricEndpoint


def _make_ep():
    return FabricEndpoint(
        base="http://localhost:8080",
        sparql_url="http://localhost:8080/sparql",
        void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
    )


def _mock_response(text: str, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


def test_small_result_returned_unchanged():
    ep = _make_ep()
    tool = make_fabric_query_tool(ep, max_chars=100)
    small = '{"results":{"bindings":[]}}'
    with patch("httpx.post", return_value=_mock_response(small)):
        result = tool("SELECT ?s WHERE {?s ?p ?o}")
    assert result == small


def test_large_result_is_truncated():
    ep = _make_ep()
    tool = make_fabric_query_tool(ep, max_chars=100)
    large = "x" * 500
    with patch("httpx.post", return_value=_mock_response(large)):
        result = tool("SELECT ?s WHERE {?s ?p ?o}")
    assert len(result) < len(large)
    assert "truncated" in result.lower()


def test_truncation_message_suggests_llm_query():
    """When truncated, the message should tell the agent to use llm_query() for analysis."""
    ep = _make_ep()
    tool = make_fabric_query_tool(ep, max_chars=50)
    large = "x" * 500
    with patch("httpx.post", return_value=_mock_response(large)):
        result = tool("SELECT ?s WHERE {?s ?p ?o}")
    assert "llm_query" in result


def test_truncation_message_includes_total_size():
    ep = _make_ep()
    tool = make_fabric_query_tool(ep, max_chars=50)
    large = "y" * 300
    with patch("httpx.post", return_value=_mock_response(large)):
        result = tool("SELECT ?s WHERE {?s ?p ?o}")
    assert "300" in result
