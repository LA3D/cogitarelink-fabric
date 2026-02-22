# Cycle A2 — TBox named graph exists and non-empty (D9 L2 four-layer KR)
# RED: SOSA TBox loaded into /graph/tbox/sosa at node startup

POST {{gateway}}/sparql
[FormParams]
query: ASK { GRAPH <{{gateway}}/graph/tbox/sosa> { ?s ?p ?o } }

HTTP 200
[Asserts]
body contains "true"
