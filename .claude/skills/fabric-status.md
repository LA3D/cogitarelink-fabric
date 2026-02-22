# /fabric-status

Inspect Docker Compose stack health and summarize running fabric node state.

## Usage
```
/fabric-status [--compose-file <path>]
```

## Steps

1. **Docker Compose status**:
   ```bash
   docker compose ps
   docker compose logs --tail=20 fabric-node
   ```
   Report: running/stopped containers, recent errors

2. **SPARQL endpoint check**:
   ```bash
   curl -s http://localhost:8080/sparql?query=SELECT+(COUNT(*)+AS+?n)+WHERE{?s+?p+?o} \
     -H "Accept: application/sparql-results+json"
   ```
   Report: triple count across all graphs

3. **Named graph inventory**:
   ```sparql
   SELECT ?g (COUNT(*) AS ?triples) WHERE { GRAPH ?g { ?s ?p ?o } }
   GROUP BY ?g ORDER BY DESC(?triples)
   ```
   Report: all named graphs with triple counts

4. **.well-known/ response check**:
   ```bash
   curl -s -I http://localhost:8080/.well-known/void
   curl -s -I http://localhost:8080/.well-known/shacl
   ```
   Report: HTTP status + Content-Type for each

5. **Oxigraph direct check** (if port exposed):
   ```bash
   curl -s http://localhost:7878/
   ```
   Report: Oxigraph version + storage location

6. **Credo sidecar check** (if running):
   ```bash
   curl -s http://localhost:3000/health
   ```
   Report: Credo status + DID wallet info

## Output Format
```
Fabric node status — {timestamp}

Docker containers:
  fabric-node    RUNNING  (up 2h)
  oxigraph       RUNNING  (up 2h)
  credo-sidecar  STOPPED  (Phase 1 — not required)

SPARQL endpoint: http://localhost:8080/sparql  [OK]
Triple count: 1,247 across 6 named graphs

Named graphs:
  /ontology/sosa    892 triples
  /shapes/sosa-v1   187 triples
  /graph/observations  168 triples
  ...

.well-known/: void [200 OK] | shacl [200 OK] | sparql-examples [404 not yet]
Credo: not running (Phase 1 scope)
```
