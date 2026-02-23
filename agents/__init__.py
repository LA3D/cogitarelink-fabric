"""cogitarelink-fabric agent tools — RLM integration with fabric endpoints."""
from agents.fabric_discovery import discover_endpoint, FabricEndpoint, ShapeSummary, ExampleSummary
from agents.fabric_query import make_fabric_query_tool
from agents.fabric_validate import validate_result, ValidationResult, make_validate_tool
from agents.fabric_rdfs_routes import make_rdfs_routes_tool


def __getattr__(name):
    """Lazy import for dspy-dependent symbols."""
    if name in ("run_fabric_query", "FabricQueryResult"):
        from agents.fabric_agent import run_fabric_query, FabricQueryResult
        globals()["run_fabric_query"] = run_fabric_query
        globals()["FabricQueryResult"] = FabricQueryResult
        return globals()[name]
    raise AttributeError(f"module 'agents' has no attribute {name}")
