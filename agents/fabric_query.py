"""Fabric SPARQL query tool factory — bounded, sync, error-surfacing."""
from __future__ import annotations
from typing import Callable
import re
import httpx
from agents.fabric_discovery import FabricEndpoint, _ssl_verify

# Detects triple patterns with unbound predicate AND object variables.
# Catches: <iri> ?p ?o, ?s ?p ?o — the "entity lookup escape hatch".
# Key: predicate must be a ?variable (not a prefixed name like sosa:x or <URI>).
# We split on . and ; (SPARQL triple-pattern terminators) to avoid matching
# across adjacent triple patterns like "?obs sosa:madeBySensor ?sensor ;
# sosa:resultTime ?time" where ?sensor and ?time are in different patterns.
_UNBOUNDED_PRED = re.compile(
    r'(?:<[^>]+>|\?\w+)\s+'    # subject: IRI or variable
    r'(\?\w+)\s+'               # predicate: MUST be variable (captured)
    r'(?:\?\w+|<[^>]+>)',       # object: variable or IRI
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
    # Extract only the WHERE clause body (skip SELECT, ORDER BY, etc.)
    where_match = re.search(r'WHERE\s*\{(.+)\}\s*(?:ORDER|GROUP|LIMIT|OFFSET|$)',
                            body, flags=re.IGNORECASE | re.DOTALL)
    if not where_match:
        return False
    where_body = where_match.group(1)
    # Replace <URIs> with placeholder to prevent dots in domain names
    # from being treated as triple-pattern terminators.
    where_body = re.sub(r'<[^>]+>', '<_IRI_>', where_body)
    # Split on . and ; (SPARQL triple-pattern terminators)
    fragments = re.split(r'[.;]', where_body)
    for frag in fragments:
        frag = frag.strip()
        if not frag:
            continue
        m = _UNBOUNDED_PRED.search(frag)
        if m:
            pred = m.group(1)
            # 'a' is the SPARQL keyword for rdf:type, not a variable
            if pred == 'a':
                continue
            return True
    return False


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
            headers = {"Accept": "application/sparql-results+json"}
            if ep.vp_token:
                headers["Authorization"] = f"Bearer {ep.vp_token}"
            r = httpx.post(
                ep.sparql_url,
                data={"query": query},
                headers=headers,
                timeout=30.0,
                verify=_ssl_verify(),
            )
            if r.status_code == 401:
                return (
                    "Authentication required: the SPARQL endpoint requires a VP Bearer token "
                    "in the Authorization header. The sparql_query tool was not configured with "
                    "a valid token. This is a configuration issue, not a query issue — "
                    "retry the same query after the tool is re-initialized with credentials."
                )
            if r.status_code == 403:
                return (
                    "Access denied: your agent credentials were rejected. "
                    "Check that your agentRole has permission for this operation and graph. "
                    f"Detail: {r.text[:300]}"
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


def make_external_query_tool(
    ep: FabricEndpoint,
    max_chars: int = 10_000,
) -> Callable:
    """Return a query_external_sparql(endpoint_url, query) function for catalog-listed endpoints.

    Only allows URLs that appear in ep.external_services (safety gate).
    Follows redirects (QLever returns 308). Same error-surfacing pattern as sparql_query.
    """
    allowed = {svc.endpoint_url for svc in ep.external_services}

    def query_external_sparql(endpoint_url: str, query: str) -> str:
        """Execute SPARQL against an external endpoint listed in the fabric catalog.
        Returns JSON results. Only catalog-listed endpoint URLs are allowed."""
        if endpoint_url not in allowed:
            return (
                f"Error: endpoint {endpoint_url} not in catalog. "
                f"Allowed endpoints: {', '.join(sorted(allowed)) or 'none'}"
            )
        try:
            r = httpx.post(
                endpoint_url,
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"},
                timeout=30.0,
                follow_redirects=True,
            )
            r.raise_for_status()
            txt = r.text
            if len(txt) > max_chars:
                return txt[:max_chars] + f"\n... truncated ({len(txt)} total chars)."
            return txt
        except httpx.HTTPStatusError as e:
            return f"External SPARQL error (HTTP {e.response.status_code}): {e.response.text[:500]}"
        except Exception as e:
            return f"External SPARQL error: {e}"
    return query_external_sparql
