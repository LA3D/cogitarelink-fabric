# /fabric-test

Run the fabric node conformance suite against a running fabric node.

## Usage
```
/fabric-test [--endpoint <url>]
```
Default endpoint: http://localhost:8080

## Tests

### 1. SPARQL endpoint health
```bash
curl -s "{endpoint}/sparql?query=SELECT+*+WHERE{?s+?p+?o}LIMIT+1" \
  -H "Accept: application/sparql-results+json"
```
Pass: HTTP 200 + valid JSON with `head`/`results` keys

### 2. .well-known/void response structure
- HTTP 200 with Content-Type: text/turtle (or application/ld+json)
- Contains `void:sparqlEndpoint` triple
- Contains `dct:conformsTo` triple
- Contains at least one `void:namedGraph` entry

### 3. .well-known/shacl response structure
- HTTP 200 with Content-Type: text/turtle
- Contains at least one `sh:NodeShape`
- Each shape has `sh:targetClass`
- At least one shape has `sh:agentInstruction` (agent-navigable)

### 4. .well-known/sparql-examples structure
- HTTP 200 (directory listing as RDF or 404 with explanation)
- If present: contains `sh:SPARQLExecutable` instances with `rdfs:label` and `schema:target`

### 5. SHACL validation round-trip
- Fetch shapes from `.well-known/shacl`
- Insert a minimal valid SOSA Observation into `/graph/observations`
- Run pyshacl: must report conforms=True
- Insert an invalid observation (missing `sosa:hasResult`): must report conforms=False with violation

### 6. Entity dereferenceability (FAIR A1)
- If any entities exist in `/graph/entities`: dereference one via `/entity/{uuid}`
- Expect HTTP 200 + Turtle with at least 3 triples describing the entity

### 7. DID resolution (Phase 2 — skip in Phase 1 if Credo not running)
- Resolve node DID from `void.ttl` `dct:creator` or equivalent
- `did resolve {did}` via Credo sidecar
- Expect valid DID document with `verificationMethod` array

## Output
```
fabric-test results for {endpoint}
  [PASS] SPARQL endpoint health
  [PASS] .well-known/void structure
  [PASS] .well-known/shacl structure
  [SKIP] .well-known/sparql-examples (not yet implemented)
  [PASS] SHACL validation round-trip (valid: conforms, invalid: 1 violation)
  [SKIP] Entity dereferenceability (no entities yet)
  [SKIP] DID resolution (Phase 1 — Credo not in scope)

3/5 implemented tests passing. 2 skipped (not yet implemented).
```
