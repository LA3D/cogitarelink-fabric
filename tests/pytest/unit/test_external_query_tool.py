"""Unit tests for make_external_query_tool — external SPARQL endpoint querying."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[3]))

import pytest
from unittest.mock import patch, MagicMock
from agents.fabric_discovery import FabricEndpoint, ExternalService, ExampleSummary


def _ep_with_services(urls=None):
    """Build a FabricEndpoint with external_services for testing."""
    if urls is None:
        urls = ["https://qlever.cs.uni-freiburg.de/api/pubchem"]
    services = [
        ExternalService(title=f"svc-{i}", endpoint_url=u, description="test", vocabularies=[], examples=[])
        for i, u in enumerate(urls)
    ]
    return FabricEndpoint(
        base="http://localhost:8080",
        sparql_url="http://localhost:8080/sparql",
        void_ttl="", profile_ttl="", shapes_ttl="", examples_ttl="",
        external_services=services,
    )


class TestMakeExternalQueryTool:
    def test_import(self):
        from agents.fabric_query import make_external_query_tool

    def test_returns_callable(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services()
        fn = make_external_query_tool(ep)
        assert callable(fn)

    def test_function_name(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services()
        fn = make_external_query_tool(ep)
        assert fn.__name__ == "query_external_sparql"

    def test_rejects_unlisted_url(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://allowed.example.org/sparql"])
        fn = make_external_query_tool(ep)
        result = fn("https://evil.example.org/sparql", "SELECT 1")
        assert "not in catalog" in result.lower() or "not allowed" in result.lower()

    def test_accepts_listed_url(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://qlever.cs.uni-freiburg.de/api/pubchem"])
        fn = make_external_query_tool(ep)
        mock_resp = MagicMock()
        mock_resp.text = '{"head":{"vars":["x"]},"results":{"bindings":[]}}'
        mock_resp.raise_for_status = MagicMock()
        with patch("agents.fabric_query.httpx.post", return_value=mock_resp):
            result = fn("https://qlever.cs.uni-freiburg.de/api/pubchem", "SELECT 1")
        assert "bindings" in result

    def test_truncates_large_results(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://example.org/sparql"])
        fn = make_external_query_tool(ep, max_chars=100)
        mock_resp = MagicMock()
        mock_resp.text = "x" * 200
        mock_resp.raise_for_status = MagicMock()
        with patch("agents.fabric_query.httpx.post", return_value=mock_resp):
            result = fn("https://example.org/sparql", "SELECT 1")
        assert "truncated" in result
        assert len(result) < 200

    def test_follows_redirects(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://example.org/sparql"])
        fn = make_external_query_tool(ep)
        mock_resp = MagicMock()
        mock_resp.text = '{"head":{"vars":[]},"results":{"bindings":[]}}'
        mock_resp.raise_for_status = MagicMock()
        with patch("agents.fabric_query.httpx.post", return_value=mock_resp) as mock_post:
            fn("https://example.org/sparql", "SELECT 1")
            call_kwargs = mock_post.call_args
            assert call_kwargs.kwargs.get("follow_redirects") is True

    def test_surfaces_http_errors(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services(["https://example.org/sparql"])
        fn = make_external_query_tool(ep)
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.raise_for_status.side_effect = Exception("HTTP 500")
        with patch("agents.fabric_query.httpx.post", return_value=mock_resp):
            result = fn("https://example.org/sparql", "SELECT 1")
        assert "error" in result.lower()

    def test_no_services_means_all_rejected(self):
        from agents.fabric_query import make_external_query_tool
        ep = _ep_with_services([])
        fn = make_external_query_tool(ep)
        result = fn("https://example.org/sparql", "SELECT 1")
        assert "not in catalog" in result.lower() or "not allowed" in result.lower()
