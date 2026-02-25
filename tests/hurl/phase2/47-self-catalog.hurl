# Phase 2 — D23 Stage 1: Self-catalog from VoID
# GET /.well-known/catalog returns DCAT datasets extracted from node's VoID

GET {{gateway}}/.well-known/catalog
Accept: text/turtle
HTTP 200
Content-Type: text/turtle
[Asserts]
body contains "dcat:Dataset"
body contains "Observations"
body contains "/sparql"
