"""Fabric endpoint discovery — four-layer KR loading (D9)."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ShapeSummary:
    name: str
    target_class: str
    agent_instruction: str | None
    properties: list[str] = field(default_factory=list)


@dataclass
class ExampleSummary:
    label: str
    comment: str
    sparql: str
    target: str


@dataclass
class FabricEndpoint:
    base: str
    sparql_url: str
    void_ttl: str
    profile_ttl: str
    shapes_ttl: str
    examples_ttl: str
    vocabularies: list[str] = field(default_factory=list)
    conforms_to: str = ""
    shapes: list[ShapeSummary] = field(default_factory=list)
    examples: list[ExampleSummary] = field(default_factory=list)

    @property
    def routing_plan(self) -> str:
        lines = [
            f"Endpoint: {self.base}",
            f"SPARQL: {self.sparql_url}",
            f"Profile: {self.conforms_to}",
            "",
            "Vocabularies:",
        ]
        for v in self.vocabularies:
            short = v.rstrip("/#").rsplit("/", 1)[-1]
            lines.append(f"  - {short}: <{v}>")

        lines.append("")
        lines.append(f"Shapes ({len(self.shapes)}):")
        for s in self.shapes:
            lines.append(f"  {s.name} -> {s.target_class}")
            if s.properties:
                lines.append(f"    Properties: {', '.join(s.properties)}")
            if s.agent_instruction:
                lines.append(f"    Agent hint: {s.agent_instruction}")

        lines.append("")
        lines.append(f"SPARQL Examples ({len(self.examples)}):")
        for e in self.examples:
            lines.append(f'  "{e.label}" -> {e.target}')
            lines.append(f"    {e.comment}")
            for sparql_line in e.sparql.strip().splitlines():
                lines.append(f"    {sparql_line}")

        return "\n".join(lines)
