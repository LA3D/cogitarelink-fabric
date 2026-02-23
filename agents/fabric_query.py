"""Fabric SPARQL query tool factory — bounded, sync, error-surfacing."""
from __future__ import annotations
from typing import Callable
import httpx
from agents.fabric_discovery import FabricEndpoint


def make_fabric_query_tool(ep: FabricEndpoint, max_chars: int = 10_000) -> Callable:
    """Return a sparql_query(query) function bound to ep's SPARQL endpoint.

    The returned function is sync (for dspy.RLM REPL), bounded (truncates
    large results), and error-surfacing (returns error strings, not exceptions).
    """
    def sparql_query(query: str) -> str:
        """Execute SPARQL against the fabric endpoint. Returns JSON results.
        Results are truncated to ~10k chars. On error, returns error description."""
        try:
            r = httpx.post(
                ep.sparql_url,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30.0,
            )
            r.raise_for_status()
            txt = r.text
            if len(txt) > max_chars:
                return txt[:max_chars] + f"\n... truncated ({len(txt)} total chars). Use llm_query() to analyse large results."
            return txt
        except httpx.HTTPStatusError as e:
            return f"SPARQL error (HTTP {e.response.status_code}): {e.response.text[:500]}"
        except Exception as e:
            return f"SPARQL error: {e}"
    return sparql_query
