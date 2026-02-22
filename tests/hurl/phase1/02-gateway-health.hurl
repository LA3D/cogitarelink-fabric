# Cycle 2 — FastAPI gateway health
# RED: gateway /healthz returns {"status":"ok"}

GET http://localhost:8080/healthz

HTTP 200
[Asserts]
header "Content-Type" contains "application/json"
jsonpath "$.status" == "ok"
