"""Fabric SPARQL query tool factory — bounded, sync, error-surfacing."""
from __future__ import annotations
from typing import Callable
import re
import httpx
from agents.fabric_discovery import FabricEndpoint

# Detects triple patterns with unbound predicate AND object variables.
# Catches: <iri> ?p ?o, ?s ?p ?o — the "entity lookup escape hatch".
_UNBOUNDED_SCAN = re.compile(
    r'(?:<[^>]+>|\?\w+)\s+'   # subject: IRI or variable
    r'\?\w+\s+'                # predicate: variable (this is what we detect)
    r'\?\w+',                  # object: variable
)

_UNBOUNDED_MSG = (
    "Query rejected: unbounded predicate scan (?p ?o) is too expensive on "
    "large graphs. Specify predicates explicitly. If unsure which predicates "
    "to use, consult analyze_rdfs_routes() or check the SHACL shape declarations."
)


def _is_unbounded_scan(query: str) -> bool:
    """Detect unbounded predicate scans like <iri> ?p ?o or ?s ?p ?o."""
    body = re.sub(r'PREFIX\s+\S+\s+<[^>]+>', '', query, flags=re.IGNORECASE)
    body = re.sub(r'#[^\n]*', '', body)
    return bool(_UNBOUNDED_SCAN.search(body))


def make_fabric_query_tool(
    ep: FabricEndpoint,
    max_chars: int = 10_000,
    reject_unbounded: bool = False,
) -> Callable:
    """Return a sparql_query(query) function bound to ep's SPARQL endpoint.

    The returned function is sync (for dspy.RLM REPL), bounded (truncates
    large results), and error-surfacing (returns error strings, not exceptions).

    When reject_unbounded=True, queries with unbound predicate+object variables
    (?p ?o patterns) are rejected before execution.
    """
    def sparql_query(query: str) -> str:
        """Execute SPARQL against the fabric endpoint. Returns JSON results.
        Results are truncated to ~10k chars. On error, returns error description."""
        try:
            if reject_unbounded and _is_unbounded_scan(query):
                return _UNBOUNDED_MSG
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
