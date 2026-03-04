"""Fabric write tools — discover, write, validate, commit (D10, D24)."""
from __future__ import annotations
import re
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from rdflib import Graph
from rdflib.exceptions import ParserError

from agents.fabric_discovery import FabricEndpoint, _ssl_verify
from agents.fabric_validate import validate_result

_SAFE_IRI = re.compile(r'^https?://[^\s"<>{}]+$')


def _uuid7_stub() -> str:
    """UUIDv4 stand-in — matches existing uuid7() pattern in codebase."""
    return str(uuid4())


def _update_url(sparql_url: str) -> str:
    """Derive SPARQL Update endpoint from query endpoint."""
    url = sparql_url.rstrip("/")
    if not url.endswith("/update"):
        url = url + "/update"
    return url


# ---------------------------------------------------------------------------
# discover_write_targets
# ---------------------------------------------------------------------------

def make_discover_write_targets_tool(ep: FabricEndpoint) -> Callable:
    def discover_write_targets() -> str:
        """List named graphs that accept writes, with governing shapes."""
        writable = [ng for ng in ep.named_graphs if ng.get("writable")]
        if not writable:
            return "No writable graphs found at this endpoint."
        lines = ["Writable graphs:"]
        for ng in writable:
            lines.append(f"  {ng['graph_uri']} — {ng.get('title', '')}")
            if "conformsTo" in ng:
                lines.append(f"    Shape: {ng['conformsTo']}")
        return "\n".join(lines)
    return discover_write_targets


# ---------------------------------------------------------------------------
# write_triples
# ---------------------------------------------------------------------------

def make_write_triples_tool(ep: FabricEndpoint) -> Callable:
    def write_triples(graph: str, turtle: str) -> str:
        """Write Turtle triples to a named graph. No validation at write time.
        Returns confirmation or error message."""
        try:
            if not _SAFE_IRI.match(graph):
                return f"Invalid graph URI: {graph}"
            g = Graph()
            g.parse(data=turtle, format="turtle")
            ntriples = g.serialize(format="nt")

            # Build SPARQL UPDATE with INSERT DATA
            update = f"INSERT DATA {{ GRAPH <{graph}> {{ {ntriples} }} }}"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if ep.vp_token:
                headers["Authorization"] = f"Bearer {ep.vp_token}"

            r = httpx.post(
                _update_url(ep.sparql_url),
                data={"update": update},
                headers=headers,
                timeout=30.0,
                verify=_ssl_verify(),
            )
            if r.status_code == 401:
                return "Authentication required: VP Bearer token missing or expired."
            if r.status_code == 403:
                return f"Access denied: insufficient permissions. {r.text[:300]}"
            r.raise_for_status()
            return f"OK: {len(g)} triples written to <{graph}>."
        except ParserError as e:
            return f"Turtle syntax error: {e}"
        except Exception as e:
            return f"Write error: {e}"
    return write_triples


# ---------------------------------------------------------------------------
# validate_graph
# ---------------------------------------------------------------------------

def make_validate_graph_tool(ep: FabricEndpoint) -> Callable:
    def validate_graph(graph: str) -> str:
        """Validate a named graph's contents against this endpoint's SHACL shapes.
        Returns conformance result with fix instructions if non-conformant."""
        try:
            if not _SAFE_IRI.match(graph):
                return f"Invalid graph URI: {graph}"
            q = f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}"
            headers = {"Accept": "text/turtle"}
            if ep.vp_token:
                headers["Authorization"] = f"Bearer {ep.vp_token}"

            r = httpx.post(
                ep.sparql_url,
                data={"query": q},
                headers=headers,
                timeout=30.0,
                verify=_ssl_verify(),
            )
            if r.status_code == 401:
                return "Authentication required: VP Bearer token missing or expired."
            r.raise_for_status()

            data_ttl = r.text
            if not data_ttl.strip():
                return f"Graph <{graph}> is empty — nothing to validate."

            result = validate_result(
                data_ttl, ep.shapes_ttl,
                tbox_graph=getattr(ep, "tbox_graph", None),
            )
            if result.conforms:
                return f"CONFORMS: Graph <{graph}> passes all SHACL constraints."

            lines = [f"NON-CONFORMANT: {len(result.violations)} violation(s) in <{graph}>:"]
            for v in result.violations:
                lines.append(f"  - {v.message}")
                if v.path:
                    lines.append(f"    Path: {v.path}")
                if v.agent_hint:
                    lines.append(f"    Fix: {v.agent_hint}")
            return "\n".join(lines)
        except httpx.HTTPStatusError as e:
            return f"SPARQL error (HTTP {e.response.status_code}): {e.response.text[:500]}"
        except Exception as e:
            return f"Validation error: {e}"
    return validate_graph


# ---------------------------------------------------------------------------
# commit_graph
# ---------------------------------------------------------------------------

def make_commit_graph_tool(ep: FabricEndpoint) -> Callable:
    def commit_graph(graph: str) -> str:
        """Validate graph and record PROV-O provenance on success.
        Returns validation report on failure, provenance confirmation on success."""
        try:
            if not _SAFE_IRI.match(graph):
                return f"Invalid graph URI: {graph}"
            q = f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{graph}> {{ ?s ?p ?o }} }}"
            headers = {"Accept": "text/turtle"}
            if ep.vp_token:
                headers["Authorization"] = f"Bearer {ep.vp_token}"

            r = httpx.post(
                ep.sparql_url,
                data={"query": q},
                headers=headers,
                timeout=30.0,
                verify=_ssl_verify(),
            )
            if r.status_code == 401:
                return "Authentication required: VP Bearer token missing or expired."
            r.raise_for_status()

            data_ttl = r.text
            if not data_ttl.strip():
                return f"Graph <{graph}> is empty — nothing to commit."

            # Step 2: Validate
            result = validate_result(
                data_ttl, ep.shapes_ttl,
                tbox_graph=getattr(ep, "tbox_graph", None),
            )

            if not result.conforms:
                lines = [f"COMMIT REJECTED: {len(result.violations)} violation(s) in <{graph}>:"]
                for v in result.violations:
                    lines.append(f"  - {v.message}")
                    if v.path:
                        lines.append(f"    Path: {v.path}")
                    if v.agent_hint:
                        lines.append(f"    Fix: {v.agent_hint}")
                lines.append("\nFix violations and try again.")
                return "\n".join(lines)

            # Step 3: Write PROV-O provenance to /graph/audit
            activity_id = _uuid7_stub()
            agent_did = getattr(ep, "agent_did", None) or "urn:unknown-agent"
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Find governing shape for this graph
            shape_uri = ""
            for ng in ep.named_graphs:
                if ng.get("graph_uri") == graph:
                    shape_uri = ng.get("conformsTo", "")
                    break

            prov_update = (
                "PREFIX prov: <http://www.w3.org/ns/prov#>\n"
                "PREFIX dct: <http://purl.org/dc/terms/>\n"
                "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n"
                f"INSERT DATA {{ GRAPH <{ep.base}/graph/audit> {{\n"
                f"  <{ep.base}/activity/{activity_id}> a prov:Activity ;\n"
                f'    prov:wasAssociatedWith <{agent_did}> ;\n'
            )
            if shape_uri:
                prov_update += f'    prov:used <{shape_uri}> ;\n'
            prov_update += (
                f'    prov:generated <{graph}> ;\n'
                f'    prov:endedAtTime "{now}"^^xsd:dateTime .\n'
                f"}} }}"
            )

            update_headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if ep.vp_token:
                update_headers["Authorization"] = f"Bearer {ep.vp_token}"

            r2 = httpx.post(
                _update_url(ep.sparql_url),
                data={"update": prov_update},
                headers=update_headers,
                timeout=30.0,
                verify=_ssl_verify(),
            )
            r2.raise_for_status()

            return (
                f"COMMITTED: Graph <{graph}> validated and provenance recorded.\n"
                f"  Activity: {ep.base}/activity/{activity_id}\n"
                f"  Agent: {agent_did}\n"
                f"  Time: {now}"
            )
        except httpx.HTTPStatusError as e:
            return f"Commit error (HTTP {e.response.status_code}): {e.response.text[:500]}"
        except Exception as e:
            return f"Commit error: {e}"
    return commit_graph
