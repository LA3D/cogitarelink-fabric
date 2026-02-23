"""RDFS route analysis tool for fabric RLM agents.

Adapts PDDL-Instruct methodology for SPARQL via a sub-agent that reads
ontology structure and produces routing plans with SPARQL triple patterns.

Source: ontology-agent-kr/experiments/rdfs_instruct/rdfs_instruct.py
Copied (not imported) to keep fabric repo self-contained.

Public API:
    make_rdfs_routes_tool(ep) -> Callable[[str], str]
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from agents.fabric_discovery import FabricEndpoint

SCHEMA = Namespace("http://schema.org/")

RDFS_INSTRUCT_PATTERNS = """\
You are an RDFS reasoning specialist. Given an ontology's structural
declarations and an information need, apply the RDFS/OWL reasoning patterns
below to identify routing paths and affordances for SPARQL construction.

For each step, cite the specific RDFS/OWL axiom being applied and show
the SPARQL triple pattern it produces.

=== PATTERN 0: TYPE GROUNDING ===

RDFS RULE: rdf:type declares which class an individual belongs to.
           Ontology axioms (domain/range, allValuesFrom) are defined on
           classes, not individuals. You cannot route from an individual
           without knowing its type.

INSTANCE CONTEXT (provided by the caller):
  inst:station-alpha  rdf:type  :Platform .

ONTOLOGY:
  :hosts  schema:domainIncludes :Platform ;
          schema:rangeIncludes  :Sensor, :Actuator .

REASONING: The question asks what inst:station-alpha hosts. The instance
  context says it is a :Platform. Properties with :Platform in domainIncludes:
  :hosts. Route: inst:station-alpha :hosts ?device .

INCORRECT: Guessing the type from structural fingerprints or question text.
  WHY WRONG: Obfuscated URIs are opaque. Only rdf:type assertions in the
  data are authoritative.

WHEN NO INSTANCE CONTEXT IS PROVIDED:
  Flag in your routing plan that the main agent must first resolve the
  individual's type via sparql_describe(uri), then re-call with context.


=== PATTERN 1: DOMAIN/RANGE ROUTING ===

RDFS RULE: rdfs:domain declares which class a property belongs to.
           rdfs:range declares what class the property points to.

ONTOLOGY (any ontology):
  :propA  rdfs:domain :ClassX ;  rdfs:range :ClassY .
  :propB  rdfs:domain :ClassY ;  rdfs:range :ClassZ .

REASONING: To get from :ClassX to :ClassZ, there is no direct property.
  But :propA goes X->Y and :propB goes Y->Z.
  Route: ?x :propA ?y . ?y :propB ?z .

DIRECTION RULE: At each hop, determine if the starting type is in domain or range:
  - Type in DOMAIN -> FORWARD: starting node is subject.
      SPARQL: ?startingNode :prop ?target .
  - Type in RANGE -> BACKWARD: starting node is object.
      SPARQL: ?target :prop ?startingNode .

SPARQL MATERIALIZATION:
  SELECT ?z WHERE { ?x :propA ?y . ?y :propB ?z . }


=== PATTERN 2: HIERARCHY EXPANSION ===

RDFS RULE: rdfs:subClassOf creates a type hierarchy.
           Querying the parent misses instances typed only as the subclass.

ONTOLOGY:
  :SubA  rdfs:subClassOf :Parent .
  :propX rdfs:domain :SubA ; rdfs:range :Target .

REASONING: Must query :SubA specifically, not :Parent.

SPARQL MATERIALIZATION:
  Option A: ?x a :SubA . ?x :propX ?target .
  Option B: ?sub rdfs:subClassOf :Parent . ?x a ?sub . ?x :propX ?target .


=== PATTERN 3: INVERSE PROPERTY NAVIGATION ===

RDFS+ RULE: owl:inverseOf means two properties express the same
            relationship from opposite directions.

BEST PRACTICE: Specify BOTH forward and backward forms:
    FORWARD: inst:sensor :madeObservation ?obs .
    BACKWARD: ?obs :madeBySensor inst:sensor .
  Endpoints without inference may only materialize ONE direction.


=== PATTERN 4: EXISTENTIAL GUARANTEE (OWL RESTRICTION) ===

OWL RULE: owl:someValuesFrom means every instance has at least one value.

DIAGNOSTIC: Zero results on a guaranteed path = query error, not data absence.


=== PATTERN 5: DISJOINTNESS PRUNING ===

OWL RULE: owl:disjointWith means no instance belongs to both classes.
  Prunes the search space.


=== PATTERN 6: UNIVERSAL TYPE RESTRICTION (OWL allValuesFrom) ===

OWL RULE: owl:allValuesFrom = type safety, not existence guarantee.
  Zero results does NOT mean query error.


=== YOUR TASK ===

Given the ONTOLOGY STRUCTURE and INFORMATION NEED below, apply these
patterns to produce a ROUTING ANALYSIS:

1. Identify source entity type and target information type.
2. Trace routing path using domain/range (Pattern 1). Show DIRECTION per hop.
3. Flag hierarchy expansions (Pattern 2).
4. For inverse pairs (Pattern 3), provide BOTH SPARQL forms.
5. Flag existential guarantees (Pattern 4).
6. Flag disjointness pruning (Pattern 5).
7. Flag universal type restrictions (Pattern 6).

For EACH routing hop, cite the axiom:
  "madeBySensor: domain=Observation, range=Sensor (BACKWARD from Sensor)"

End with a ROUTING PLAN listing SPARQL triple patterns in order.
"""


def _short_name(uri) -> str:
    s = str(uri)
    if "#" in s:
        return s.split("#")[-1]
    return s.rsplit("/", 1)[-1]


def extract_ontology_structure(g: Graph) -> str:
    """Convert rdflib.Graph to routing-relevant text for RDFS sub-agent."""
    sections = []

    routes = []
    for p in sorted(g.subjects(RDF.type, OWL.ObjectProperty)):
        if not isinstance(p, URIRef):
            continue
        dom = g.value(p, RDFS.domain)
        rng = g.value(p, RDFS.range)
        if dom and rng and isinstance(dom, URIRef) and isinstance(rng, URIRef):
            routes.append(f"  {_short_name(p)}: {_short_name(dom)} -> {_short_name(rng)}")
    sections.append(f"ROUTING PATHS (object properties with domain -> range) [{len(routes)}]:")
    sections.extend(routes)

    dt_props = []
    for p in sorted(g.subjects(RDF.type, OWL.DatatypeProperty)):
        if not isinstance(p, URIRef):
            continue
        dom = g.value(p, RDFS.domain)
        rng = g.value(p, RDFS.range)
        if dom and isinstance(dom, URIRef):
            dt_props.append(
                f"  {_short_name(p)}: {_short_name(dom)} -> {_short_name(rng) if rng else 'literal'}"
            )
    sections.append(f"\nDATATYPE PROPERTIES (domain -> literal type) [{len(dt_props)}]:")
    sections.extend(dt_props)

    hierarchy: dict[str, list[str]] = defaultdict(list)
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            hierarchy[_short_name(o)].append(_short_name(s))
    sections.append("\nSUBCLASS HIERARCHIES (parent: [children]):")
    for parent in sorted(hierarchy, key=lambda p: len(hierarchy[p]), reverse=True):
        children = sorted(hierarchy[parent])
        if len(children) >= 2:
            sections.append(f"  {parent} ({len(children)}): {', '.join(children)}")

    inverses = [
        (s, o) for s, _, o in g.triples((None, OWL.inverseOf, None))
        if isinstance(s, URIRef) and isinstance(o, URIRef)
    ]
    if inverses:
        sections.append("\nINVERSE PROPERTIES (owl:inverseOf):")
        for s, o in inverses:
            sections.append(f"  {_short_name(s)} <-> {_short_name(o)}")

    seen: set[tuple] = set()
    restrictions = []
    for cls in g.subjects(RDFS.subClassOf, None):
        if not isinstance(cls, URIRef):
            continue
        for restr in g.objects(cls, RDFS.subClassOf):
            if not isinstance(restr, BNode):
                continue
            on_prop = g.value(restr, OWL.onProperty)
            some_val = g.value(restr, OWL.someValuesFrom)
            if on_prop and some_val:
                key = (_short_name(cls), _short_name(on_prop), _short_name(some_val))
                if key not in seen:
                    seen.add(key)
                    restrictions.append(
                        f"  {key[0]}: every instance has {key[1]} -> {key[2]}"
                    )
    if restrictions:
        sections.append("\nEXISTENTIAL GUARANTEES (owl:someValuesFrom restrictions):")
        sections.extend(restrictions)

    return "\n".join(sections)


def build_rdfs_sub_agent_prompt(
    ontology_summary: str,
    information_need: str,
    instance_context: str | None = None,
) -> str:
    """Assemble RDFS reasoning sub-agent prompt."""
    parts = [f"{RDFS_INSTRUCT_PATTERNS}\n", f"ONTOLOGY STRUCTURE:\n{ontology_summary}\n\n"]
    if instance_context:
        parts.append(f"INSTANCE CONTEXT (grounded types from data):\n{instance_context}\n\n")
    parts.append(
        f"INFORMATION NEED: {information_need}\n\n"
        "Apply the RDFS reasoning patterns above. For each routing hop,\n"
        "cite the specific axiom (property name, domain, range). End with\n"
        "a ROUTING PLAN listing the SPARQL triple patterns in order.\n"
    )
    return "".join(parts)


def make_rdfs_routes_tool(ep: FabricEndpoint) -> Callable[[str], str]:
    """Return analyze_rdfs_routes(information_need) bound to ep's tbox_graph.

    If ep.tbox_graph is None, returns a stub explaining TBox is absent.
    Otherwise pre-computes ontology summary at factory time and calls
    dspy.settings.lm at each invocation to run the RDFS sub-agent.
    """
    if ep.tbox_graph is None:
        def analyze_rdfs_routes(information_need: str) -> str:
            """Analyze RDFS routing paths. No TBox graph available."""
            return (
                "TBox not available: no ontology graph loaded for this endpoint. "
                "Use sparql_query() with GRAPH ?g { ?s ?p ?o } to discover properties."
            )
        return analyze_rdfs_routes

    ont_summary = extract_ontology_structure(ep.tbox_graph)

    def analyze_rdfs_routes(information_need: str) -> str:
        """Analyze RDFS/OWL routing paths to guide SPARQL construction.

        Applies 7 RDFS/OWL reasoning patterns to the loaded ontology and
        returns a ROUTING PLAN with SPARQL triple patterns for the given
        information need.
        """
        import dspy
        lm = dspy.settings.lm
        if lm is None:
            return "No LLM configured for RDFS route analysis."
        prompt = build_rdfs_sub_agent_prompt(ont_summary, information_need)
        try:
            responses = lm(messages=[{"role": "user", "content": prompt}])
            if isinstance(responses, list) and responses:
                return str(responses[0])
            return str(responses)
        except Exception as e:
            return f"RDFS analysis error: {e}"

    return analyze_rdfs_routes
