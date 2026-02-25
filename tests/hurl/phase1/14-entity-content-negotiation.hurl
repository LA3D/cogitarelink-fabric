# Phase 1 — Entity dereference content negotiation (FAIR A1)
# /entity/{id} should serve Turtle (default), JSON-LD, and N-Triples.

# Step 1: Ensure test entity exists
POST {{gateway}}/sparql/update
Content-Type: application/x-www-form-urlencoded

```
update=PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {
  GRAPH <http://localhost:8080/graph/entities> {
    <http://localhost:8080/entity/conneg-test-001>
        a sosa:Sensor ;
        sosa:observes <http://dbpedia.org/resource/Electric_potential> .
  }
}
```

HTTP 204

# Step 2: JSON-LD response
GET {{gateway}}/entity/conneg-test-001
Accept: application/ld+json

HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "conneg-test-001"

# Step 3: N-Triples response
GET {{gateway}}/entity/conneg-test-001
Accept: application/n-triples

HTTP 200
[Asserts]
header "Content-Type" contains "application/n-triples"
body contains "conneg-test-001"

# Step 4: Default (Turtle) response
GET {{gateway}}/entity/conneg-test-001

HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "conneg-test-001"
