# Cycle A1 — VoID vocabulary declarations (D9 L1 four-layer KR)
# RED: .well-known/void must advertise void:vocabulary for SOSA + OWL-Time

GET {{gateway}}/.well-known/void
Accept: text/turtle

HTTP 200
[Asserts]
header "Content-Type" contains "text/turtle"
body contains "void:vocabulary"
body contains "sosa/"
body contains "time#"
