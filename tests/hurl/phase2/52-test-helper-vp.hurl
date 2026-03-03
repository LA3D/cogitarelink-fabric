# 52-test-helper-vp.hurl — Dev helper creates a VP token for testing

POST {{gateway}}/test/create-vp
Content-Type: application/json
{
  "agentRole": "DevelopmentAgentRole",
  "authorizedGraphs": ["/graph/observations", "/graph/entities"],
  "authorizedOperations": ["read"]
}
HTTP 201
[Asserts]
jsonpath "$.token" exists
jsonpath "$.agentDid" exists
jsonpath "$.agentRole" == "DevelopmentAgentRole"
jsonpath "$.validUntil" exists
[Captures]
vp_token: jsonpath "$.token"
