# Cycle C2 — CoreProfile PROF document at /.well-known/profile (D7, D9)
# RED: fabric:CoreProfile must be served as PROF profile with ResourceDescriptors

GET {{gateway}}/.well-known/profile
Accept: text/turtle

HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "prof:Profile"
body contains "prof:hasResource"
body contains "role:specification"
body contains "role:schema"
body contains "role:constraints"
body contains "role:guidance"
body contains "role:example"
body contains "owl:NamedIndividual"
body contains "sosa/"
body contains "CoreProfile"
