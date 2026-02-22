---
paths: ["**/*.rq", "**/*.sparql"]
---

# SPARQL Patterns

## Prefix Declarations
Always include these at top of every file:
```sparql
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX dct:  <http://purl.org/dc/terms/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX ssn:  <http://www.w3.org/ns/ssn/>
PREFIX qudt: <http://qudt.org/schema/qudt/>
PREFIX unit: <http://qudt.org/vocab/unit/>
PREFIX sh:   <http://www.w3.org/ns/shacl#>
PREFIX void: <http://rdfs.org/ns/void#>
PREFIX fab:  <https://fabric.example.org/vocab#>
```

## Named Graph Queries (D6)
Use GRAPH clause for partition access:
```sparql
SELECT ?obs WHERE {
  GRAPH <https://node.example.org/graph/observations> {
    ?obs a sosa:Observation ;
         sosa:hasResult ?r .
  }
}
LIMIT 100
```

## SPARQL UPDATE for Writes
Never POST raw Turtle; always use SPARQL UPDATE:
```sparql
INSERT DATA {
  GRAPH <https://node.example.org/graph/observations> {
    <https://node.example.org/entity/{uuid7}> a sosa:Observation .
  }
}
```

## Federation (D21, D20)
PubChem via QLever (Phase 1):
```sparql
SELECT ?cid ?label WHERE {
  SERVICE <https://qlever.dev/api/pubchem> {
    ?cid wdt:P233 ?smiles .
    OPTIONAL { ?cid rdfs:label ?label . FILTER(lang(?label) = "en") }
  }
}
LIMIT 10
```

## Exploratory Queries
Always include LIMIT on exploratory queries (default 100):
```sparql
SELECT DISTINCT ?type WHERE {
  GRAPH ?g { ?s a ?type }
}
LIMIT 100
```

## SPARQL Examples Files (SIB spex: pattern, D9 L4)
Each example is a `sh:SPARQLExecutable` instance:
```turtle
ex:FindObservationsByFeature a sh:SPARQLExecutable, spex:Example ;
    rdfs:label "Find observations for a feature of interest" ;
    schema:target <https://node.example.org/sparql> ;
    sh:select """
      PREFIX sosa: <http://www.w3.org/ns/sosa/>
      SELECT ?obs ?result WHERE {
        GRAPH <.../graph/observations> {
          ?obs sosa:hasFeatureOfInterest ?foi ;
               sosa:hasResult ?result .
        }
      } LIMIT 20
    """ .
```
