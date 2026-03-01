# Cycle 5 — SOSA data load and retrieval
# RED: INSERT a mock SOSA Observation, then SELECT and verify it exists

# Step 0: Clear the test graph for idempotent runs
POST {{gateway}}/sparql/update
Content-Type: application/x-www-form-urlencoded

```
update=DROP SILENT GRAPH <{{gateway}}/graph/observations>
```

HTTP 204

# Step 1: INSERT mock SOSA Observation into /graph/observations
POST {{gateway}}/sparql/update
Content-Type: application/x-www-form-urlencoded

```
update=PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {
  GRAPH <{{gateway}}/graph/observations> {
    <{{gateway}}/entity/test-obs-001>
        a sosa:Observation ;
        sosa:hasSimpleResult "0.42"^^xsd:decimal ;
        sosa:resultTime "2026-02-22T00:00:00Z"^^xsd:dateTime .
  }
}
```

HTTP 204

# Step 2: SELECT to verify exactly one observation exists
POST {{gateway}}/sparql
Accept: application/sparql-results+json
[FormParams]
query: PREFIX sosa: <http://www.w3.org/ns/sosa/> SELECT (COUNT(*) AS ?n) FROM <{{gateway}}/graph/observations> WHERE { ?obs a sosa:Observation }

HTTP 200
[Asserts]
jsonpath "$.results.bindings[0].n.value" == "1"
