# Cycle 6 — .well-known/shacl endpoint-specific shapes
# RED: gateway exposes SHACL shapes with sh:NodeShape, sh:targetClass, sh:agentInstruction

GET http://localhost:8080/.well-known/shacl
Accept: text/turtle

HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "sh:NodeShape"
body contains "sh:targetClass"
body contains "sh:agentInstruction"
