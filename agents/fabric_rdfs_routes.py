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


# ============================================================================
# The Seven General RDFS Instruct Patterns (Pattern 0-6)
#
# ALL examples use abstract vocabulary (:ClassX, :propA, etc.) to avoid
# leaking domain knowledge into the sub-agent prompt.  The patterns teach
# RDFS/OWL reasoning principles; the actual ontology structure is supplied
# separately via extract_ontology_structure().
# ============================================================================

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
  inst:alpha  rdf:type  :ClassA .

ONTOLOGY:
  :propA  schema:domainIncludes :ClassA ;
          schema:rangeIncludes  :ClassB, :ClassC .

REASONING: The question asks what inst:alpha relates to via :propA. The
  instance context says it is a :ClassA. Properties with :ClassA in
  domainIncludes: :propA. Route: inst:alpha :propA ?target .

INCORRECT: Guessing the type from structural fingerprints or question text.
  WHY WRONG: Obfuscated URIs are opaque. Only rdf:type assertions in the
  data are authoritative.

WHEN NO INSTANCE CONTEXT IS PROVIDED:
  Flag in your routing plan that the main agent must first resolve the
  individual's type via sparql_describe(uri), then re-call with context.


=== PATTERN 1: DOMAIN/RANGE ROUTING ===

RDFS RULE: rdfs:domain declares which class a property belongs to.
           rdfs:range declares what class the property points to.
           (Also applies to schema:domainIncludes/rangeIncludes.)

ONTOLOGY (any ontology):
  :propA  rdfs:domain :ClassX ;  rdfs:range :ClassY .
  :propB  rdfs:domain :ClassY ;  rdfs:range :ClassZ .

REASONING: To get from :ClassX to :ClassZ, there is no direct property.
  But :propA goes X->Y and :propB goes Y->Z.
  Route: ?x :propA ?y . ?y :propB ?z .

INCORRECT: ?x :propB ?z
  WHY WRONG: :propB has rdfs:domain :ClassY, not :ClassX.
  You need the intermediate hop through :ClassY.

DIRECTION RULE: At each hop, determine if the starting node's type
  appears in the property's domain or range:
  - Type in DOMAIN -> FORWARD: starting node is subject.
      SPARQL: ?startingNode :prop ?target .
  - Type in RANGE -> BACKWARD: starting node is object.
      SPARQL: ?target :prop ?startingNode .

DIRECTION EXAMPLE:
  :propC  domain :ClassM ;  range :ClassN .

  Starting from a :ClassN instance (inst:beta):
    :ClassN is in RANGE -> BACKWARD traversal.
    SPARQL: ?m :propC inst:beta .

  Starting from a :ClassM instance:
    :ClassM is in DOMAIN -> FORWARD traversal.
    SPARQL: ?m :propC ?n .

INCORRECT: inst:beta :propC ?m .
  WHY WRONG: :ClassN is the range, not the domain. The :ClassN instance
  goes in object position when using :propC.

SPARQL MATERIALIZATION:
  SELECT ?z WHERE { ?x :propA ?y . ?y :propB ?z . }


=== PATTERN 2: HIERARCHY EXPANSION ===

RDFS RULE: rdfs:subClassOf creates a type hierarchy.
           Instances of a subclass are also instances of the parent.
           Querying the parent misses instances typed only as the subclass.

ONTOLOGY:
  :SubA  rdfs:subClassOf :Parent .
  :SubB  rdfs:subClassOf :Parent .
  :propX rdfs:domain :SubA ; rdfs:range :Target .

REASONING: If I need :Target from a :Parent instance, I must know which
  subclass has the property. :propX is on :SubA only. Querying :Parent
  for :propX will fail -- the domain is :SubA.
  I must either: (a) query for :SubA specifically, or
                 (b) use rdfs:subClassOf* to find which subclasses exist,
                     then check which one has :propX.

INCORRECT: ?x a :Parent . ?x :propX ?target
  WHY WRONG: :propX has rdfs:domain :SubA. If ?x is typed as :Parent
  but the actual data types it as :SubB, this returns nothing.

SPARQL MATERIALIZATION (two options):
  Option A (specific): ?x a :SubA . ?x :propX ?target .
  Option B (discovery): ?sub rdfs:subClassOf :Parent .
                        ?x a ?sub . ?x :propX ?target .


=== PATTERN 3: INVERSE PROPERTY NAVIGATION ===

RDFS+ RULE: owl:inverseOf means two properties express the same
            relationship from opposite directions.

ONTOLOGY:
  :propD  owl:inverseOf :propE .
  :propD  domain :ClassP ;  range :ClassQ .
  :propE  domain :ClassQ ;  range :ClassP .

MATERIALIZATION RULE: Endpoints without inference may only materialize
  ONE direction of an inverse pair. Do not assume both exist as triples.
  Prefer the property where your starting type is in the DOMAIN
  (forward traversal), as forward triples are more commonly asserted.

REASONING: Starting from a :ClassP instance, I need :ClassQ.
  Option A: inst:p1 :propD ?q  (forward on :propD)
  Option B: ?q :propE inst:p1  (forward on :propE)
  Both are semantically correct. But if the data only asserts
  :propE triples, Option A returns nothing. Option B works.

BEST PRACTICE: In the routing plan, specify BOTH the forward and
  backward forms so the main agent can try the materialized one:
    FORWARD: inst:p1 :propD ?q .
    BACKWARD: ?q :propE inst:p1 .
  If the forward form returns 0 results, the backward form uses the
  inverse property and is equivalent.


=== PATTERN 4: EXISTENTIAL GUARANTEE (OWL RESTRICTION) ===

OWL RULE: owl:someValuesFrom on a property means every instance
          of the restricted class has at least one value for that property.

ONTOLOGY:
  :ClassX rdfs:subClassOf [ owl:onProperty :propA ;
                             owl:someValuesFrom :ClassY ] .

REASONING: Every :ClassX instance is GUARANTEED to have a :propA link
  to some :ClassY. If my query returns zero results for this path,
  my query is wrong -- the data must be there.

DIAGNOSTIC: Zero results on a guaranteed path = query error, not data absence.


=== PATTERN 5: DISJOINTNESS PRUNING ===

OWL RULE: owl:disjointWith means no instance can belong to both classes.

ONTOLOGY:
  :SubA  owl:disjointWith :SubB .
  :SubA  rdfs:subClassOf :Parent .
  :SubB  rdfs:subClassOf :Parent .

REASONING: If I'm looking for data via :SubA, I can ignore :SubB entirely.
  No entity is both :SubA and :SubB. This prunes the search space.

NEGATIVE AFFORDANCE: Don't look for :SubA-specific properties on :SubB instances.


=== PATTERN 6: UNIVERSAL TYPE RESTRICTION (OWL allValuesFrom) ===

OWL RULE: owl:allValuesFrom means every value of that property MUST be
          of the specified class. Type safety, not existence guarantee.

REASONING: Can assume type of traversal result without explicit check.
CONTRAST: someValuesFrom = "path exists"; allValuesFrom = "values are typed".
          Zero results on allValuesFrom does NOT mean query error.


=== YOUR TASK ===

Given the ONTOLOGY STRUCTURE and INFORMATION NEED below, apply these
patterns to produce a ROUTING ANALYSIS:

1. Identify the source entity type and target information type.
   If INSTANCE CONTEXT is provided, use the grounded rdf:type (Pattern 0).
   If not provided for a named individual, flag that types must be resolved first.
2. Trace the routing path from source to target using domain/range
   declarations (Pattern 1). Show each hop with its DIRECTION:
   - FORWARD if starting type is in domain (starting node = subject).
   - BACKWARD if starting type is in range (starting node = object).
3. Flag any hierarchy expansions needed (Pattern 2) -- where a property
   is on a subclass, not the parent.
4. For inverse property pairs (Pattern 3), provide BOTH forward and
   backward SPARQL forms. Flag that only one direction may be
   materialized in the data.
5. Flag any existential guarantees (Pattern 4) -- paths guaranteed to
   have results.
6. Flag any disjointness pruning opportunities (Pattern 5).
7. Flag any universal type restrictions (Pattern 6) -- values guaranteed
   to be of a specific type.

For EACH routing hop, cite the specific axiom and direction:
  "propC: domain=ClassM, range=ClassN (BACKWARD from ClassN)"

End with a ROUTING PLAN: the sequence of SPARQL triple patterns the
main agent should use, in order. For hops with inverse pairs, show
both directions.
"""


# ============================================================================
# Ontology structure extraction
# ============================================================================

def _short_name(uri) -> str:
    s = str(uri)
    if "#" in s:
        return s.split("#")[-1]
    return s.rsplit("/", 1)[-1]


def extract_ontology_structure(g: Graph) -> str:
    """Extract RDFS/OWL structural declarations as a concise text summary.

    Reads an rdflib.Graph and produces a summary suitable for the RDFS
    reasoning sub-agent. Includes: classes, properties with domain/range,
    soft routing hints (schema:domainIncludes/rangeIncludes), union domains,
    subClassOf hierarchies, owl:inverseOf pairs, OWL restrictions, and
    owl:disjointWith pairs.
    """
    sections = []

    # --- Object properties with hard domain/range (the routing paths) ---
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

    # Track which properties already have hard domain/range
    _routed_props = {str(p) for p in g.subjects(RDF.type, OWL.ObjectProperty)
                     if isinstance(p, URIRef)
                     and g.value(p, RDFS.domain) and isinstance(g.value(p, RDFS.domain), URIRef)
                     and g.value(p, RDFS.range) and isinstance(g.value(p, RDFS.range), URIRef)}

    # --- schema:domainIncludes / schema:rangeIncludes (soft routing hints) ---
    soft_obj_routes = []
    for p in sorted(g.subjects(RDF.type, OWL.ObjectProperty)):
        if not isinstance(p, URIRef) or str(p) in _routed_props:
            continue
        dom_includes = sorted(
            {_short_name(o) for o in g.objects(p, SCHEMA.domainIncludes) if isinstance(o, URIRef)}
        )
        rng_includes = sorted(
            {_short_name(o) for o in g.objects(p, SCHEMA.rangeIncludes) if isinstance(o, URIRef)}
        )
        if dom_includes or rng_includes:
            dom_str = ", ".join(dom_includes) if dom_includes else "?"
            rng_str = ", ".join(rng_includes) if rng_includes else "?"
            soft_obj_routes.append(
                f"  {_short_name(p)}: domainIncludes({dom_str}) -> rangeIncludes({rng_str})"
            )
    if soft_obj_routes:
        sections.append(
            f"\nSOFT ROUTING HINTS (schema:domainIncludes/rangeIncludes) [{len(soft_obj_routes)}]:"
        )
        sections.extend(soft_obj_routes)

    # --- Datatype properties with schema:domainIncludes (soft hints) ---
    soft_dt_routes = []
    for p in sorted(g.subjects(RDF.type, OWL.DatatypeProperty)):
        if not isinstance(p, URIRef):
            continue
        if g.value(p, RDFS.domain) and isinstance(g.value(p, RDFS.domain), URIRef):
            continue
        dom_includes = sorted(
            {_short_name(o) for o in g.objects(p, SCHEMA.domainIncludes) if isinstance(o, URIRef)}
        )
        if dom_includes:
            rng = g.value(p, RDFS.range)
            rng_name = _short_name(rng) if rng else "literal"
            dom_str = ", ".join(dom_includes)
            soft_dt_routes.append(
                f"  {_short_name(p)}: domainIncludes({dom_str}) -> {rng_name}"
            )
    if soft_dt_routes:
        sections.append(
            f"\nSOFT DATATYPE HINTS (schema:domainIncludes for datatype properties) [{len(soft_dt_routes)}]:"
        )
        sections.extend(soft_dt_routes)

    # --- Object properties with owl:unionOf domains ---
    union_routes = []
    for p in sorted(g.subjects(RDF.type, OWL.ObjectProperty)):
        if not isinstance(p, URIRef):
            continue
        dom = g.value(p, RDFS.domain)
        rng = g.value(p, RDFS.range)
        if not (dom and isinstance(dom, BNode) and rng and isinstance(rng, URIRef)):
            continue
        union_of = g.value(dom, OWL.unionOf)
        if not union_of:
            continue
        try:
            members = [_short_name(m) for m in g.items(union_of) if isinstance(m, URIRef)]
        except Exception:
            continue
        if members:
            union_routes.append(
                f"  {_short_name(p)}: unionOf({', '.join(members)}) -> {_short_name(rng)}"
            )
    if union_routes:
        sections.append(
            f"\nUNION-DOMAIN PROPERTIES (owl:unionOf domains) [{len(union_routes)}]:"
        )
        sections.extend(union_routes)

    # --- Datatype properties with hard domain ---
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

    # --- SubClassOf hierarchies (grouped by parent, 2+ children) ---
    hierarchy: dict[str, list[str]] = defaultdict(list)
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            hierarchy[_short_name(o)].append(_short_name(s))
    sections.append("\nSUBCLASS HIERARCHIES (parent: [children]):")
    for parent in sorted(hierarchy, key=lambda p: len(hierarchy[p]), reverse=True):
        children = sorted(hierarchy[parent])
        if len(children) >= 2:
            sections.append(f"  {parent} ({len(children)}): {', '.join(children)}")

    # --- owl:inverseOf pairs ---
    inverses = [
        (s, o) for s, _, o in g.triples((None, OWL.inverseOf, None))
        if isinstance(s, URIRef) and isinstance(o, URIRef)
    ]
    if inverses:
        sections.append("\nINVERSE PROPERTIES (owl:inverseOf):")
        for s, o in inverses:
            sections.append(f"  {_short_name(s)} <-> {_short_name(o)}")

    # --- owl:disjointWith pairs ---
    disjoints = [
        (s, o) for s, _, o in g.triples((None, OWL.disjointWith, None))
        if isinstance(s, URIRef) and isinstance(o, URIRef)
    ]
    if disjoints:
        sections.append("\nDISJOINT CLASSES (owl:disjointWith):")
        for s, o in disjoints:
            sections.append(f"  {_short_name(s)} disjoint {_short_name(o)}")

    # --- OWL restrictions (someValuesFrom = existential guarantees) ---
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

    # --- OWL restrictions (allValuesFrom = universal type constraints) ---
    seen_universal: set[tuple] = set()
    universals = []
    for cls in g.subjects(RDFS.subClassOf, None):
        if not isinstance(cls, URIRef):
            continue
        for restr in g.objects(cls, RDFS.subClassOf):
            if not isinstance(restr, BNode):
                continue
            on_prop = g.value(restr, OWL.onProperty)
            all_val = g.value(restr, OWL.allValuesFrom)
            if on_prop and all_val and isinstance(all_val, URIRef):
                if not isinstance(on_prop, URIRef):
                    continue
                key = (_short_name(cls), _short_name(on_prop), _short_name(all_val))
                if key not in seen_universal:
                    seen_universal.add(key)
                    universals.append(
                        f"  {key[0]}: {key[1]} constrained to {key[2]}"
                    )
    if universals:
        sections.append(f"\nUNIVERSAL CONSTRAINTS (owl:allValuesFrom) [{len(universals)}]:")
        sections.extend(universals)

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
