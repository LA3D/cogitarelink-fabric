# 51-vp-verify.hurl — Credo verifies a VP (VP proof + embedded VC proof)

# Step 1: Register agent
POST http://localhost:3000/agents/register
Content-Type: application/json
{
  "agentRole": "QARole",
  "authorizedGraphs": ["/graph/observations"],
  "authorizedOperations": ["read"]
}
HTTP 201
[Captures]
agent_credential: jsonpath "$.credential"
agent_did: jsonpath "$.agentDid"

# Step 2: Create VP
POST http://localhost:3000/presentations/create
Content-Type: application/json
{
  "credential": {{agent_credential}},
  "holderDid": "{{agent_did}}",
  "validMinutes": 5
}
HTTP 201
[Captures]
vp_json: jsonpath "$"

# Step 3: Verify VP
POST http://localhost:3000/presentations/verify
Content-Type: application/json
{{vp_json}}
HTTP 200
[Asserts]
jsonpath "$.verified" == true
jsonpath "$.credentialSubject.agentRole" exists
jsonpath "$.validUntil" exists
