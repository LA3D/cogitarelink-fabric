# Cycle 2 — FastAPI gateway health
# RED: gateway /healthz returns {"status":"ok"}

GET {{gateway}}/healthz

HTTP 200
[Asserts]
header "Content-Type" contains "application/json"
jsonpath "$.status" == "ok"
