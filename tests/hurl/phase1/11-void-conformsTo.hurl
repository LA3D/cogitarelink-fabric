# Cycle C1 — VoID declares dct:conformsTo fabric:CoreProfile (D7, D9 L1)
# RED: .well-known/void must include dct:conformsTo pointing to CoreProfile

# Turtle representation
GET {{gateway}}/.well-known/void
Accept: text/turtle

HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "dct:conformsTo"
body contains "fabric#CoreProfile"

# JSON-LD representation
GET {{gateway}}/.well-known/void
Accept: application/ld+json

HTTP 200
[Asserts]
header "Content-Type" contains "application/ld+json"
body contains "dct:conformsTo"
body contains "fabric#CoreProfile"
