"""Registry + agent helpers — pure Python, no FastAPI dependency (D12, D13, D14).

Same pattern as did_resolver.py and integrity.py:
imported by main.py (Docker) and unit tests (local).
"""
from datetime import datetime, timezone

from rdflib import Graph, Namespace
from rdflib.namespace import DCTERMS

try:
    from fabric.node.did_resolver import sparql_escape
except ModuleNotFoundError:
    from did_resolver import sparql_escape

FABRIC_NS = "https://w3id.org/cogitarelink/fabric#"

VALID_AGENT_ROLES = frozenset({
    "IngestCuratorRole",
    "LinkingCuratorRole",
    "QARole",
    "MaintenanceRole",
    "SecurityMonitorRole",
    "IntegrityAuditorRole",
    "DevelopmentAgentRole",
})


def build_registry_insert(
    node_base: str, node_did: str, registered_by: str | None = None,
) -> str:
    """SPARQL INSERT DATA for a node entry in /graph/registry."""
    now = datetime.now(timezone.utc).isoformat()
    reg_by = registered_by or node_did
    safe_did = sparql_escape(node_did)
    safe_reg = sparql_escape(reg_by)
    return f"""\
PREFIX fabric: <{FABRIC_NS}>
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {{
  GRAPH <{node_base}/graph/registry> {{
    <{node_did}> a fabric:FabricNode ;
        fabric:nodeDID "{safe_did}" ;
        fabric:conformanceCredential <{node_base}/.well-known/conformance-vc.json> ;
        fabric:voidEndpoint <{node_base}/.well-known/void> ;
        fabric:sparqlEndpoint <{node_base}/sparql> ;
        fabric:ldnInbox <{node_base}/inbox> ;
        fabric:resolverEndpoint <{node_base}/1.0/identifiers/> ;
        dct:conformsTo <{FABRIC_NS}CoreProfile> ;
        fabric:registeredAt "{now}"^^xsd:dateTime ;
        fabric:registeredBy <{safe_reg}> .
  }}
}}"""


def build_registry_construct(node_base: str) -> str:
    """SPARQL CONSTRUCT returning all entries in /graph/registry."""
    return f"""\
PREFIX fabric: <{FABRIC_NS}>
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
CONSTRUCT {{ ?node ?p ?o }}
WHERE {{
  GRAPH <{node_base}/graph/registry> {{
    ?node a fabric:FabricNode ; ?p ?o .
  }}
}}"""


def build_registry_entry_construct(node_base: str, node_did: str) -> str:
    """SPARQL CONSTRUCT for a single node by DID."""
    safe_did = sparql_escape(node_did)
    return f"""\
PREFIX fabric: <{FABRIC_NS}>
PREFIX dct:    <http://purl.org/dc/terms/>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
CONSTRUCT {{ <{safe_did}> ?p ?o }}
WHERE {{
  GRAPH <{node_base}/graph/registry> {{
    <{safe_did}> a fabric:FabricNode ; ?p ?o .
  }}
}}"""


def check_void_conformance(void_turtle: str) -> bool:
    """Check if VoID declares dct:conformsTo fabric:CoreProfile via rdflib parsing."""
    if not void_turtle or not void_turtle.strip():
        return False
    FABRIC = Namespace(FABRIC_NS)
    try:
        g = Graph()
        g.parse(data=void_turtle, format="turtle")
        return (None, DCTERMS.conformsTo, FABRIC.CoreProfile) in g
    except Exception:
        return False


def build_agent_insert(
    node_base: str, agent_did: str, agent_role: str,
    authorized_graphs: list[str], authorized_operations: list[str],
) -> str:
    """SPARQL INSERT DATA for an agent in /graph/agents."""
    if agent_role not in VALID_AGENT_ROLES:
        raise ValueError(f"Invalid agent role: {agent_role}. Must be one of {sorted(VALID_AGENT_ROLES)}")
    now = datetime.now(timezone.utc).isoformat()
    safe_did = sparql_escape(agent_did)
    graphs_ttl = " , ".join(f'"{sparql_escape(g)}"' for g in authorized_graphs)
    ops_ttl = " , ".join(f'"{sparql_escape(o)}"' for o in authorized_operations)
    return f"""\
PREFIX fabric: <{FABRIC_NS}>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {{
  GRAPH <{node_base}/graph/agents> {{
    <{agent_did}> a fabric:RegisteredAgent ;
        fabric:agentDID "{safe_did}" ;
        fabric:agentRole fabric:{agent_role} ;
        fabric:authorizedGraph {graphs_ttl} ;
        fabric:authorizedOperation {ops_ttl} ;
        fabric:homeNode <{node_base}> ;
        fabric:registeredAt "{now}"^^xsd:dateTime .
  }}
}}"""


def build_agents_list_construct(node_base: str) -> str:
    """SPARQL CONSTRUCT returning all agents in /graph/agents."""
    return f"""\
PREFIX fabric: <{FABRIC_NS}>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
CONSTRUCT {{ ?agent ?p ?o }}
WHERE {{
  GRAPH <{node_base}/graph/agents> {{
    ?agent a fabric:RegisteredAgent ; ?p ?o .
  }}
}}"""


def build_agent_construct(node_base: str, agent_did: str) -> str:
    """SPARQL CONSTRUCT for a single agent by DID."""
    safe_did = sparql_escape(agent_did)
    return f"""\
PREFIX fabric: <{FABRIC_NS}>
PREFIX xsd:    <http://www.w3.org/2001/XMLSchema#>
CONSTRUCT {{ <{safe_did}> ?p ?o }}
WHERE {{
  GRAPH <{node_base}/graph/agents> {{
    <{safe_did}> a fabric:RegisteredAgent ; ?p ?o .
  }}
}}"""
