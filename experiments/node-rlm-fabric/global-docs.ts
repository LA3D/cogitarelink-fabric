export const BASELINE_DOCS = `
## Fabric Endpoint Tools

You are querying a self-describing SPARQL endpoint (cogitarelink fabric node).
The endpoint serves RDF data in named graphs.

### Available Functions

**comunica_query(query, sources?)** — Execute SPARQL SELECT or CONSTRUCT.
  - query: SPARQL query string
  - sources: optional array of SPARQL endpoint URLs (defaults to the fabric endpoint)
  - Returns: JSON array of result bindings (max 10K chars)
  - Example: const results = await comunica_query("SELECT ?s ?p ?o WHERE { GRAPH <.../graph/observations> { ?s ?p ?o } } LIMIT 10")

**fetchVoID()** — Fetch the endpoint's service description (VoID/SD).
  - Returns: Turtle string describing available named graphs, shapes, SPARQL examples
  - Start here to understand what data the endpoint has

**fetchShapes()** — Fetch SHACL shapes describing data constraints.
  - Returns: Turtle string with NodeShape/PropertyShape declarations
  - Shapes include sh:agentInstruction hints for query construction

**fetchExamples()** — Fetch SPARQL example queries.
  - Returns: Turtle string with example SELECT/CONSTRUCT patterns
  - Use these as templates for your queries

**fetchEntity(entityId)** — Dereference an entity by UUID.
  - entityId: UUID7 string (e.g., "01234567-89ab-cdef-0123-456789abcdef")
  - Returns: JSON-LD representation of the entity

### Discovery Strategy

1. Call fetchVoID() to understand the endpoint structure (named graphs, vocabularies)
2. Call fetchShapes() for data constraints and agent hints
3. Call fetchExamples() for query templates
4. Use comunica_query() to execute SPARQL against specific named graphs
`.trim();

export const JSONLD_DOCS = `
## Fabric Endpoint Tools

You are querying a self-describing SPARQL endpoint (cogitarelink fabric node).
The endpoint serves RDF data in named graphs and vocabulary definitions as JSON-LD.

### Available Functions

**comunica_query(query, sources?)** — Execute SPARQL SELECT or CONSTRUCT.
  - query: SPARQL query string
  - sources: optional array of SPARQL endpoint URLs (defaults to the fabric endpoint)
  - Returns: JSON array of result bindings (max 10K chars)
  - Use this for querying instance data in named graphs

**fetchVoID()** — Fetch the endpoint's service description (VoID/SD).
  - Returns: Turtle string describing available named graphs, shapes, SPARQL examples
  - Start here to understand what data the endpoint has

**fetchShapes()** — Fetch SHACL shapes describing data constraints.
  - Returns: Turtle string with NodeShape/PropertyShape declarations
  - Shapes include sh:agentInstruction hints for query construction

**fetchExamples()** — Fetch SPARQL example queries.
  - Returns: Turtle string with example SELECT/CONSTRUCT patterns
  - Use these as templates for your queries

**fetchEntity(entityId)** — Dereference an entity by UUID.
  - entityId: UUID7 string
  - Returns: JSON-LD representation of the entity

**fetchJsonLd(url)** — Fetch any URL as JSON-LD.
  - url: any HTTP(S) URL (fabric endpoints, vocabulary URIs, external sources)
  - Returns: JSON-LD string (max 10K chars, truncated with guidance if larger)
  - Use this to retrieve vocabulary definitions from /ontology/{vocab}

**jsonld.expand(doc)** — Expand compact JSON-LD to explicit form.
  - Makes all IRIs absolute, removes @context compaction
  - Essential for seeing the full property URIs in a vocabulary

**jsonld.compact(doc, context)** — Compact expanded JSON-LD with a context.
  - Applies prefix mappings for readable output
  - Useful after expand to make results human-readable

**jsonld.frame(doc, frame)** — Extract subgraph matching a frame pattern.
  - Like a structured query over JSON-LD — specify the shape you want
  - Example: frame for all properties with a given rdfs:domain

### Tool Selection by Graph Purpose

The service description classifies each named graph with fabric:graphPurpose:
- **"instances"** graphs (observations, entities): Query with comunica_query() using SPARQL SELECT/CONSTRUCT
- **"schema"** graphs (ontologies at /ontology/*): Explore with fetchJsonLd() + jsonld.frame() for structural discovery, or comunica_query() with SPARQL CONSTRUCT for targeted axiom queries
- **"metadata"** graphs: Query with comunica_query() when needed for audit trails

### Discovery Strategy

1. Call fetchVoID() to understand the endpoint structure (named graphs, vocabularies, graph purposes)
2. Call fetchShapes() for data constraints and agent hints
3. Call fetchExamples() for query templates
4. For schema graphs: use fetchJsonLd() + jsonld.frame() to explore vocabulary structure incrementally
5. For large ontologies: use jsonld.frame() to extract specific patterns (e.g., all properties of a class) rather than reading the full document
6. For instance graphs: use comunica_query() with SPARQL SELECT/CONSTRUCT
7. Combine: discover structure via JSON-LD, then construct precise SPARQL queries for data
`.trim();

export const LTQP_DOCS = `
${BASELINE_DOCS}

### Link Traversal (additional)

**comunica_traverse(query, seedUrls)** — Execute SPARQL with link traversal.
  - The engine follows RDF links automatically during query execution
  - seedUrls: starting points for traversal (e.g., VoID endpoint, entity URIs)
  - Results arrive progressively as links are discovered
  - Useful for exploring data without knowing the exact graph structure
`.trim();

export const COMBINED_DOCS = JSONLD_DOCS;

export function getGlobalDocs(condition: string): string {
  switch (condition) {
    case "js-baseline": return BASELINE_DOCS;
    case "js-jsonld": return JSONLD_DOCS;
    case "js-ltqp": return LTQP_DOCS;
    case "js-combined": return COMBINED_DOCS;
    default: return BASELINE_DOCS;
  }
}
