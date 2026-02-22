# Cycle B — .well-known/sparql-examples (SIB pattern, D9 L3 four-layer KR)
# RED: endpoint serves SPARQL examples catalog with spex:SPARQLExecutable

GET {{gateway}}/.well-known/sparql-examples
Accept: text/turtle

HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "SPARQLExecutable"
body contains "sh:select"
body contains "sosa:Observation"
body contains "rdfs:comment"
