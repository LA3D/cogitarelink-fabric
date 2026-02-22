# /nanopub-draft

Draft a nanopublication from a fabric named graph (D18). Assembles four-graph structure.

## Usage
```
/nanopub-draft <graph-iri> [--endpoint <url>] [--attribution <orcid>]
```
Example: `/nanopub-draft https://node.example.org/graph/observations/run-2026-02-22`

## Background (D18)

Nanopub four-graph pattern:
- `#head` — declares the other three graphs
- `#assertion` — the scientific claim (triples from source graph)
- `#provenance` — how the assertion was produced (PROV-O)
- `#pubinfo` — publication metadata (attribution, timestamp, license)

Three-tier use cases:
1. Scientific: auto-drafted → human approves → published to nanopub server (external HitL gate)
2. Industry: internal only, auto-committed (no external submission)
3. DoD: strictest gates (out of scope for Phase 1)

## Steps

1. **Query source graph** to extract assertion triples:
   ```sparql
   CONSTRUCT { ?s ?p ?o } WHERE {
     GRAPH <{source-graph}> { ?s ?p ?o }
   } LIMIT 200
   ```

2. **Assemble nanopub IRI**: `urn:uuid:{uuid7}` (later upgraded to TrustyURI post-hashing)

3. **Build four-graph Turtle**:
   ```turtle
   @prefix np: <http://www.nanopub.org/nschema#> .
   @prefix : <urn:uuid:{uuid7}#> .

   :head {
     : a np:Nanopublication ;
       np:hasAssertion :assertion ;
       np:hasProvenance :provenance ;
       np:hasPublicationInfo :pubinfo .
   }

   :assertion {
     # triples from source graph (CONSTRUCT result)
   }

   :provenance {
     :assertion prov:wasDerivedFrom <{source-graph}> ;
       prov:wasAttributedTo <{attribution-orcid}> .
   }

   :pubinfo {
     : dct:created "{iso-timestamp}"^^xsd:dateTime ;
       dct:creator <{attribution-orcid}> ;
       dct:license <https://creativecommons.org/licenses/by/4.0/> ;
       fabric:status fabric:Draft .
   }
   ```

4. **Write as `fabric:Draft`** to a new named graph:
   - IRI: `{node-base}/nanopubs/{uuid7}`
   - INSERT into Oxigraph as a TriG-formatted named graph

5. Report: nanopub IRI, triple count in each graph, status=Draft
   - For scientific tier: indicate "awaiting human approval for external submission"
   - For industry tier: indicate "auto-committed (no external submission)"
