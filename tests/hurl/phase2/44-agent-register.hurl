# Phase 2 — D13/D14: Agent registration
# Register an IngestCurator agent, verify 201 + credential returned

POST {{gateway}}/agents/register
Content-Type: application/json
```json
{
  "agentRole": "IngestCuratorRole",
  "authorizedGraphs": ["/graph/observations", "/graph/entities"],
  "authorizedOperations": ["read", "write"]
}
```
HTTP 201
[Asserts]
jsonpath "$.agentDid" exists
jsonpath "$.credential" exists
jsonpath "$.credential.type" contains "AgentAuthorizationCredential"

# Error case: invalid role returns 400
POST {{gateway}}/agents/register
Content-Type: application/json
```json
{
  "agentRole": "BogusRole",
  "authorizedGraphs": [],
  "authorizedOperations": []
}
```
HTTP 400
