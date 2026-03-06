# SPARQL Proxy Service Description Leak — Debug Tests

Investigation into why Comunica's source auto-detection resolves to the
internal Docker hostname (`oxigraph:7878`) when querying through the
FastAPI SPARQL proxy.

**Date**: 2026-03-06
**Status**: Workaround in place, root cause not yet identified
**Workaround**: Explicit `{ type: "sparql", value: url }` source typing
bypasses SD discovery entirely (used in `sandbox-tools.ts`)

## The Problem

When Comunica auto-detects source type (string URL, no explicit type):

1. Comunica GETs `/sparql` (no `query` param) → proxy forwards to Oxigraph → returns SPARQL SD
2. SD contains `sd:endpoint <>` (relative IRI) — should resolve to external URL
3. Comunica constructs query URL as `https://oxigraph:7878/query?query=...` (WRONG)
4. Query fails: `ENOTFOUND oxigraph`

The internal Docker hostname leaks through the proxy somehow.

## What We Verified

- The SD body is correct: `sd:endpoint <>` with no internal URLs
- The fetch Response `.url` is correct: `https://bootstrap.cogitarelink.ai/sparql`
- N3 parser resolves `<>` correctly against the response URL base
- No response headers contain the internal hostname
- Oxigraph returns only 3 headers: `content-type`, `server`, `content-length`
- The proxy's `_HOP_BY_HOP` filter is minimal but nothing leaked is hop-by-hop

## What We Suspect

Comunica's `ActorRdfMetadataExtractSparqlService` has an `inferHttpsEndpoint`
flag that rewrites `http:` → `https:` when the original URL starts with `https`.
This would produce `https://oxigraph:7878/query` from `http://oxigraph:7878/query`.

The question: **where does `http://oxigraph:7878/query` enter the pipeline?**

Possible causes:
1. The streaming RDF parser in Comunica's pipeline receives a different base IRI
   than expected (maybe from `ActorDereferenceHttpBase` line 71:
   `const url = resolve(httpResponse.url, action.url)`)
2. Some Comunica actor caches or derives the URL from a source other than
   the fetch Response
3. Engine state effects: a failed 401 request "primes" the engine so subsequent
   requests work (test 01 demonstrates this)

## Test Progression

Run all tests from `experiments/node-rlm-fabric/`:

```bash
NODE_EXTRA_CA_CERTS=../../caddy-root.crt npx tsx debug/01-engine-priming.ts
NODE_EXTRA_CA_CERTS=../../caddy-root.crt npx tsx debug/02-fresh-engine.ts
NODE_EXTRA_CA_CERTS=../../caddy-root.crt npx tsx debug/03-explicit-source-type.ts
NODE_EXTRA_CA_CERTS=../../caddy-root.crt npx tsx debug/04-fetch-url-trace.ts
```

| Test | What It Isolates | Expected Result |
|------|-----------------|-----------------|
| `01-engine-priming.ts` | Same engine: failed call (401) → working call (auth). Shows that a prior failure "primes" the engine. | Test 1 fails (401), Test 2 succeeds, Test 3 (fresh engine) fails |
| `02-fresh-engine.ts` | Fresh engine with auth, single query. Demonstrates the baseline failure. | Fails with `ENOTFOUND oxigraph` |
| `03-explicit-source-type.ts` | `{ type: "sparql", value: url }` source. Demonstrates the workaround. | Succeeds — sends query directly, no SD discovery |
| `04-fetch-url-trace.ts` | Logging wrapper around fetch to trace ALL URLs Comunica requests. Shows exactly where the internal URL appears. | First fetch OK (`bootstrap.cogitarelink.ai`), second fetch FAILS (`oxigraph:7878`) |

## Next Steps for Investigation

1. Add Comunica verbose logging (`@comunica/logger-pretty`) to see internal actor communication
2. Instrument `ActorRdfMetadataExtractSparqlService` to log what `sparqlService` gets extracted
3. Check if `ActorDereferenceHttpBase` returns a different `url` than expected (line 71)
4. Test whether adding a `Content-Location` header in the proxy fixes the base URI resolution
5. Test whether rewriting `sd:endpoint <>` to an absolute URL in the proxy fixes it

## Relevant Source Files

| Comunica Module | File (in node_modules) | Key Line |
|---|---|---|
| SD metadata extraction | `@comunica/actor-rdf-metadata-extract-sparql-service` | `inferHttpsEndpoint` rewrite |
| SPARQL source identification | `@comunica/actor-query-source-identify-hypermedia-sparql` | Line 29: `forceSourceType ? action.url : metadata.sparqlService` |
| HTTP dereference | `@comunica/actor-dereference-http` | Line 71: `resolve(httpResponse.url, action.url)` |
| N3 RDF parse | `@comunica/actor-rdf-parse-n3` | `baseIRI: action.metadata?.baseIRI` |
| HTTP fetch | `@comunica/actor-http-fetch` | Uses context `fetch` or `globalThis.fetch` |
