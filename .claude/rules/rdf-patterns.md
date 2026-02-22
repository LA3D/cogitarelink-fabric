---
paths: ["**/*.ttl", "**/*.jsonld", "**/*.trig", "**/*.nq"]
---

# RDF Patterns

## Turtle Style
- One triple per line; blank node reuse for complex objects
- Prefix declarations at top; use standard prefixes (rdf, rdfs, owl, xsd, dct, prov, sosa, ssn, qudt, sh, spex, void, prof, dcat, foaf)
- No semicolons on final triple of a subject block

## JSON-LD
- Use `@context` from `ontology/fabric-context.jsonld`, not inline
- Include `@type` on every object
- Prefer compact IRI form over full URIs in `@context`-covered terms

## Named Graph Conventions (D6)
Named graphs in Oxigraph:
- `/graph/observations` — SOSA Observation instances
- `/graph/entities` — identified entities (sosa:FeatureOfInterest, instrument records)
- `/graph/claims` — inferred or curated assertions
- `/graph/security` — security events
- `/graph/audit` — audit log entries
- `/graph/pending` — awaiting HitL approval (D19)
- `/graph/approvals` — approved items (dual-proof VC attached)
- `/graph/crosswalks` — SSSOM entity PID crosswalks (D11)
- `/graph/mappings` — SSSOM vocabulary/term alignment (D21)
- `/ontology/sosa`, `/ontology/time`, `/ontology/qudt` — TBox cache (D9 L2)
- `/shapes/sosa-v1` — standard SOSA SHACL shapes (D9 L2)

## Provenance
- Always include `prov:wasAttributedTo <https://orcid.org/0000-0003-4091-6059>` in provenance graphs
- IngestCurator writes must include `prov:wasGeneratedBy [ a prov:Activity ; ... ]`
- Use `prov:startedAtTime`/`prov:endedAtTime` with xsd:dateTime

## Nanopub Four-Graph Pattern (D18)
```turtle
# Head graph (always first)
:np-{uuid} {
    :np-{uuid} np:hasAssertion :np-{uuid}#assertion ;
               np:hasProvenance :np-{uuid}#provenance ;
               np:hasPublicationInfo :np-{uuid}#pubinfo .
}
# Assertion, Provenance, PubInfo follow
```

## SSSOM Serialization (D21)
- Use sssom-py Turtle serialization (not TSV) for `/graph/mappings`
- Required predicates: `sssom:subject_id`, `sssom:object_id`, `sssom:predicate_id`, `sssom:mapping_justification`, `sssom:confidence`
- Prefer `semapv:ManualMappingCuration` or `semapv:LogicalReasoning` for justification

## SHACL Shapes Files
- `sh:agentInstruction` — narrow NL hint on a shape (routing, format, units)
- `sh:intent` — purpose of the shape (agent-readable description)
- `sh:SPARQLExecutable` instances go in sparql-examples files (D9 L4), not shapes files
