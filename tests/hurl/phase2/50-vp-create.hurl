# 50-vp-create.hurl — Credo creates a VP wrapping a VC
# Prerequisite: register an agent first to get a credential

# Step 1: Register agent
POST http://localhost:3000/agents/register
Content-Type: application/json
{
  "agentRole": "DevelopmentAgentRole",
  "authorizedGraphs": ["/graph/observations", "/graph/entities"],
  "authorizedOperations": ["read"]
}
HTTP 201
[Captures]
agent_credential: jsonpath "$.credential"
agent_did: jsonpath "$.agentDid"

# Step 2: Create VP from credential
POST http://localhost:3000/presentations/create
Content-Type: application/json
{
  "credential": {{agent_credential}},
  "holderDid": "{{agent_did}}",
  "validMinutes": 5
}
HTTP 201
[Asserts]
jsonpath "$.type[0]" == "VerifiablePresentation"
jsonpath "$.holder" exists
jsonpath "$.validUntil" exists
jsonpath "$.proof" exists
jsonpath "$.proof.cryptosuite" == "eddsa-jcs-2022"
jsonpath "$.proof.proofPurpose" == "authentication"
jsonpath "$.verifiableCredential" count == 1
