"""Fabric agent orchestration — discover + query via dspy.RLM."""
from __future__ import annotations
from dataclasses import dataclass, field
import dspy
from agents.fabric_discovery import FabricEndpoint
from agents.fabric_query import make_fabric_query_tool


@dataclass
class FabricQueryResult:
    answer: str
    sparql: str | None = None
    sources: list[str] = field(default_factory=list)
    iterations: int = 0
    converged: bool = True


class FabricQuery(dspy.Signature):
    """Navigate a fabric endpoint using its self-description to answer a query.
    Use the endpoint's SHACL shapes and SPARQL examples as guides for
    constructing SPARQL queries. Execute queries with sparql_query()."""
    endpoint_sd: str = dspy.InputField(
        desc="Endpoint self-description: vocabularies, SHACL shapes with "
             "agent instructions, and SPARQL example queries")
    query: str = dspy.InputField(desc="Natural language question to answer")
    answer: str = dspy.OutputField(
        desc="Answer with supporting evidence from SPARQL results")
    sparql_used: str = dspy.OutputField(
        desc="The SPARQL query that produced the answer")
    sources: list[str] = dspy.OutputField(
        desc="Named graphs consulted")


def run_fabric_query(
    ep: FabricEndpoint,
    query: str,
    *,
    model: str = "anthropic/claude-sonnet-4-6",
    max_iterations: int = 10,
    max_llm_calls: int = 20,
    verbose: bool = False,
) -> FabricQueryResult:
    """Run an RLM agent against a fabric endpoint.

    Pre-loads the endpoint's self-description (four-layer KR), then
    launches a dspy.RLM REPL with a bound SPARQL query tool.

    Args:
        ep: FabricEndpoint from discover_endpoint()
        query: Natural language question
        model: LLM model identifier
        max_iterations: REPL turn budget
        max_llm_calls: Sub-LLM call budget
        verbose: Print REPL trace

    Returns:
        FabricQueryResult with answer, SPARQL used, and sources
    """
    sparql_query = make_fabric_query_tool(ep)

    dspy.configure(lm=dspy.LM(model))
    rlm = dspy.RLM(
        FabricQuery,
        tools=[sparql_query],
        max_iterations=max_iterations,
        max_llm_calls=max_llm_calls,
        verbose=verbose,
    )

    result = rlm(endpoint_sd=ep.routing_plan, query=query)

    return FabricQueryResult(
        answer=getattr(result, "answer", ""),
        sparql=getattr(result, "sparql_used", None),
        sources=getattr(result, "sources", []),
    )
