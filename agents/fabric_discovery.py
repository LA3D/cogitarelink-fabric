"""Fabric endpoint discovery — four-layer KR loading (D9)."""
from __future__ import annotations
import logging
import re
from dataclasses import dataclass, field

import httpx
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, RDFS, DCTERMS

log = logging.getLogger(__name__)

_SAFE_IRI = re.compile(r'^https?://[^\s"<>{}]+$')


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
    uri_space: str | None = None
    prefix_declarations: dict[str, str] = field(default_factory=dict)
    named_graphs: list[dict] = field(default_factory=list)
    shapes: list[ShapeSummary] = field(default_factory=list)
    examples: list[ExampleSummary] = field(default_factory=list)
    tbox_graph: Graph | None = field(default=None, repr=False)
    vocab_graph_map: dict[str, str] = field(default_factory=dict)

    @property
    def routing_plan(self) -> str:
        lines = [
            f"Endpoint: {self.base}",
            f"SPARQL: {self.sparql_url}",
            f"Profile: {self.conforms_to}",
        ]

        if self.uri_space:
            lines.append("")
            lines.append(f"Entity URI space: {self.uri_space}")
            lines.append(f"  Pattern: {self.uri_space}{{id}}")
            lines.append(f"  Dereferenceable: GET /entity/{{id}}")

        lines.append("")
        if self.prefix_declarations:
            lines.append("Local ontology cache (no external dereferencing needed):")
            for prefix, ns in sorted(self.prefix_declarations.items()):
                graph_uri = self.vocab_graph_map.get(ns, "")
                if graph_uri:
                    # split("//host/path", 3) → ["https:", "", "host", "path"]
                    parts = graph_uri.split("/", 3)
                    path = "/" + parts[-1] if len(parts) >= 4 else graph_uri
                    lines.append(f"  {prefix}: <{ns}> -> {path}")
                else:
                    lines.append(f"  {prefix}: <{ns}>")
        else:
            lines.append("Vocabularies:")
            for v in self.vocabularies:
                short = v.rstrip("/#").rsplit("/", 1)[-1]
                lines.append(f"  - {short}: <{v}>")

        if self.named_graphs:
            lines.append("")
            lines.append("Named graphs:")
            for ng in self.named_graphs:
                lines.append(f"  {ng['graph_uri']} — {ng['title']}")

        lines.append("")
        lines.append(f"Shapes ({len(self.shapes)}):")
        for s in self.shapes:
            lines.append(f"  {s.name} -> {s.target_class}")
            if s.properties:
                lines.append(f"    Properties: {', '.join(s.properties)}")
            if s.agent_instruction:
                hint_lines = s.agent_instruction.splitlines()
                lines.append(f"    Agent hint: {hint_lines[0]}")
                for hl in hint_lines[1:]:
                    lines.append(f"      {hl}")

        lines.append("")
        lines.append(f"SPARQL Examples ({len(self.examples)}):")
        for e in self.examples:
            lines.append(f'  "{e.label}" -> {e.target}')
            lines.append(f"    {e.comment}")
            for sparql_line in e.sparql.strip().splitlines():
                lines.append(f"    {sparql_line}")

        return "\n".join(lines)


# --- Namespaces -----------------------------------------------------------

VOID = Namespace("http://rdfs.org/ns/void#")
SH = Namespace("http://www.w3.org/ns/shacl#")
SPEX = Namespace("https://purl.expasy.org/sparql-examples/ontology#")
SDO = Namespace("https://schema.org/")

# --- Helpers ---------------------------------------------------------------

# W3C standard prefixes — always available regardless of endpoint
_W3C_PREFIXES: dict[str, str] = {
    "http://www.w3.org/ns/shacl#": "sh:",
    "http://www.w3.org/ns/prov#": "prov:",
    "http://www.w3.org/2006/time#": "time:",
    "http://www.w3.org/ns/dx/prof/": "prof:",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf:",
    "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
    "http://www.w3.org/2002/07/owl#": "owl:",
}


def _build_compact_map(prefix_declarations: dict[str, str] | None = None) -> dict[str, str]:
    """Build namespace->prefix: map from endpoint declarations + W3C fallbacks."""
    ns_to_prefix: dict[str, str] = dict(_W3C_PREFIXES)
    if prefix_declarations:
        for prefix, ns in prefix_declarations.items():
            ns_to_prefix[ns] = f"{prefix}:"
    return ns_to_prefix


def _compact(iri: str, compact_map: dict[str, str] | None = None) -> str:
    mapping = compact_map if compact_map is not None else _W3C_PREFIXES
    for ns, prefix in mapping.items():
        if iri.startswith(ns):
            return prefix + iri[len(ns):]
    return iri


def _fetch(url: str, accept: str = "text/turtle") -> str:
    r = httpx.get(url, headers={"Accept": accept}, timeout=10.0)
    r.raise_for_status()
    return r.text


def _parse_void(ttl: str) -> tuple[str, list[str], str, str | None, list[dict]]:
    g = Graph()
    g.parse(data=ttl, format="turtle")
    sparql_url = ""
    vocabs: list[str] = []
    conforms = ""
    uri_space: str | None = None
    named_graphs: list[dict] = []
    # Root dataset = void:Dataset subject that is not itself a void:subset object;
    # subset blank nodes may also carry dct:conformsTo (their shape), which must
    # not overwrite the top-level profile declaration.
    subset_objects = set(g.objects(predicate=VOID.subset))
    root = next(
        (s for s in g.subjects(RDF.type, VOID.Dataset) if s not in subset_objects),
        None,
    )
    for s in g.subjects(RDF.type, VOID.Dataset):
        for o in g.objects(s, VOID.sparqlEndpoint):
            sparql_url = str(o)
        for o in g.objects(s, VOID.vocabulary):
            vocabs.append(str(o))
        if s == root:
            for o in g.objects(s, DCTERMS.conformsTo):
                conforms = str(o)
        for o in g.objects(s, VOID.uriSpace):
            uri_space = str(o)
        for subset in g.objects(s, VOID.subset):
            title = str(g.value(subset, DCTERMS.title) or "")
            graph_uri = str(g.value(subset, VOID.sparqlGraphEndpoint) or "")
            if graph_uri:
                named_graphs.append({"title": title, "graph_uri": graph_uri})
    return sparql_url, vocabs, conforms, uri_space, named_graphs


def _parse_prefix_declarations(ttl: str) -> dict[str, str]:
    g = Graph()
    g.parse(data=ttl, format="turtle")
    prefixes: dict[str, str] = {}
    for decl in g.objects(predicate=SH.declare):
        prefix = str(g.value(decl, SH.prefix) or "")
        ns = str(g.value(decl, SH.namespace) or "")
        if prefix and ns:
            prefixes[prefix] = ns
    return prefixes


def _parse_shapes(ttl: str, compact_map: dict[str, str] | None = None) -> list[ShapeSummary]:
    g = Graph()
    g.parse(data=ttl, format="turtle")
    shapes = []
    for s in g.subjects(RDF.type, SH.NodeShape):
        name = str(s).rsplit("/", 1)[-1].rsplit("#", 1)[-1]
        tc = ""
        for o in g.objects(s, SH.targetClass):
            tc = _compact(str(o), compact_map)
        instr = None
        for o in g.objects(s, SH.agentInstruction):
            instr = str(o)
        props = []
        for prop_node in g.objects(s, SH.property):
            for path in g.objects(prop_node, SH.path):
                parts = [_compact(str(path), compact_map)]
                cls = g.value(prop_node, SH["class"])
                if cls:
                    parts.append(f"class={_compact(str(cls), compact_map)}")
                nk = g.value(prop_node, SH.nodeKind)
                if nk:
                    parts.append(f"nodeKind={str(nk).rsplit('#', 1)[-1]}")
                pattern = g.value(prop_node, SH.pattern)
                if pattern:
                    parts.append(f"pattern={str(pattern)}")
                props.append(" ".join(parts))
        shapes.append(ShapeSummary(name=name, target_class=tc,
                                   agent_instruction=instr, properties=props))
    return shapes


def _parse_examples(ttl: str) -> list[ExampleSummary]:
    g = Graph()
    g.parse(data=ttl, format="turtle")
    examples = []
    for s in g.subjects(RDF.type, SPEX.SPARQLExecutable):
        label = str(g.value(s, RDFS.label) or "")
        comment = str(g.value(s, RDFS.comment) or "")
        sparql = str(g.value(s, SH.select) or "")
        target = str(g.value(s, SDO.target) or "")
        if sparql:
            examples.append(ExampleSummary(label=label, comment=comment,
                                           sparql=sparql, target=target))
    return examples


# --- TBox loading (L2) ----------------------------------------------------

def _resolve_vocab_graphs(sparql_url: str, vocabs: list[str]) -> dict[str, str]:
    """Find named graphs containing triples whose subjects start with each vocabulary IRI.

    Returns: dict mapping vocabulary namespace -> graph URI.
    """
    mapping: dict[str, str] = {}
    for vocab in vocabs:
        if not _SAFE_IRI.match(vocab):
            log.warning("Skipping unsafe vocabulary IRI: %s", vocab)
            continue
        q = f'SELECT DISTINCT ?g WHERE {{ GRAPH ?g {{ ?s ?p ?o . FILTER(STRSTARTS(STR(?s), "{vocab}")) }} }}'
        r = httpx.post(
            sparql_url, data={"query": q},
            headers={"Accept": "application/sparql-results+json"},
            timeout=10.0,
        )
        r.raise_for_status()
        for binding in r.json().get("results", {}).get("bindings", []):
            uri = binding.get("g", {}).get("value", "")
            if uri and vocab not in mapping:
                mapping[vocab] = uri
    return mapping


def _load_tbox(sparql_url: str, graph_uris: list[str]) -> Graph:
    """CONSTRUCT all triples from discovered TBox named graphs into one rdflib.Graph."""
    g = Graph()
    for uri in graph_uris:
        if not _SAFE_IRI.match(uri):
            log.warning("Skipping unsafe graph IRI: %s", uri)
            continue
        q = f"CONSTRUCT {{ ?s ?p ?o }} WHERE {{ GRAPH <{uri}> {{ ?s ?p ?o }} }}"
        r = httpx.post(
            sparql_url, data={"query": q},
            headers={"Accept": "text/turtle"},
            timeout=30.0,
        )
        r.raise_for_status()
        if r.text.strip():
            g.parse(data=r.text, format="turtle")
    return g


# --- Public API ------------------------------------------------------------

def discover_endpoint(url: str) -> FabricEndpoint:
    """Fetch all four D9 layers from a fabric node's .well-known/ endpoints."""
    base = url.rstrip("/")

    void_ttl = _fetch(f"{base}/.well-known/void")
    sparql_url, vocabs, conforms, uri_space, named_graphs = _parse_void(void_ttl)

    profile_ttl = _fetch(f"{base}/.well-known/profile")
    shapes_ttl = _fetch(f"{base}/.well-known/shacl")
    examples_ttl = _fetch(f"{base}/.well-known/sparql-examples")

    prefix_declarations = _parse_prefix_declarations(shapes_ttl)
    compact_map = _build_compact_map(prefix_declarations)
    shapes = _parse_shapes(shapes_ttl, compact_map)
    examples = _parse_examples(examples_ttl)

    # L2 TBox loading — non-fatal; routing plan text still works without it
    vocab_graph_map: dict[str, str] = {}
    tbox = None
    if sparql_url and vocabs:
        try:
            vocab_graph_map = _resolve_vocab_graphs(sparql_url, vocabs)
            graph_uris = list(dict.fromkeys(vocab_graph_map.values()))  # dedup, preserve order
            if graph_uris:
                tbox = _load_tbox(sparql_url, graph_uris)
        except (httpx.HTTPError, ValueError, SyntaxError) as exc:
            log.debug("TBox loading failed: %s", exc)

    return FabricEndpoint(
        base=base, sparql_url=sparql_url,
        void_ttl=void_ttl, profile_ttl=profile_ttl,
        shapes_ttl=shapes_ttl, examples_ttl=examples_ttl,
        vocabularies=vocabs, conforms_to=conforms,
        uri_space=uri_space,
        prefix_declarations=prefix_declarations,
        named_graphs=named_graphs,
        shapes=shapes, examples=examples,
        tbox_graph=tbox,
        vocab_graph_map=vocab_graph_map,
    )
