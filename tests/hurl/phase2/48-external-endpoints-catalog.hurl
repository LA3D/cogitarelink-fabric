# Phase 2 — D29: External endpoint attestation
# /.well-known/catalog includes dcat:DataService entries for vouched external endpoints

GET {{gateway}}/.well-known/catalog
Accept: text/turtle
HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
# External entries are dcat:DataService (not dcat:Dataset)
body contains "dcat#DataService"
# fabric:vouchedBy predicate links to vouching node
body contains "vouchedBy"
# All three QLever endpoints present
body contains "pubchem"
body contains "wikidata"
body contains "osm-planet"
# Endpoint URLs resolve to QLever
body contains "qlever.cs.uni-freiburg.de"
