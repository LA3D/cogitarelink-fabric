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
${BASELINE_DOCS}

### JSON-LD Processing (additional)

**jsonld.expand(doc)** — Expand JSON-LD to canonical form (full IRIs)
**jsonld.compact(doc, context)** — Compact using a context (readable prefixes)
**jsonld.frame(doc, frame)** — Reshape JSON-LD into a tree structure matching a template
**jsonld.fromRDF(nquads, options)** — Convert N-Quads to JSON-LD
**jsonld.toRDF(doc, options)** — Convert JSON-LD to N-Quads

The jsonld document loader resolves fabric vocabulary URIs to local /ontology/{vocab} endpoints.
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

export const COMBINED_DOCS = `
${JSONLD_DOCS}

### Link Traversal (additional)

**comunica_traverse(query, seedUrls)** — Execute SPARQL with link traversal.
  - The engine follows RDF links automatically during query execution
  - seedUrls: starting points for traversal
  - Results arrive progressively as links are discovered
`.trim();

export function getGlobalDocs(condition: string): string {
  switch (condition) {
    case "js-baseline": return BASELINE_DOCS;
    case "js-jsonld": return JSONLD_DOCS;
    case "js-ltqp": return LTQP_DOCS;
    case "js-combined": return COMBINED_DOCS;
    default: return BASELINE_DOCS;
  }
}
