"""SHACL validation tool for fabric endpoints."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field

from pyshacl import validate as pyshacl_validate
from rdflib import Graph, Namespace
from rdflib.namespace import RDF

from agents.fabric_discovery import FabricEndpoint


SH = Namespace("http://www.w3.org/ns/shacl#")


@dataclass
class Violation:
    message: str
    source_shape: str
    focus_node: str
    path: str | None = None
    agent_hint: str | None = None


@dataclass
class ValidationResult:
    conforms: bool
    violations: list[Violation] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    report_text: str = ""


def _extract_violations(report_g: Graph, shapes_g: Graph) -> list[Violation]:
    """Extract violations with sh:agentInstruction hints from SHACL report."""
    violations = []
    for result in report_g.subjects(RDF.type, SH.ValidationResult):
        msg = str(report_g.value(result, SH.resultMessage) or "")
        source = report_g.value(result, SH.sourceShape)
        focus = str(report_g.value(result, SH.focusNode) or "")
        path_node = report_g.value(result, SH.resultPath)
        path = str(path_node) if path_node else None

        # Look for sh:agentInstruction on the source shape.
        # If source is a property BNode, walk up to the parent NodeShape.
        hint = None
        if source is not None:
            hint_val = shapes_g.value(source, SH.agentInstruction)
            if hint_val is None:
                # source might be a property blank node — find its parent NodeShape
                for parent in shapes_g.subjects(SH.property, source):
                    hint_val = shapes_g.value(parent, SH.agentInstruction)
                    if hint_val:
                        break
            if hint_val:
                hint = str(hint_val)

        violations.append(Violation(
            message=msg,
            source_shape=str(source) if source else "",
            focus_node=focus,
            path=path,
            agent_hint=hint,
        ))
    return violations


def validate_result(
    data_ttl: str,
    shapes_ttl: str,
    *,
    tbox_graph: Graph | None = None,
) -> ValidationResult:
    """Validate RDF data against SHACL shapes, extracting agent hints.

    Args:
        data_ttl: Turtle-serialized data to validate
        shapes_ttl: Turtle-serialized SHACL shapes
        tbox_graph: Optional TBox graph for RDFS/OWL inference

    Returns:
        ValidationResult with conformance, violations, and agent hints
    """
    data_g = Graph()
    data_g.parse(data=data_ttl, format="turtle")

    shapes_g = Graph()
    shapes_g.parse(data=shapes_ttl, format="turtle")

    # Merge TBox for inference if available
    ont_g = None
    if tbox_graph is not None and len(tbox_graph) > 0:
        ont_g = tbox_graph

    conforms, report_g, report_text = pyshacl_validate(
        data_graph=data_g,
        shacl_graph=shapes_g,
        ont_graph=ont_g,
        inference="rdfs",
        advanced=True,
    )

    violations = [] if conforms else _extract_violations(report_g, shapes_g)
    hints = [v.agent_hint for v in violations if v.agent_hint]
    # Deduplicate hints preserving order
    seen: set[str] = set()
    unique_hints = []
    for h in hints:
        if h not in seen:
            seen.add(h)
            unique_hints.append(h)

    return ValidationResult(
        conforms=conforms,
        violations=violations,
        hints=unique_hints,
        report_text=report_text,
    )


def make_validate_tool(ep: FabricEndpoint) -> Callable[[str], str]:
    """Create a validation callable bound to an endpoint's shapes for RLM REPL use.

    Args:
        ep: FabricEndpoint with shapes_ttl and optional tbox_graph

    Returns:
        Callable that takes Turtle string, returns validation summary string
    """
    def validate_triples(turtle: str) -> str:
        """Validate Turtle-serialized RDF data against this endpoint's SHACL shapes."""
        result = validate_result(
            turtle, ep.shapes_ttl,
            tbox_graph=getattr(ep, "tbox_graph", None),
        )
        if result.conforms:
            return "CONFORMS: Data passes all SHACL shape constraints."
        lines = [f"VIOLATIONS ({len(result.violations)}):"]
        for v in result.violations:
            lines.append(f"  - {v.message}")
            if v.path:
                lines.append(f"    Path: {v.path}")
            if v.agent_hint:
                lines.append(f"    Hint: {v.agent_hint}")
        return "\n".join(lines)

    return validate_triples
